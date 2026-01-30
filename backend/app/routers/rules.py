"""
规则树路由
"""
from fastapi import APIRouter, HTTPException, Response
from ..database import get_connection, get_rules_version, increment_rules_version
from ..models.rule import (
    GroupCreate, GroupResponse, KeywordCreate,
    RulesTreeResponse, KeywordResponse, CASRequest,
    GroupUpdate, GroupToggle, GroupBatchRequest,
    HierarchyAddRequest, HierarchyRemoveRequest, HierarchyBatchMoveRequest,
    KeywordToggle
)

router = APIRouter()


def build_rules_tree() -> list[GroupResponse]:
    """构建规则树结构"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 获取所有组（包含 enabled 字段）
        cursor.execute("SELECT id, name, parent_id, enabled FROM search_groups ORDER BY id")
        groups = {row['id']: {
            'id': row['id'],
            'name': row['name'],
            'parent_id': row['parent_id'],
            'enabled': bool(row['enabled']) if row['enabled'] is not None else True,
            'keywords': [],
            'children': []
        } for row in cursor.fetchall()}

        # 获取所有关键词（包含 enabled 字段）
        cursor.execute("SELECT id, keyword, group_id, enabled FROM search_keywords")
        for row in cursor.fetchall():
            if row['group_id'] in groups:
                groups[row['group_id']]['keywords'].append(
                    KeywordResponse(
                        id=row['id'],
                        keyword=row['keyword'],
                        group_id=row['group_id'],
                        enabled=bool(row['enabled']) if row['enabled'] is not None else True
                    )
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
                enabled=g['enabled'],
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


@router.post("/keywords/{keyword_id}/toggle")
async def toggle_keyword(keyword_id: int, data: KeywordToggle):
    """切换关键词启用状态"""
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

        # 更新启用状态
        cursor.execute(
            "UPDATE search_keywords SET enabled = ? WHERE id = ?",
            (1 if data.enabled else 0, keyword_id)
        )

        # 递增版本号
        new_version = increment_rules_version(
            conn, data.client_id, "toggle_keyword",
            f"keyword_id={keyword_id}, enabled={data.enabled}"
        )
        conn.commit()

        return {"success": True, "new_version": new_version}


@router.put("/groups/{group_id}")
async def update_group(group_id: int, data: GroupUpdate):
    """更新规则组（重命名、移动父节点、启用/禁用）"""
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
        cursor.execute("SELECT id, name, parent_id FROM search_groups WHERE id = ?", (group_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="规则组不存在")

        updates = []
        params = []
        details = []

        if data.name is not None:
            updates.append("name = ?")
            params.append(data.name)
            details.append(f"name={data.name}")

        if data.enabled is not None:
            updates.append("enabled = ?")
            params.append(1 if data.enabled else 0)
            details.append(f"enabled={data.enabled}")

        if data.parent_id is not None:
            # 检查新父节点是否存在
            if data.parent_id != 0:
                cursor.execute("SELECT id FROM search_groups WHERE id = ?", (data.parent_id,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=404, detail="父组不存在")
            updates.append("parent_id = ?")
            params.append(data.parent_id if data.parent_id != 0 else None)
            details.append(f"parent_id={data.parent_id}")

        if not updates:
            return {"success": True, "new_version": current_version, "message": "无更新"}

        params.append(group_id)
        cursor.execute(f"UPDATE search_groups SET {', '.join(updates)} WHERE id = ?", params)

        # 如果移动了父节点，需要重建层级关系
        if data.parent_id is not None:
            rebuild_hierarchy_for_group(cursor, group_id, data.parent_id if data.parent_id != 0 else None)

        new_version = increment_rules_version(
            conn, data.client_id, "update_group",
            f"group_id={group_id}, {', '.join(details)}"
        )
        conn.commit()

        return {"success": True, "new_version": new_version}


@router.post("/groups/{group_id}/toggle")
async def toggle_group(group_id: int, data: GroupToggle):
    """切换规则组启用状态"""
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

        cursor.execute(
            "UPDATE search_groups SET enabled = ? WHERE id = ?",
            (1 if data.enabled else 0, group_id)
        )

        new_version = increment_rules_version(
            conn, data.client_id, "toggle_group",
            f"group_id={group_id}, enabled={data.enabled}"
        )
        conn.commit()

        return {"success": True, "new_version": new_version, "enabled": data.enabled}


@router.post("/groups/batch")
async def batch_groups(data: GroupBatchRequest):
    """批量操作规则组"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # CAS 版本检查
        current_version = get_rules_version()
        if data.base_version != current_version:
            raise HTTPException(
                status_code=409,
                detail=f"版本冲突: 期望 {data.base_version}, 当前 {current_version}"
            )

        affected = 0

        if data.action == "delete":
            for gid in data.group_ids:
                cursor.execute("DELETE FROM search_groups WHERE id = ?", (gid,))
                affected += cursor.rowcount

        elif data.action == "enable":
            for gid in data.group_ids:
                cursor.execute("UPDATE search_groups SET enabled = 1 WHERE id = ?", (gid,))
                affected += cursor.rowcount

        elif data.action == "disable":
            for gid in data.group_ids:
                cursor.execute("UPDATE search_groups SET enabled = 0 WHERE id = ?", (gid,))
                affected += cursor.rowcount

        elif data.action == "move":
            for gid in data.group_ids:
                cursor.execute(
                    "UPDATE search_groups SET parent_id = ? WHERE id = ?",
                    (data.target_parent_id, gid)
                )
                if cursor.rowcount > 0:
                    rebuild_hierarchy_for_group(cursor, gid, data.target_parent_id)
                    affected += 1

        else:
            raise HTTPException(status_code=400, detail=f"未知操作: {data.action}")

        new_version = increment_rules_version(
            conn, data.client_id, "batch_groups",
            f"action={data.action}, group_ids={data.group_ids}, affected={affected}"
        )
        conn.commit()

        return {"success": True, "new_version": new_version, "affected": affected}


