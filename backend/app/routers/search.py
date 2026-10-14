"""
搜索路由 - 完整迁移旧项目搜索逻辑
"""
import threading
import time

from fastapi import APIRouter, Request
from pydantic import BaseModel
from ..database import get_connection
from ..models.image import SearchRequest, SearchResponse

router = APIRouter()


# ==============================================================
#  总数缓存
# ==============================================================
#
# 为什么需要：COUNT(*) 在 43 万行上要 ~13ms，是「浏览」接口里最贵的一步，
# 而且前端每次翻页都会重新请求一次，但绝大多数翻页时总数根本没变。
#
# 策略：
#   - 用「无过滤」的总数做基准缓存（浏览页最常见的情况，直接命中）
#   - 带过滤条件的查询不缓存（条件组合太多，命中率低）
#   - 用 images 表的行数变化做失效判断：行数变了（上传/删除）就重算，
#     这样不需要在别处显式清缓存，也不会返回过期的总数
#
_count_cache_lock = threading.Lock()
_count_cache: dict = {"total": None, "rowcount": None, "ts": 0.0}
_COUNT_CACHE_TTL = 300.0  # 兜底 TTL（秒）；行数未变时最多 5 分钟重算一次


def _current_rowcount(cursor) -> int:
    """
    取 images 表的行数（走 sqlite_sequence 或 MAX(id) 的近似值）。
    这里用 MAX(id) 做轻量指纹：它与实际行数同步变化，
    且能走主键索引，开销可忽略。
    """
    row = cursor.execute("SELECT MAX(id) FROM images").fetchone()
    return row[0] if row and row[0] is not None else 0


