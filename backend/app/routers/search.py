"""
搜索路由
"""
from fastapi import APIRouter
from ..database import get_connection
from ..models.image import SearchRequest, SearchResponse, ImageResponse

router = APIRouter()


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
                WHERE sk.keyword = ?
            """, (tag,))

            group_ids = [row['id'] for row in cursor.fetchall()]

            for group_id in group_ids:
                # 获取所有子孙节点的关键词
                cursor.execute("""
                    SELECT DISTINCT sk.keyword
                    FROM search_keywords sk
                    JOIN search_hierarchy sh ON sk.group_id = sh.descendant_id
                    WHERE sh.ancestor_id = ?
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


@router.post("/search", response_model=SearchResponse)
async def search_images(request: SearchRequest):
    """搜索图片"""
    # 膨胀包含标签
    expanded_include = expand_tags_with_rules(request.include_tags)

    with get_connection() as conn:
        cursor = conn.cursor()

        # 构建查询
        if expanded_include:
            # 使用 FTS5 搜索
            fts_query = " OR ".join(f'"{tag}"' for tag in expanded_include)
            base_query = f"""
                SELECT i.* FROM images i
                JOIN images_fts fts ON i.id = fts.rowid
                WHERE images_fts MATCH ?
            """
            params = [fts_query]
        else:
            base_query = "SELECT * FROM images i WHERE 1=1"
            params = []

        # 排除标签
        for exclude_tag in request.exclude_tags:
            base_query += " AND i.tags NOT LIKE ?"
            params.append(f"%{exclude_tag}%")

        # 获取总数
        count_query = f"SELECT COUNT(*) as total FROM ({base_query})"
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']

        # 分页查询
        offset = (request.page - 1) * request.page_size
        paginated_query = f"{base_query} ORDER BY i.created_at DESC LIMIT ? OFFSET ?"
        params.extend([request.page_size, offset])

        cursor.execute(paginated_query, params)
        rows = cursor.fetchall()

        images = [ImageResponse(**dict(row)) for row in rows]

        return SearchResponse(
            images=images,
            total=total,
            page=request.page,
            page_size=request.page_size,
            expanded_tags=expanded_include,
        )


@router.get("/tags")
async def get_all_tags():
    """获取所有标签"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT tags FROM images WHERE tags != ''")

        all_tags = set()
        for row in cursor.fetchall():
            tags = row['tags'].split()
            all_tags.update(tags)

        return {"tags": sorted(all_tags)}
