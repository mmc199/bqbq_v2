"""
系统路由（导入导出、版本等）
"""
import json
import io
from datetime import datetime
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Union
from ..database import get_connection, get_rules_version, ensure_hierarchy_edges, rebuild_hierarchy_from_edges

router = APIRouter()


class CheckMD5Request(BaseModel):
    md5: str
    refresh_time: bool = False


class UpdateTagsRequest(BaseModel):
    md5: str
    tags: Union[list[str], str]
    client_id: str | None = None
    base_version: int | None = None


@router.get("/version")
async def get_version():
    """获取当前规则版本"""
    return {"version": get_rules_version()}


@router.post("/check_md5")
async def check_md5_compat(data: CheckMD5Request):
    """旧项目兼容：/api/check_md5"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename FROM images WHERE md5 = ?", (data.md5,))
        row = cursor.fetchone()

        if row:
            time_refreshed = False
            if data.refresh_time:
                cursor.execute(
                    "UPDATE images SET created_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (row['id'],)
                )
                conn.commit()
                time_refreshed = True

            return {
                "exists": True,
                "filename": row['filename'],
                "time_refreshed": time_refreshed
            }

        return {"exists": False}


@router.post("/update_tags")
async def update_tags_compat(data: UpdateTagsRequest):
    """旧项目兼容：/api/update_tags"""
    tags_list = data.tags if isinstance(data.tags, list) else str(data.tags).split()
    tags_str = " ".join([t for t in tags_list if t])

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM images WHERE md5 = ?", (data.md5,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="图片不存在")

        cursor.execute("UPDATE images SET tags = ? WHERE md5 = ?", (tags_str, data.md5))
        conn.commit()

        return {"success": True}


@router.get("/export")
async def export_data():
    """导出所有数据（兼容旧项目格式）"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 导出图片数据（转换为旧项目格式）
        cursor.execute("""
            SELECT i.*, f.tags as tags_text
            FROM images i
            LEFT JOIN images_fts f ON i.id = f.rowid
        """)
        images_data = []
        for row in cursor.fetchall():
            tags_text = row['tags_text'] if row['tags_text'] else ""
            tags = tags_text.split(' ') if tags_text else []
            images_data.append({
                "md5": row['md5'],
                "filename": row['filename'],
                "created_at": row['created_at'],
                "width": row['width'],
                "height": row['height'],
                "size": row['file_size'],
                "tags": tags
            })

        # 导出规则组（转换为旧项目格式）
        cursor.execute("SELECT id as group_id, name as group_name, COALESCE(enabled, 1) as is_enabled FROM search_groups")
        groups = [dict(row) for row in cursor.fetchall()]

        # 导出关键词（转换为旧项目格式）
        cursor.execute("SELECT keyword, group_id, COALESCE(enabled, 1) as is_enabled FROM search_keywords")
        keywords = [dict(row) for row in cursor.fetchall()]

        # 导出层级关系（旧项目边表 parent_id/child_id）
        ensure_hierarchy_edges(conn)
        cursor.execute("SELECT parent_id, child_id FROM search_hierarchy_edges")
        hierarchy = [dict(row) for row in cursor.fetchall()]

        # 导出标签字典
        cursor.execute("SELECT name, use_count FROM tags_dict")
        tags_dict = [{"name": row['name'], "use_count": row['use_count']} for row in cursor.fetchall()]

        # 构建兼容旧项目的导出格式
        export_data = {
            "export_time": datetime.now().timestamp(),
            "version": "1.0",
            "images": images_data,
            "rules": {
                "version_id": get_rules_version(),
                "groups": groups,
                "keywords": keywords,
                "hierarchy": hierarchy
            },
            "tags_dict": tags_dict
        }

        # 转换为 JSON
        json_str = json.dumps(export_data, ensure_ascii=False, indent=2, default=str)
        buffer = io.BytesIO(json_str.encode('utf-8'))

        return StreamingResponse(
            buffer,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=bqbq_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            }
        )


@router.get("/export/all")
async def export_all_compat():
    """旧项目兼容：/api/export/all"""
    return await export_data()


