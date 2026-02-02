"""
搜索路由 - 完整迁移旧项目搜索逻辑
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel
from ..database import get_connection
from ..models.image import SearchRequest, SearchResponse

router = APIRouter()


class AdvancedSearchRequest(BaseModel):
    """高级搜索请求（兼容旧项目二维数组格式）"""
    # 二维数组：每个子数组是一个标签膨胀后的关键词列表（子数组内OR，子数组间AND）
    keywords: list[list[str]] = []
    # 二维数组：每个子数组是一个排除标签膨胀后的关键词列表（子数组内OR，子数组间AND排除）
    excludes: list[list[str]] = []
    # 三维数组：交集排除，结构为 [[[kw1膨胀组], [kw2膨胀组]], ...]
    # 每个胶囊内的关键词组需要同时匹配才排除（组内OR，组间AND，整体NOT）
    excludes_and: list[list[list[str]]] = []
    # 包含的扩展名列表
    extensions: list[str] = []
    # 排除的扩展名列表
    exclude_extensions: list[str] = []
    # 分页
    offset: int = 0
    limit: int = 50
    # 排序：date_desc/asc, size_desc/asc, resolution_desc/asc
    sort_by: str = "date_desc"
    # 标签数量筛选
    min_tags: int = 0
    max_tags: int = -1  # -1 表示无限制


def expand_tags_with_rules(tags: list[str]) -> list[str]:
    """根据规则树膨胀标签（包含所有子节点关键词）"""
    if not tags:
        return []

    expanded = set(tags)

    with get_connection() as conn:
        cursor = conn.cursor()

        for tag in tags:
            # 查找包含该关键词的组
            cursor.execute("""
                SELECT DISTINCT sg.id
                FROM search_groups sg
                JOIN search_keywords sk ON sg.id = sk.group_id
                WHERE sk.keyword = ? AND sg.enabled = 1
            """, (tag,))

            group_ids = [row['id'] for row in cursor.fetchall()]

            for group_id in group_ids:
                # 获取所有子孙节点的关键词
                cursor.execute("""
                    SELECT DISTINCT sk.keyword
                    FROM search_keywords sk
                    JOIN search_hierarchy sh ON sk.group_id = sh.descendant_id
                    JOIN search_groups sg ON sk.group_id = sg.id
                    WHERE sh.ancestor_id = ? AND sg.enabled = 1
                """, (group_id,))

                for row in cursor.fetchall():
                    expanded.add(row['keyword'])

                # 也包含当前组的关键词
                cursor.execute("""
                    SELECT keyword FROM search_keywords WHERE group_id = ?
                """, (group_id,))

                for row in cursor.fetchall():
                    expanded.add(row['keyword'])

    return list(expanded)


async def search_images_simple(request: SearchRequest) -> SearchResponse:
    """搜索图片（简化版，兼容新前端）"""
    # 根据 expand 参数决定是否膨胀标签
    if request.expand:
        expanded_include = expand_tags_with_rules(request.include_tags)
    else:
        expanded_include = request.include_tags

    with get_connection() as conn:
        cursor = conn.cursor()

        # 构建查询
        where_clauses = ["1=1"]
        params = []
        tags_expr = "NULLIF(f.tags, '')"

        # 包含标签（OR 关系）
        if expanded_include:
            or_conditions = []
            for tag in expanded_include:
                or_conditions.append(f"{tags_expr} LIKE ?")
                params.append(f"%{tag}%")
            where_clauses.append(f"({' OR '.join(or_conditions)})")

        # 排除标签
        for exclude_tag in request.exclude_tags:
            where_clauses.append(f"{tags_expr} NOT LIKE ?")
            params.append(f"%{exclude_tag}%")

        # 标签数量过滤
        tag_count_expr = """
            CASE
                WHEN {tags_expr} IS NULL OR {tags_expr} = '' THEN 0
                ELSE LENGTH({tags_expr}) - LENGTH(REPLACE({tags_expr}, ' ', '')) + 1
            END
        """.format(tags_expr=tags_expr)

        if request.min_tags is not None and request.min_tags > 0:
            where_clauses.append(f"({tag_count_expr}) >= ?")
            params.append(request.min_tags)

        if request.max_tags is not None and request.max_tags >= 0:
            where_clauses.append(f"({tag_count_expr}) <= ?")
            params.append(request.max_tags)

        # 扩展名过滤
        if request.extensions:
            ext_conditions = []
            for ext in request.extensions:
                ext_conditions.append("LOWER(i.filename) LIKE ?")
                params.append(f"%.{ext.lower()}")
            where_clauses.append(f"({' OR '.join(ext_conditions)})")

        # 排除扩展名
        if request.exclude_extensions:
            for ext in request.exclude_extensions:
                where_clauses.append("LOWER(i.filename) NOT LIKE ?")
                params.append(f"%.{ext.lower()}")

        where_sql = " AND ".join(where_clauses)

        # 获取总数
        count_query = f"""
            SELECT COUNT(*) as total
            FROM images i
            LEFT JOIN images_fts f ON i.id = f.rowid
            WHERE {where_sql}
        """
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']

        # 排序
        sort_map = {
            "time_desc": "i.created_at DESC",
            "time_asc": "i.created_at ASC",
            "tags_desc": f"({tag_count_expr}) DESC",
            "tags_asc": f"({tag_count_expr}) ASC",
            "size_desc": "i.file_size DESC",
            "size_asc": "i.file_size ASC",
            "resolution_desc": "i.height DESC, i.width DESC",
            "resolution_asc": "i.height ASC, i.width ASC",
        }
        order_by = sort_map.get(request.sort_by, "i.created_at DESC")

        # 分页查询
        offset = (request.page - 1) * request.page_size
        paginated_query = f"""
            SELECT i.*, f.tags as tags_text
            FROM images i
            LEFT JOIN images_fts f ON i.id = f.rowid
            WHERE {where_sql}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
        """
        params.extend([request.page_size, offset])

        cursor.execute(paginated_query, params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            tags_text = row['tags_text'] if row['tags_text'] else row['tags']
            tags = tags_text.split(' ') if tags_text else []
            results.append({
                "md5": row['md5'],
                "filename": row['filename'],
                "tags": tags,
                "w": row['width'],
                "h": row['height'],
                "size": row['file_size'],
                "is_trash": 'trash_bin' in tags
            })

        return {"total": total, "results": results}


@router.post("/search")
async def search_images(request: Request):
    """搜索图片（兼容旧项目高级搜索/新项目简化搜索）"""
    data = await request.json()
    if isinstance(data, dict) and (
        "keywords" in data or "excludes" in data or "excludes_and" in data
    ):
        return await advanced_search(AdvancedSearchRequest(**data))

    return await search_images_simple(SearchRequest(**data))


async def advanced_search(request: AdvancedSearchRequest):
    """
    高级搜索（完全兼容旧项目搜索逻辑）
    - keywords: 二维数组，每个子数组是一个标签膨胀后的关键词列表（子数组内OR，子数组间AND）
    - excludes: 二维数组，每个子数组是一个排除标签膨胀后的关键词列表（子数组内OR，子数组间AND排除）
    - excludes_and: 三维数组，交集排除
    """
    where_clauses = ["1=1"]
    params = []
    tags_expr = "NULLIF(f.tags, '')"

    # 处理包含关键词组（AND 关系，每组内部是 OR 关系）
    for kw_group in request.keywords:
        if not kw_group:
            continue
        or_conditions = []
        for kw in kw_group:
            or_conditions.append(f"{tags_expr} LIKE ?")
            params.append(f"%{kw}%")
        if or_conditions:
            where_clauses.append(f"({' OR '.join(or_conditions)})")

    # 处理排除关键词组（AND 排除，每组内部是 OR 关系 -> 任一命中即排除）
    for ex_group in request.excludes:
        if not ex_group:
            continue
        or_conditions = []
        for ex in ex_group:
            or_conditions.append(f"{tags_expr} LIKE ?")
            params.append(f"%{ex}%")
        if or_conditions:
            where_clauses.append(f"NOT ({' OR '.join(or_conditions)})")

    # 处理交集排除关键词组（每个胶囊内的多个关键词组需要同时匹配才排除）
    for capsule in request.excludes_and:
        if not capsule:
            continue
        and_conditions = []
        for kw_group in capsule:
            if not kw_group:
                continue
            or_conditions = []
            for kw in kw_group:
                or_conditions.append(f"{tags_expr} LIKE ?")
                params.append(f"%{kw}%")
            if or_conditions:
                and_conditions.append(f"({' OR '.join(or_conditions)})")
        if and_conditions:
            where_clauses.append(f"NOT ({' AND '.join(and_conditions)})")

    # 处理包含扩展名
    if request.extensions:
        ext_conditions = []
        for ext in request.extensions:
            clean_ext = ext.lstrip('.')
            ext_conditions.append("i.filename LIKE ?")
            params.append(f"%.{clean_ext}")
        if ext_conditions:
            where_clauses.append(f"({' OR '.join(ext_conditions)})")

    # 处理排除扩展名
    if request.exclude_extensions:
        ext_conditions = []
        for ext in request.exclude_extensions:
            clean_ext = ext.lstrip('.')
            ext_conditions.append("i.filename LIKE ?")
            params.append(f"%.{clean_ext}")
        if ext_conditions:
            where_clauses.append(f"NOT ({' OR '.join(ext_conditions)})")

    # 标签数量筛选
    tag_count_expr = """
        CASE
            WHEN {tags_expr} IS NULL OR {tags_expr} = '' THEN 0
            ELSE LENGTH({tags_expr}) - LENGTH(REPLACE({tags_expr}, ' ', '')) + 1
        END
    """.format(tags_expr=tags_expr)

    if request.min_tags > 0:
        where_clauses.append(f"({tag_count_expr}) >= ?")
        params.append(request.min_tags)

    if request.max_tags >= 0:
        where_clauses.append(f"({tag_count_expr}) <= ?")
        params.append(request.max_tags)

    where_sql = " AND ".join(where_clauses)

    # 排序
    sort_map = {
        "date_desc": "i.created_at DESC",
        "date_asc": "i.created_at ASC",
        "size_desc": "i.file_size DESC",
        "size_asc": "i.file_size ASC",
        "resolution_desc": "i.height DESC, i.width DESC",
        "resolution_asc": "i.height ASC, i.width ASC",
    }
    order_sql = sort_map.get(request.sort_by, "i.created_at DESC")

    with get_connection() as conn:
        cursor = conn.cursor()

        # 获取总数
        count_query = f"""
            SELECT COUNT(*) as total
            FROM images i
            LEFT JOIN images_fts f ON i.id = f.rowid
            WHERE {where_sql}
        """
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']

        # 分页查询
        query = f"""
            SELECT i.*, f.tags as tags_text
            FROM images i
            LEFT JOIN images_fts f ON i.id = f.rowid
            WHERE {where_sql}
            ORDER BY {order_sql}
            LIMIT ? OFFSET ?
        """
        cursor.execute(query, params + [request.limit, request.offset])
        rows = cursor.fetchall()

        results = []
        for r in rows:
            tags_text = r['tags_text'] if r['tags_text'] else ""
            tags = tags_text.split(' ') if tags_text else []
            results.append({
                "md5": r['md5'],
                "filename": r['filename'],
                "tags": tags,
                "w": r['width'],
                "h": r['height'],
                "size": r['file_size'],
                "is_trash": 'trash_bin' in tags
            })

        return {"total": total, "results": results}


@router.get("/tags")
async def get_all_tags():
    """获取所有标签（按使用次数排序）"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 优先从 tags_dict 获取（按使用次数排序）
        cursor.execute("SELECT name FROM tags_dict ORDER BY use_count DESC")
        rows = cursor.fetchall()

        if rows:
            return {"tags": [row['name'] for row in rows]}

        # 降级：从 images 表获取
        cursor.execute("SELECT tags FROM images_fts WHERE tags != ''")
        all_tags = set()
        for row in cursor.fetchall():
            tags = row['tags'].split()
            all_tags.update(tags)

        return {"tags": sorted(all_tags)}


@router.get("/meta/tags")
async def get_meta_tags():
    """获取标签建议（按使用次数排序，兼容旧项目 API）"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM tags_dict ORDER BY use_count DESC")
        rows = cursor.fetchall()
        return [row['name'] for row in rows]