def get_cached_total(cursor, count_query: str, params: list):
    """
    带指纹失效的总数缓存。

    只有当查询是「无过滤」时（params 为空）才走缓存，
    因为浏览页就是这种请求，且数量最多。
    """
    if params:
        # 有过滤条件：不缓存，直接算
        cursor.execute(count_query, params)
        return cursor.fetchone()['total']

    now = time.time()
    fingerprint = _current_rowcount(cursor)

    with _count_cache_lock:
        fresh = (
            _count_cache["total"] is not None
            and _count_cache["rowcount"] == fingerprint
            and (now - _count_cache["ts"]) < _COUNT_CACHE_TTL
        )
        if fresh:
            return _count_cache["total"]

    # 缓存未命中或已失效：重算（放在锁外，避免阻塞其它请求）
    cursor.execute(count_query, params)
    total = cursor.fetchone()['total']

    with _count_cache_lock:
        _count_cache["total"] = total
        _count_cache["rowcount"] = fingerprint
        _count_cache["ts"] = now

    return total


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

    # 游标分页（可选，仅时间排序有意义）
    # 排序键是 (created_at, id) 复合键，两个值必须一起回传。
    # 填了游标则忽略 offset，翻页代价恒为 O(1)。
    cursor_id: int | None = None
    cursor_ts: str | None = None


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

        # ---------------------------------------------------------------
        # 【性能关键】是否真的需要 JOIN images_fts？
        #
        # images_fts 是 FTS5 外部内容虚拟表。在 LEFT JOIN 下它**无法走索引**，
        # 执行计划会变成 `SCAN f VIRTUAL TABLE ... LEFT-JOIN`，
        # 必须为每一行回填一次，43 万行下 COUNT 要 4.3 秒（纯 images 表只要 9ms）。
        #
        # 而大多数请求（无标签过滤、不按标签数排序）根本用不到 tags，
        # 这些请求就不该 JOIN。实测这是浏览页最主要的瓶颈。
        # ---------------------------------------------------------------
        need_fts = bool(
            expanded_include
            or request.exclude_tags
            or (request.min_tags is not None and request.min_tags > 0)
            or (request.max_tags is not None and request.max_tags >= 0)
            or request.sort_by in ("tags_desc", "tags_asc")
        )

        # 构建查询
        where_clauses = ["1=1"]
        params = []
        # 需要 tags 时优先取 FTS 的（外部内容表，与 images.tags 同步）；
        # 不需要时用 images.tags，避免 JOIN。
        tags_expr = "NULLIF(f.tags, '')" if need_fts else "NULLIF(i.tags, '')"
        # 计数查询即使需要 tags 过滤，也可以直接查 images.tags（内容等价），
        # 从而完全避免 JOIN —— 这是把 COUNT 从 4.3s 降到 ~10ms 的关键。
        tags_expr_count = "NULLIF(i.tags, '')"

        # 包含标签（OR 关系）
        if expanded_include:
            or_conditions = []
            for tag in expanded_include:
                or_conditions.append(f"{tags_expr} LIKE ?")
                params.append(f"%{tag}%")
            where_clauses.append(f"({' OR '.join(or_conditions)})")

        # 排除标签
        for exclude_tag in request.exclude_tags:
            # 【重要】必须用 COALESCE(tags,'') 包一层。
            #
            # 原因：tags 为 NULL 时（43 万张无标签的图），
            # `NULL NOT LIKE '%x%'` 的结果是 NULL 而不是 TRUE，
            # 在 WHERE 里视为不通过 —— 于是「排除某个标签」会把
            # 所有无标签的图一起排除掉（实测：exclude=['猫'] 只剩 174 行，
            # 而正确结果应是 43 万左右）。
            # COALESCE 后空标签变成 ''，'' NOT LIKE '%x%' 为 TRUE，语义才正确。
            where_clauses.append(f"COALESCE({tags_expr}, '') NOT LIKE ?")
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

        # 计数用的 WHERE：把 tags 引用换成 i.tags，这样不需要 JOIN 也能算。
        # images_fts 是 external content 表，tags 内容与 images.tags 一致，
        # 所以过滤结果等价，但省掉了 43 万次虚拟表回填。
        count_where_sql = where_sql.replace("f.tags", "i.tags") if need_fts else where_sql

        # 获取总数（不 JOIN，实测 4.3s -> ~10ms；无过滤时再走缓存 -> ~0ms）
        count_query = f"""
            SELECT COUNT(*) as total
            FROM images i
            WHERE {count_where_sql}
        """
        total = get_cached_total(cursor, count_query, params)

        # 排序
        #
        # 【时间语义】created_at 已用旧库的 modified_time 回填为**真实修改时间**，
        # 跨度 2025-09 ~ 2026-10、40 万+ 个不同取值，可以真实反映图片新旧。
        # 因此时间排序用 created_at。
        #
        # 【为什么带 id 兜底】created_at 仍可能同秒重复（如批量导入），
        # 只按它排序时同值行的顺序不稳定，翻页会出现重复/漏图。
        # 追加 id 作为次级键保证全序稳定。
        #
        # 【必须配套索引】`created_at DESC, id DESC` 如果没有复合索引，
        # SQLite 会对第二列做 TEMP B-TREE 排序，深翻页实测会到 1 秒。
        # 已建 idx_images_created_id 消除该排序（深翻页降到 ~29ms）。
        sort_map = {
            "time_desc": "i.created_at DESC, i.id DESC",
            "time_asc": "i.created_at ASC, i.id ASC",
            "tags_desc": f"({tag_count_expr}) DESC, i.created_at DESC, i.id DESC",
            "tags_asc": f"({tag_count_expr}) ASC, i.created_at DESC, i.id DESC",
            "size_desc": "i.file_size DESC, i.created_at DESC, i.id DESC",
            "size_asc": "i.file_size ASC, i.created_at DESC, i.id DESC",
            "resolution_desc": "i.height DESC, i.width DESC, i.created_at DESC, i.id DESC",
            "resolution_asc": "i.height ASC, i.width ASC, i.created_at DESC, i.id DESC",
        }
        order_by = sort_map.get(request.sort_by, "i.created_at DESC, i.id DESC")

        # 分页查询
        #
        # 只有确实需要 tags（按标签过滤/排序）时才 JOIN images_fts。
        # 浏览页这类「无过滤、按时间倒序」的请求因此完全不碰虚拟表，
        # 深翻页时也不会因为 JOIN 而放大代价。
        #
        # 支持两种分页方式：
        #   1) cursor_id / cursor_ts：keyset 分页，O(1)，推荐给前端「下一页」用
        #   2) page：传统 OFFSET 分页，保留兼容旧前端
        #
        # keyset 仅对时间排序有意义（time_desc / time_asc）。
        # 由于排序键是 (created_at, id) 复合键，游标也必须带**两个**值，
        # 否则同一 created_at 的行会被跳过或重复。
        use_keyset = (
            request.cursor_id is not None
            and request.cursor_ts is not None
            and request.sort_by in ("time_desc", "time_asc")
        )

        page_where_sql = where_sql
        page_params = list(params)

        if use_keyset:
            # 复合游标：(created_at, id) 的严格不等比较，等价于元组比较
            if request.sort_by == "time_asc":
                page_where_sql += " AND (i.created_at > ? OR (i.created_at = ? AND i.id > ?))"
            else:
                page_where_sql += " AND (i.created_at < ? OR (i.created_at = ? AND i.id < ?))"
            page_params.extend([request.cursor_ts, request.cursor_ts, request.cursor_id])

        page_join = "LEFT JOIN images_fts f ON i.id = f.rowid" if need_fts else ""
        page_tags = "f.tags" if need_fts else "i.tags"

        if use_keyset:
            # 无 OFFSET：直接按主键定位起点，任意深度代价相同
            paginated_query = f"""
                SELECT i.*, {page_tags} as tags_text
                FROM images i
                {page_join}
                WHERE {page_where_sql}
                ORDER BY {order_by}
                LIMIT ?
            """
            page_params.append(request.page_size)
        else:
            offset = (request.page - 1) * request.page_size
            paginated_query = f"""
                SELECT i.*, {page_tags} as tags_text
                FROM images i
                {page_join}
                WHERE {page_where_sql}
                ORDER BY {order_by}
                LIMIT ? OFFSET ?
            """
            page_params.extend([request.page_size, offset])

        cursor.execute(paginated_query, page_params)
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
                "is_trash": 'trash_bin' in tags,
                # 供前端游标分页使用（仅时间排序有意义）
                "id": row['id'],
                "created_at": row['created_at'],
            })

        # 下一页游标：复合键 (created_at, id)，前端原样回传即可
        next_cursor = None
        next_cursor_ts = None
        if results and request.sort_by in ("time_desc", "time_asc"):
            next_cursor = results[-1]["id"]
            next_cursor_ts = results[-1]["created_at"]

        return {
            "total": total,
            "results": results,
            "next_cursor": next_cursor,
            "next_cursor_ts": next_cursor_ts,
        }


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

    # ---------------------------------------------------------------
    # 【性能关键】同 search_images_simple：只有真的需要 tags 时才 JOIN FTS。
    #
    # images_fts 是 FTS5 外部内容表，LEFT JOIN 下无法走索引，
    # 必须逐行回填；43 万行下 COUNT 要 4.3 秒。
    # 而「浏览页」这类空条件请求根本不需要 tags。
    #
    # tags 内容与 images.tags 一致（外部内容表），所以即使需要过滤，
    # 直接查 i.tags 结果等价，却能完全省掉 JOIN。
    # ---------------------------------------------------------------
    need_fts = bool(
        request.keywords
        or request.excludes
        or request.excludes_and
        or request.min_tags > 0
        or request.max_tags >= 0
        or request.sort_by in ("tags_desc", "tags_asc")
    )

    tags_expr = "NULLIF(i.tags, '')"

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
    #
    # 【重要】必须用 COALESCE(tags,'') 包一层。
    # tags 为 NULL 时（43 万张无标签的图），`NOT (NULL LIKE '%x%')` 结果是 NULL，
    # 在 WHERE 里视为不通过 —— 于是「排除某标签」会把所有无标签图一起排掉
    # （实测 excludes=[['trash_bin']] 只剩 175 行，正确应为 43 万左右）。
    for ex_group in request.excludes:
        if not ex_group:
            continue
        or_conditions = []
        for ex in ex_group:
            or_conditions.append(f"COALESCE({tags_expr}, '') LIKE ?")
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
                or_conditions.append(f"COALESCE({tags_expr}, '') LIKE ?")
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
    #
    # 【时间语义】created_at 已回填为**真实修改时间**（见 backfill_real_time.py），
    # 可以真实反映图片新旧；带 id 兜底保证同秒内顺序稳定。
    # 需配套 idx_images_created_id 复合索引，否则深翻页会因 TEMP B-TREE 变慢。
    sort_map = {
        "date_desc": "i.created_at DESC, i.id DESC",
        "date_asc": "i.created_at ASC, i.id ASC",
        "size_desc": "i.file_size DESC, i.created_at DESC, i.id DESC",
        "size_asc": "i.file_size ASC, i.created_at DESC, i.id DESC",
        "resolution_desc": "i.height DESC, i.width DESC, i.created_at DESC, i.id DESC",
        "resolution_asc": "i.height ASC, i.width ASC, i.created_at DESC, i.id DESC",
    }
    order_sql = sort_map.get(request.sort_by, "i.created_at DESC, i.id DESC")

    with get_connection() as conn:
        cursor = conn.cursor()

        # 获取总数（不 JOIN；无过滤时走缓存 -> 约 0ms）
        count_query = f"""
            SELECT COUNT(*) as total
            FROM images i
            WHERE {where_sql}
        """
        total = get_cached_total(cursor, count_query, params)

        # 游标分页：排序键是 (created_at, id)，必须用复合比较，
        # 否则同一 created_at 的行会被跳过或重复。
        use_cursor = (
            request.cursor_id is not None
            and request.cursor_ts is not None
            and request.sort_by in ("date_desc", "date_asc")
        )
        page_where = where_sql
        page_params = list(params)
        if use_cursor:
            if request.sort_by == "date_asc":
                page_where += " AND (i.created_at > ? OR (i.created_at = ? AND i.id > ?))"
            else:
                page_where += " AND (i.created_at < ? OR (i.created_at = ? AND i.id < ?))"
            page_params.extend([request.cursor_ts, request.cursor_ts, request.cursor_id])

        # 分页查询：只在需要 tags 时才 JOIN（同 count 的处理）
        page_join = "LEFT JOIN images_fts f ON i.id = f.rowid" if need_fts else ""
        page_tags = "f.tags" if need_fts else "i.tags"

        if use_cursor:
            query = f"""
                SELECT i.*, {page_tags} as tags_text
                FROM images i
                {page_join}
                WHERE {page_where}
                ORDER BY {order_sql}
                LIMIT ?
            """
            page_params.append(request.limit)
        else:
            query = f"""
                SELECT i.*, {page_tags} as tags_text
                FROM images i
                {page_join}
                WHERE {page_where}
                ORDER BY {order_sql}
                LIMIT ? OFFSET ?
            """
            page_params.extend([request.limit, request.offset])

        cursor.execute(query, page_params)
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
                "is_trash": 'trash_bin' in tags,
                # 供前端游标分页使用（仅时间排序有意义）
                "id": r['id'],
                "created_at": r['created_at'],
            })

        # 下一页游标：复合键 (created_at, id)
        next_cursor = None
        next_cursor_ts = None
        if results and request.sort_by in ("date_desc", "date_asc"):
            next_cursor = results[-1]["id"]
            next_cursor_ts = results[-1]["created_at"]

        return {
            "total": total,
            "results": results,
            "next_cursor": next_cursor,
            "next_cursor_ts": next_cursor_ts,
        }

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
