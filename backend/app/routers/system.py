"""
系统路由（导入导出、版本等）
"""
import json
import io
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Union
from ..database import get_connection, get_rules_version, increment_rules_version

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
                "id": row['id'],
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

        if data.base_version is not None and data.client_id is not None:
            current_version = get_rules_version()
            if data.base_version != current_version:
                raise HTTPException(
                    status_code=409,
                    detail=f"版本冲突: 期望 {data.base_version}, 当前 {current_version}"
                )

        cursor.execute("UPDATE images SET tags = ? WHERE md5 = ?", (tags_str, data.md5))

        new_version = increment_rules_version(
            conn, data.client_id or "legacy", "update_tags", f"md5={data.md5}"
        )
        conn.commit()

        return {"success": True, "new_version": new_version}


@router.get("/export")
async def export_data():
    """导出所有数据（兼容旧项目格式）"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 导出图片数据（转换为旧项目格式）
        cursor.execute("SELECT * FROM images")
        images_data = []
        for row in cursor.fetchall():
            tags_text = row['tags'] if row['tags'] else ""
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
        cursor.execute("SELECT id as group_id, name as group_name, enabled as is_enabled FROM search_groups")
        groups = [dict(row) for row in cursor.fetchall()]

        # 导出关键词（转换为旧项目格式）
        cursor.execute("SELECT keyword, group_id, 1 as is_enabled FROM search_keywords")
        keywords = [dict(row) for row in cursor.fetchall()]

        # 导出层级关系（转换为旧项目简单格式 parent_id/child_id）
        cursor.execute("""
            SELECT sg.parent_id, sg.id as child_id
            FROM search_groups sg
            WHERE sg.parent_id IS NOT NULL
        """)
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
async def import_data(file: UploadFile = File(...)):
    """导入数据（兼容旧项目格式）"""
    try:
        content = await file.read()
        data = json.loads(content.decode('utf-8'))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无效的 JSON 文件: {e}")

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
            cursor.execute("DELETE FROM search_keywords")
            cursor.execute("DELETE FROM search_hierarchy")
            cursor.execute("DELETE FROM search_groups")

            rules = data.get("rules", {})
            group_id_map = {}  # 旧 group_id -> 新 id

            # 导入组
            for group in rules.get("groups", []):
                old_id = group.get('group_id')
                cursor.execute(
                    "INSERT INTO search_groups (name, enabled) VALUES (?, ?)",
                    (group.get('group_name', ''), group.get('is_enabled', 1))
                )
                new_id = cursor.lastrowid
                group_id_map[old_id] = new_id
                imported_counts["groups"] += 1

                # 自己到自己的层级关系
                cursor.execute(
                    "INSERT INTO search_hierarchy (ancestor_id, descendant_id, depth) VALUES (?, ?, 0)",
                    (new_id, new_id)
                )

            # 导入关键词
            for keyword in rules.get("keywords", []):
                old_group_id = keyword.get('group_id')
                new_group_id = group_id_map.get(old_group_id)
                if new_group_id:
                    cursor.execute(
                        "INSERT INTO search_keywords (keyword, group_id) VALUES (?, ?)",
                        (keyword.get('keyword', ''), new_group_id)
                    )
                    imported_counts["keywords"] += 1

            # 导入层级关系
            for hier in rules.get("hierarchy", []):
                old_parent_id = hier.get('parent_id')
                old_child_id = hier.get('child_id')
                new_parent_id = group_id_map.get(old_parent_id)
                new_child_id = group_id_map.get(old_child_id)

                if new_parent_id and new_child_id:
                    # 更新 parent_id
                    cursor.execute(
                        "UPDATE search_groups SET parent_id = ? WHERE id = ?",
                        (new_parent_id, new_child_id)
                    )
                    # 添加层级关系
                    cursor.execute("""
                        INSERT OR IGNORE INTO search_hierarchy (ancestor_id, descendant_id, depth)
                        SELECT ancestor_id, ?, depth + 1
                        FROM search_hierarchy
                        WHERE descendant_id = ?
                    """, (new_child_id, new_parent_id))

            # 重置版本号
            new_version = rules.get('version_id', 0)
            cursor.execute(
                "UPDATE system_meta SET value = ? WHERE key = 'rules_version'",
                (str(new_version),)
            )

        else:
            # 新项目格式导入（保持原有逻辑）
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
                except Exception:
                    pass

            for kw in data.get("keywords", []):
                try:
                    group_id = kw['group_id']
                    if group_id in group_id_map:
                        group_id = group_id_map[group_id]

                    cursor.execute(
                        "INSERT INTO search_keywords (keyword, group_id) VALUES (?, ?)",
                        (kw['keyword'], group_id)
                    )
                    imported_counts["keywords"] += 1
                except Exception:
                    pass

        conn.commit()

    return {
        "success": True,
        "imported_images": imported_counts["images"],
        "skipped_images": imported_counts["skipped_images"],
        "imported": imported_counts,
        "message": f"导入完成: 新增 {imported_counts['images']} 张图片, 跳过 {imported_counts['skipped_images']} 张"
    }


@router.post("/import/all")
async def import_all_compat(file: UploadFile = File(...)):
    """旧项目兼容：/api/import/all"""
    return await import_data(file)


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
