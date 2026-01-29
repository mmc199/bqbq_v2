"""
系统路由（导入导出、版本等）
"""
import json
import io
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from ..database import get_connection, get_rules_version

router = APIRouter()


@router.get("/version")
async def get_version():
    """获取当前规则版本"""
    return {"version": get_rules_version()}


@router.get("/export")
async def export_data():
    """导出所有数据"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 导出图片数据
        cursor.execute("SELECT * FROM images")
        images = [dict(row) for row in cursor.fetchall()]

        # 导出规则组
        cursor.execute("SELECT * FROM search_groups")
        groups = [dict(row) for row in cursor.fetchall()]

        # 导出关键词
        cursor.execute("SELECT * FROM search_keywords")
        keywords = [dict(row) for row in cursor.fetchall()]

        # 导出层级关系
        cursor.execute("SELECT * FROM search_hierarchy")
        hierarchy = [dict(row) for row in cursor.fetchall()]

        export_data = {
            "version": "2.0",
            "exported_at": datetime.now().isoformat(),
            "rules_version": get_rules_version(),
            "images": images,
            "groups": groups,
            "keywords": keywords,
            "hierarchy": hierarchy,
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


@router.post("/import")
async def import_data(file: UploadFile = File(...)):
    """导入数据"""
    try:
        content = await file.read()
        data = json.loads(content.decode('utf-8'))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无效的 JSON 文件: {e}")

    imported_counts = {
        "images": 0,
        "groups": 0,
        "keywords": 0,
    }

    with get_connection() as conn:
        cursor = conn.cursor()

        # 导入图片（跳过已存在的）
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

        # 导入规则组
        group_id_map = {}  # 旧 ID -> 新 ID
        for group in data.get("groups", []):
            try:
                old_id = group['id']
                parent_id = group.get('parent_id')

                # 映射父 ID
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

        # 导入关键词
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

        # 重建层级关系
        for group_id in group_id_map.values():
            # 自己到自己
            cursor.execute(
                "INSERT OR IGNORE INTO search_hierarchy (ancestor_id, descendant_id, depth) VALUES (?, ?, 0)",
                (group_id, group_id)
            )

        # 根据 parent_id 重建层级
        cursor.execute("SELECT id, parent_id FROM search_groups WHERE parent_id IS NOT NULL")
        for row in cursor.fetchall():
            cursor.execute("""
                INSERT OR IGNORE INTO search_hierarchy (ancestor_id, descendant_id, depth)
                SELECT ancestor_id, ?, depth + 1
                FROM search_hierarchy
                WHERE descendant_id = ?
            """, (row['id'], row['parent_id']))

        conn.commit()

    return {
        "success": True,
        "imported": imported_counts,
        "message": f"导入完成: {imported_counts['images']} 张图片, {imported_counts['groups']} 个规则组, {imported_counts['keywords']} 个关键词"
    }


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