@router.post("/hierarchy/add")
async def add_hierarchy(data: HierarchyAddRequest):
    """添加层级关系（将子节点移动到父节点下）"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # CAS 版本检查
        current_version = get_rules_version()
        if data.base_version != current_version:
            raise HTTPException(
                status_code=409,
                detail=f"版本冲突: 期望 {data.base_version}, 当前 {current_version}"
            )

        # 检查节点是否存在
        cursor.execute("SELECT id FROM search_groups WHERE id = ?", (data.child_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="子节点不存在")

        cursor.execute("SELECT id FROM search_groups WHERE id = ?", (data.parent_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="父节点不存在")

        # 更新父节点
        cursor.execute(
            "UPDATE search_groups SET parent_id = ? WHERE id = ?",
            (data.parent_id, data.child_id)
        )

        # 重建层级关系
        rebuild_hierarchy_for_group(cursor, data.child_id, data.parent_id)

        new_version = increment_rules_version(
            conn, data.client_id, "add_hierarchy",
            f"child_id={data.child_id}, parent_id={data.parent_id}"
        )
        conn.commit()

        return {"success": True, "new_version": new_version}


@router.post("/hierarchy/remove")
async def remove_hierarchy(data: HierarchyRemoveRequest):
    """删除层级关系（将子节点移动到根级别）"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # CAS 版本检查
        current_version = get_rules_version()
        if data.base_version != current_version:
            raise HTTPException(
                status_code=409,
                detail=f"版本冲突: 期望 {data.base_version}, 当前 {current_version}"
            )

        # 检查节点是否存在
        cursor.execute("SELECT id, parent_id FROM search_groups WHERE id = ?", (data.child_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="子节点不存在")

        # 更新为根节点
        cursor.execute(
            "UPDATE search_groups SET parent_id = NULL WHERE id = ?",
            (data.child_id,)
        )

        # 重建层级关系
        rebuild_hierarchy_for_group(cursor, data.child_id, None)

        new_version = increment_rules_version(
            conn, data.client_id, "remove_hierarchy",
            f"child_id={data.child_id}, old_parent_id={data.parent_id}"
        )
        conn.commit()

        return {"success": True, "new_version": new_version}


@router.post("/hierarchy/batch_move")
async def batch_move_hierarchy(data: HierarchyBatchMoveRequest):
    """批量移动层级"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # CAS 版本检查
        current_version = get_rules_version()
        if data.base_version != current_version:
            raise HTTPException(
                status_code=409,
                detail=f"版本冲突: 期望 {data.base_version}, 当前 {current_version}"
            )

        # 检查新父节点是否存在
        if data.new_parent_id is not None:
            cursor.execute("SELECT id FROM search_groups WHERE id = ?", (data.new_parent_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="目标父节点不存在")

        affected = 0
        for gid in data.group_ids:
            cursor.execute(
                "UPDATE search_groups SET parent_id = ? WHERE id = ?",
                (data.new_parent_id, gid)
            )
            if cursor.rowcount > 0:
                rebuild_hierarchy_for_group(cursor, gid, data.new_parent_id)
                affected += 1

        new_version = increment_rules_version(
            conn, data.client_id, "batch_move_hierarchy",
            f"group_ids={data.group_ids}, new_parent_id={data.new_parent_id}, affected={affected}"
        )
        conn.commit()

        return {"success": True, "new_version": new_version, "affected": affected}


def rebuild_hierarchy_for_group(cursor, group_id: int, new_parent_id: int | None):
    """重建单个组的层级关系"""
    # 删除该组作为后代的所有关系（除了自己到自己）
    cursor.execute("""
        DELETE FROM search_hierarchy
        WHERE descendant_id = ? AND ancestor_id != ?
    """, (group_id, group_id))

    # 确保自己到自己的关系存在
    cursor.execute("""
        INSERT OR IGNORE INTO search_hierarchy (ancestor_id, descendant_id, depth)
        VALUES (?, ?, 0)
    """, (group_id, group_id))

    # 如果有新父节点，继承父节点的所有祖先关系
    if new_parent_id is not None:
        cursor.execute("""
            INSERT OR REPLACE INTO search_hierarchy (ancestor_id, descendant_id, depth)
            SELECT ancestor_id, ?, depth + 1
            FROM search_hierarchy
            WHERE descendant_id = ?
        """, (group_id, new_parent_id))

    # 递归更新所有子孙节点的层级关系
    cursor.execute("""
        SELECT id FROM search_groups WHERE parent_id = ?
    """, (group_id,))
    children = cursor.fetchall()
    for child in children:
        rebuild_hierarchy_for_group(cursor, child['id'], group_id)
