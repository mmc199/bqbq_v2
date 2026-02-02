"""
图片 CRUD 路由
"""
import base64
import hashlib
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from PIL import Image
import io

from ..config import settings
from ..database import get_connection, get_rules_version, increment_rules_version
from ..models.image import ImageCreate, ImageResponse, ImageUpdate

router = APIRouter()


class CheckMD5Request(BaseModel):
    md5: str
    refresh_time: bool = False


def save_thumbnail(image_bytes: bytes, md5: str) -> None:
    """生成缩略图（与旧项目一致的命名）"""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.thumbnail((settings.thumbnail_max_size, settings.thumbnail_max_size))
        thumbnails_path = Path(settings.thumbnails_path)
        thumbnails_path.mkdir(parents=True, exist_ok=True)
        thumb_path = thumbnails_path / f"{md5}_thumbnail.jpg"
        img.convert("RGB").save(thumb_path, format="JPEG", quality=85)
    except Exception:
        # 缩略图失败不影响主流程
        pass


@router.get("", response_model=list[ImageResponse])
async def list_images(page: int = 1, page_size: int = 20):
    """获取图片列表"""
    offset = (page - 1) * page_size
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM images ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (page_size, offset)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


@router.get("/check-md5/{md5}")
async def check_md5_exists(md5: str, refresh_time: bool = False):
    """检查 MD5 是否已存在"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT filename FROM images WHERE md5 = ?", (md5,))
        row = cursor.fetchone()

        if row:
            time_refreshed = False
            if refresh_time:
                # 刷新时间戳
                cursor.execute(
                    "UPDATE images SET created_at = CURRENT_TIMESTAMP WHERE md5 = ?",
                    (md5,)
                )
                conn.commit()
                time_refreshed = True

            return {
                "exists": True,
                "filename": row['filename'],
                "time_refreshed": time_refreshed
            }

        return {"exists": False}


@router.post("/check_md5")
async def check_md5_compat(data: CheckMD5Request):
    """旧项目兼容：POST /api/check_md5"""
    return await check_md5_exists(data.md5, data.refresh_time)


@router.get("/{image_id}", response_model=ImageResponse)
async def get_image(image_id: int):
    """获取单张图片"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM images WHERE id = ?", (image_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="图片不存在")
        return dict(row)


@router.post("", response_model=ImageResponse)
async def create_image(data: ImageCreate):
    """上传图片"""
    # 检查 MD5 是否已存在
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM images WHERE md5 = ?", (data.md5,))
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="图片已存在")

        # 解码 base64 数据
        try:
            image_data = base64.b64decode(data.base64_data)
        except Exception:
            raise HTTPException(status_code=400, detail="无效的 base64 数据")

        # 验证 MD5
        calculated_md5 = hashlib.md5(image_data).hexdigest()
        if calculated_md5 != data.md5:
            raise HTTPException(status_code=400, detail="MD5 校验失败")

        # 获取图片尺寸
        try:
            img = Image.open(io.BytesIO(image_data))
            width, height = img.size
        except Exception:
            width, height = 0, 0

        # 保存文件
        images_path = Path(settings.images_path)
        file_path = images_path / data.filename
        file_path.write_bytes(image_data)

        # 保存到数据库
        tags_str = " ".join(data.tags)
        cursor.execute(
            """INSERT INTO images (filename, md5, tags, file_size, width, height)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (data.filename, data.md5, tags_str, len(image_data), width, height)
        )
        conn.commit()

        image_id = cursor.lastrowid
        cursor.execute("SELECT * FROM images WHERE id = ?", (image_id,))
        return dict(cursor.fetchone())


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """旧项目兼容：Multipart 上传"""
    if not file.filename:
        return {"success": False}

    image_bytes = await file.read()
    if not image_bytes:
        return {"success": False}

    md5 = hashlib.md5(image_bytes).hexdigest()

    # 检查是否存在
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM images WHERE md5 = ?", (md5,))
        if cursor.fetchone():
            cursor.execute(
                "UPDATE images SET created_at = CURRENT_TIMESTAMP WHERE md5 = ?",
                (md5,)
            )
            conn.commit()
            return {"success": False, "msg": "Duplicate image (timestamp refreshed)"}

        # 读取尺寸
        width, height = 0, 0
        try:
            img = Image.open(io.BytesIO(image_bytes))
            width, height = img.size
        except Exception:
            pass

        # 保存原图
        images_path = Path(settings.images_path)
        images_path.mkdir(parents=True, exist_ok=True)
        ext = Path(file.filename).suffix.lower()
        if not ext:
            ext = ".jpg"
        filename = f"{md5}{ext}"
        file_path = images_path / filename
        file_path.write_bytes(image_bytes)

        # 生成缩略图
        save_thumbnail(image_bytes, md5)

        # 写入数据库
        cursor.execute(
            """INSERT INTO images (filename, md5, tags, file_size, width, height)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (filename, md5, "", len(image_bytes), width, height)
        )
        conn.commit()

    return {"success": True, "msg": md5}


@router.put("/{image_id}/tags")
async def update_image_tags(image_id: int, data: ImageUpdate):
    """更新图片标签（CAS）"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 检查图片是否存在
        cursor.execute("SELECT id FROM images WHERE id = ?", (image_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="图片不存在")

        # CAS 版本检查
        current_version = get_rules_version()
        if data.base_version != current_version:
            raise HTTPException(
                status_code=409,
                detail=f"版本冲突: 期望 {data.base_version}, 当前 {current_version}"
            )

        # 更新标签
        tags_str = " ".join(data.tags)
        cursor.execute(
            "UPDATE images SET tags = ? WHERE id = ?",
            (tags_str, image_id)
        )

        # 递增版本号
        new_version = increment_rules_version(
            conn, data.client_id, "update_tags",
            f"image_id={image_id}"
        )
        conn.commit()

        return {"success": True, "new_version": new_version}


@router.delete("/{image_id}")
async def delete_image(image_id: int):
    """删除图片"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 获取图片信息
        cursor.execute("SELECT filename FROM images WHERE id = ?", (image_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="图片不存在")

        # 删除文件
        file_path = Path(settings.images_path) / row['filename']
        if file_path.exists():
            file_path.unlink()

        # 删除数据库记录
        cursor.execute("DELETE FROM images WHERE id = ?", (image_id,))
        conn.commit()

        return {"success": True, "message": "图片已删除"}
