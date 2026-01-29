"""
规则树路由
"""
from fastapi import APIRouter, HTTPException, Response
from ..database import get_connection, get_rules_version, increment_rules_version
from ..models.rule import (
    GroupCreate, GroupResponse, KeywordCreate,
    RulesTreeResponse, KeywordResponse, CASRequest
)

router = APIRouter()


def build_rules_tree() -> list[GroupResponse]:
    """构建规则树结构"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 获取所有组
        cursor.execute("SELECT id, name, parent_id FROM search_groups ORDER BY id")
        groups = {row['id']: {
            'id': row['id'],
            'name': row['name'],
            'parent_id': row['parent_id'],
            'keywords': [],
            'children': []
        } for row in cursor.fetchall()}

        # 获取所有关键词
        cursor.execute("SELECT id, keyword, group_id FROM search_keywords")
        for row in cursor.fetchall():
            if row['group_id'] in groups:
                groups[row['group_id']]['keywords'].append(
                    KeywordResponse(id=row['id'], keyword=row['keyword'], group_id=row['group_id'])
                )

        # 构建树结构
        root_groups = []
        for group in groups.values():
            if group['parent_id'] is None:
                root_groups.append(group)
            elif group['parent_id'] in groups:
                groups[group['parent_id']]['children'].append(group)

        def to_response(g: dict) -> GroupResponse:
            return GroupResponse(
                id=g['id'],
                name=g['name'],
                keywords=g['keywords'],
                children=[to_response(c) for c in g['children']]
            )

        return [to_response(g) for g in root_groups]


@router.get("", response_model=RulesTreeResponse)
async def get_rules_tree(response: Response, if_none_match: str | None = None):
    """获取规则树（支持 ETag 缓存）"""
    current_version = get_rules_version()

    # ETag 检查
    if if_none_match and if_none_match == str(current_version):
        response.status_code = 304
        return Response(status_code=304)

    tree = build_rules_tree()
    response.headers["ETag"] = str(current_version)

    return RulesTreeResponse(version=current_version, groups=tree)


@router.post("/groups")
async def create_group(data: GroupCreate):
    """创建规则组"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # CAS 版本检查
        current_version = get_rules_version()
        if data.base_version != current_version:
            raise HTTPException(
                status_code=409,
                detail=f"版本冲突: 期望 {data.base_version}, 当前 {current_version}"
            )

        # 检查父组是否存在
        if data.parent_id is not None:
            cursor.execute("SELECT id FROM search_groups WHERE id = ?", (data.parent_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="父组不存在")

        # 创建组
        cursor.execute(
            "INSERT INTO search_groups (name, parent_id) VALUES (?, ?)",
            (data.name, data.parent_id)
        )
        group_id = cursor.lastrowid

        # 更新层级关系表
        # 自己到自己的关系
        cursor.execute(
            "INSERT INTO search_hierarchy (ancestor_id, descendant_id, depth) VALUES (?, ?, 0)",
            (group_id, group_id)
        )

        # 继承父节点的所有祖先关系
        if data.parent_id is not None:
            cursor.execute("""
                INSERT INTO search_hierarchy (ancestor_id, descendant_id, depth)
                SELECT ancestor_id, ?, depth + 1
                FROM search_hierarchy
                WHERE descendant_id = ?
            """, (group_id, data.parent_id))

        # 递增版本号
        new_version = increment_rules_version(
            conn, data.client_id, "create_group",
            f"name={data.name}, parent_id={data.parent_id}"
        )
        conn.commit()

        return {"success": True, "id": group_id, "new_version": new_version}


@router.post("/groups/{group_id}/keywords")
async def add_keyword(group_id: int, data: KeywordCreate):
    """添加关键词到组"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # CAS 版本检查
        current_version = get_rules_version()
        if data.base_version != current_version:
            raise HTTPException(
                status_code=409,
                detail=f"版本冲突: 期望 {data.base_version}, 当前 {current_version}"
            )

        # 检查组是否存在
        cursor.execute("SELECT id FROM search_groups WHERE id = ?", (group_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="规则组不存在")

        # 添加关键词
        cursor.execute(
            "INSERT INTO search_keywords (keyword, group_id) VALUES (?, ?)",
            (data.keyword, group_id)
        )
        keyword_id = cursor.lastrowid

        # 递增版本号
        new_version = increment_rules_version(
            conn, data.client_id, "add_keyword",
            f"keyword={data.keyword}, group_id={group_id}"
        )
        conn.commit()

        return {"success": True, "id": keyword_id, "new_version": new_version}


@router.delete("/groups/{group_id}")
async def delete_group(group_id: int, data: CASRequest):
    """删除规则组（级联删除子组和关键词）"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # CAS 版本检查
        current_version = get_rules_version()
        if data.base_version != current_version:
            raise HTTPException(
                status_code=409,
                detail=f"版本冲突: 期望 {data.base_version}, 当前 {current_version}"
            )

        # 检查组是否存在
        cursor.execute("SELECT name FROM search_groups WHERE id = ?", (group_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="规则组不存在")

        group_name = row['name']

        # 删除组（级联删除由外键约束处理）
        cursor.execute("DELETE FROM search_groups WHERE id = ?", (group_id,))

        # 递增版本号
        new_version = increment_rules_version(
            conn, data.client_id, "delete_group",
            f"group_id={group_id}, name={group_name}"
        )
        conn.commit()

        return {"success": True, "new_version": new_version}


@router.delete("/keywords/{keyword_id}")
async def delete_keyword(keyword_id: int, data: CASRequest):
    """删除关键词"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # CAS 版本检查
        current_version = get_rules_version()
        if data.base_version != current_version:
            raise HTTPException(
                status_code=409,
                detail=f"版本冲突: 期望 {data.base_version}, 当前 {current_version}"
            )

        # 检查关键词是否存在
        cursor.execute("SELECT keyword FROM search_keywords WHERE id = ?", (keyword_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="关键词不存在")

        # 删除关键词
        cursor.execute("DELETE FROM search_keywords WHERE id = ?", (keyword_id,))

        # 递增版本号
        new_version = increment_rules_version(
            conn, data.client_id, "delete_keyword",
            f"keyword_id={keyword_id}, keyword={row['keyword']}"
        )
        conn.commit()

        return {"success": True, "new_version": new_version}