@router.post("/import")
async def import_data(data: dict = Body(...)):
    """导入数据（兼容旧项目格式）"""

    imported_counts = {
        "images": 0,
        "skipped_images": 0,
        "groups": 0,
        "keywords": 0,
    }

    with get_connection() as conn:
        cursor = conn.cursor()

        # 检测数据格式（旧项目 vs 新项目）
        is_old_format = "rules" in data and "images" in data

        if is_old_format:
            # 旧项目格式导入
            # 导入图片（更新已存在的标签）
            for img in data.get("images", []):
                md5 = img.get('md5')
                if not md5:
                    continue

                # 检查是否已存在
                cursor.execute("SELECT id FROM images WHERE md5 = ?", (md5,))
                existing = cursor.fetchone()

                tags = img.get('tags', [])
                tags_str = ' '.join(tags) if isinstance(tags, list) else str(tags)

                if existing:
                    # 更新标签
                    cursor.execute("UPDATE images SET tags = ? WHERE md5 = ?", (tags_str, md5))
                    imported_counts["skipped_images"] += 1
                else:
                    # 新图片
                    cursor.execute(
                        """INSERT INTO images (md5, filename, tags, file_size, width, height, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, datetime(?, 'unixepoch'))""",
                        (md5, img.get('filename', f"{md5}.jpg"), tags_str,
                         img.get('size', 0), img.get('width', 0), img.get('height', 0),
                         img.get('created_at', datetime.now().timestamp()))
                    )
                    imported_counts["images"] += 1

            # 清空并重建规则树
            ensure_hierarchy_edges(conn)
            cursor.execute("DELETE FROM search_keywords")
            cursor.execute("DELETE FROM search_hierarchy_edges")
            cursor.execute("DELETE FROM search_hierarchy")
            cursor.execute("DELETE FROM search_groups")

            rules = data.get("rules", {})
            group_id_map = {}  # 旧 group_id -> 新 id

            # 导入组（保留旧 group_id）
            for group in rules.get("groups", []):
                old_id = group.get('group_id')
                cursor.execute(
                    "INSERT INTO search_groups (id, name, enabled) VALUES (?, ?, ?)",
                    (old_id, group.get('group_name', ''), group.get('is_enabled', 1))
                )
                group_id_map[old_id] = old_id
                imported_counts["groups"] += 1

            # 导入关键词
            for keyword in rules.get("keywords", []):
                old_group_id = keyword.get('group_id')
                new_group_id = group_id_map.get(old_group_id)
                if new_group_id:
                    is_enabled = keyword.get('is_enabled', 1)
                    cursor.execute(
                        "INSERT INTO search_keywords (keyword, group_id, enabled) VALUES (?, ?, ?)",
                        (keyword.get('keyword', ''), new_group_id, 1 if is_enabled else 0)
                    )
                    imported_counts["keywords"] += 1

            # 导入层级关系（旧项目边表）
            for hier in rules.get("hierarchy", []):
                old_parent_id = hier.get('parent_id')
                old_child_id = hier.get('child_id')
                new_parent_id = group_id_map.get(old_parent_id)
                new_child_id = group_id_map.get(old_child_id)

                if new_child_id is not None:
                    if old_parent_id == 0:
                        parent_value = 0
                    else:
                        if new_parent_id is None:
                            continue
                        parent_value = new_parent_id
                    cursor.execute(
                        "INSERT OR IGNORE INTO search_hierarchy_edges (parent_id, child_id) VALUES (?, ?)",
                        (parent_value, new_child_id)
                    )
                    if parent_value != 0:
                        cursor.execute(
                            "SELECT parent_id FROM search_groups WHERE id = ?",
                            (new_child_id,)
                        )
                        row = cursor.fetchone()
                        if row and row['parent_id'] is None:
                            cursor.execute(
                                "UPDATE search_groups SET parent_id = ? WHERE id = ?",
                                (parent_value, new_child_id)
                            )

            # 重置版本号
            new_version = rules.get('version_id', 0)
            cursor.execute(
                "UPDATE system_meta SET value = ? WHERE key = 'rules_version'",
                (str(new_version),)
            )

            rebuild_hierarchy_from_edges(conn)

        else:
            # 新项目格式导入（保持原有逻辑）
            ensure_hierarchy_edges(conn)
            for img in data.get("images", []):
                try:
                    cursor.execute(
                        """INSERT OR IGNORE INTO images (filename, md5, tags, file_size, width, height)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (img['filename'], img['md5'], img.get('tags', ''),
                         img.get('file_size', 0), img.get('width', 0), img.get('height', 0))
                    )
                    if cursor.rowcount > 0:
                        imported_counts["images"] += 1
                except Exception:
                    pass

            group_id_map = {}
            for group in data.get("groups", []):
                try:
                    old_id = group['id']
                    parent_id = group.get('parent_id')
                    if parent_id is not None and parent_id in group_id_map:
                        parent_id = group_id_map[parent_id]

                    cursor.execute(
                        "INSERT INTO search_groups (name, parent_id) VALUES (?, ?)",
                        (group['name'], parent_id)
                    )
                    group_id_map[old_id] = cursor.lastrowid
                    imported_counts["groups"] += 1
                    if parent_id is not None:
                        cursor.execute(
                            "INSERT OR IGNORE INTO search_hierarchy_edges (parent_id, child_id) VALUES (?, ?)",
                            (parent_id, cursor.lastrowid)
                        )
                except Exception:
                    pass

            for kw in data.get("keywords", []):
                try:
                    group_id = kw['group_id']
                    if group_id in group_id_map:
                        group_id = group_id_map[group_id]

                    enabled = kw.get('enabled', 1)
                    cursor.execute(
                        "INSERT INTO search_keywords (keyword, group_id, enabled) VALUES (?, ?, ?)",
                        (kw['keyword'], group_id, 1 if enabled else 0)
                    )
                    imported_counts["keywords"] += 1
                except Exception:
                    pass

            rebuild_hierarchy_from_edges(conn)

        conn.commit()

    return {
        "success": True,
        "imported_images": imported_counts["images"],
        "skipped_images": imported_counts["skipped_images"],
        "imported": imported_counts,
        "message": f"导入完成: 新增 {imported_counts['images']} 张图片, 跳过 {imported_counts['skipped_images']} 张"
    }


@router.post("/import/all")
async def import_all_compat(data: dict = Body(...)):
    """旧项目兼容：/api/import/all"""
    return await import_data(data)


@router.get("/stats")
async def get_stats():
    """获取系统统计信息"""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM images")
        image_count = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM search_groups")
        group_count = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM search_keywords")
        keyword_count = cursor.fetchone()['count']

        return {
            "images": image_count,
            "groups": group_count,
            "keywords": keyword_count,
            "rules_version": get_rules_version(),
        }
