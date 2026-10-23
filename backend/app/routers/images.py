"""
图片 CRUD 路由
"""
import base64
import hashlib
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from PIL import Image
import io

# 注册 HEIF/HEIC 解码器（可选依赖），否则部分 HEIC 图片无法生成缩略图
try:
    from pillow_heif import register_heif_opener
except ImportError:
    pass
else:
    register_heif_opener()

from ..auth import audit, require_edit, write_audit
from ..config import settings
from ..database import get_connection, get_rules_version, increment_rules_version
from ..image_format import resolve_upload_ext
from ..models.image import ImageCreate, ImageResponse, ImageUpdate
from ..sharding import sharded_rel_path, thumbnail_path, resolve_image_path
from ..thumbnail import create_thumbnail_for
from ..r2_sync import sync_async

router = APIRouter()

# 回收站标签。被打上这个标签的图不在正常搜索里出现。
#
# 【为什么抽成常量】此前 search.py 里是硬编码的 'trash_bin' 字面量
# （两处），images.py 现在也要用。散落的字面量容易改漏。
TRASH_TAG = "trash_bin"


class CheckMD5Request(BaseModel):
    md5: str
    refresh_time: bool = False


def save_thumbnail(original_path: Path, md5: str) -> None:
    """为刚落盘的原图生成缩略图（按 md5 分片镜像落位）。

    统一调用 app.thumbnail 的实现 —— 与"访问时按需生成"共用同一套规则
    （随机抽取动图帧 / LANCZOS / optimize=True），避免同一张动图因导入
    路径不同而产生两种封面。

    缩略图失败不影响主流程（图片已入库，前端会回退到原图接口）。
    """
    create_thumbnail_for(original_path, md5)


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
    """检查 MD5 是否已存在，并返回该图的标签与基本信息。

    【2026-10 增强：新增 tags 字段】

    背景：机器人插件需要"引用一张图 -> 显示它的标签"。
    但此前没有任何接口能按 md5 拿标签：
      · 本接口只返回 exists/filename/time_refreshed
      · /api/images/upload 重复时只返回 success/exists/msg/md5
      · /api/search 是按标签 LIKE 匹配，md5 不是标签，查不到
      · /api/images?page=N 要翻页找 —— 44 万张图下这是客户端在做
        数据库该做的事（插件实测要扫 30 页/3000 条才能碰运气找到）

    所以在这里补上 tags。选择增强而非新增接口，因为：
      · 语义本就属于同一件事（"这张图在不在 / 是什么样"）
      · 多返回一个字段不会让任何现有调用方失败（向后兼容）
      · 调用方少一次往返

    返回字段（原有字段全部保留，值不变）：
        exists          : 是否存在
        filename        : 分片相对路径（不存在时无此字段）
        time_refreshed  : 是否刷新了时间戳（仅 refresh_time=True 时可能为 True）
        tags            : list[str]，标签数组（新增）
        tag_count       : int，标签数量（新增，便于快速判断）
        width / height  : 尺寸（新增）
        file_size       : 字节数（新增）
        is_trash        : 是否在回收站（新增，看 tags 是否含 trash_bin）
    """
    md5 = (md5 or "").strip().lower()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT filename, tags, width, height, file_size "
            "FROM images WHERE md5 = ?",
            (md5,),
        )
        row = cursor.fetchone()

        if not row:
            return {"exists": False, "tags": []}

        time_refreshed = False
        if refresh_time:
            # 刷新时间戳（保持原有行为不变）
            cursor.execute(
                "UPDATE images SET created_at = CURRENT_TIMESTAMP WHERE md5 = ?",
                (md5,),
            )
            conn.commit()
            time_refreshed = True

        # tags 在库里是空格分隔的字符串，这里转成数组返回。
        # 之所以不在 SQL 里 split：SQLite 没有内置的字符串切分，
        # 而且 tags 里可能含空格标签（历史数据），交给 Python 更可控。
        tags = split_tags(row["tags"])

        return {
            "exists": True,
            "filename": row["filename"],
            "time_refreshed": time_refreshed,
            "tags": tags,
            "tag_count": len(tags),
            "width": row["width"] or 0,
            "height": row["height"] or 0,
            "file_size": row["file_size"] or 0,
            "is_trash": TRASH_TAG in tags,
        }


def split_tags(raw) -> list[str]:
    """把库里的 tags 字符串切成数组。

    【为什么单独抽出来】tags 在不同写入路径下的形态不完全一致：
      · 上传时写的是 ""（空串）
      · update_tags 写的是 " ".join(tags)
      · 手工/导入的数据可能是 None，也可能本身已是 list
    统一在这里归一，避免各处调用方各自处理。

    Args:
        raw: 库里的 tags 字段，可能是 str / None / list。

    Returns:
        去空白后的标签列表；无标签返回 []。
    """
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return [str(t).strip() for t in raw if str(t).strip()]
    return [t for t in str(raw).split() if t]


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


@router.post("", response_model=ImageResponse, dependencies=[Depends(require_edit)])
async def create_image(data: ImageCreate):
    """上传图片（base64）。需要登录。"""
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

        # 保存文件（按 md5 分片规则落位，避免根目录堆积）
        # 同样以文件头为准：data.filename 可能带假的扩展名
        try:
            ext = resolve_upload_ext(image_data, data.filename)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        rel_filename = sharded_rel_path(data.md5, ext)
        images_path = Path(settings.images_path)
        file_path = images_path.joinpath(*rel_filename.split("/"))
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(image_data)

        # 保存到数据库（filename 存分片相对路径）
        tags_str = " ".join(data.tags)
        cursor.execute(
            """INSERT INTO images (filename, md5, tags, file_size, width, height)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (rel_filename, data.md5, tags_str, len(image_data), width, height)
        )
        conn.commit()

        image_id = cursor.lastrowid
        cursor.execute("SELECT * FROM images WHERE id = ?", (image_id,))
        return dict(cursor.fetchone())


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    client_id: str | None = Query(default=None),
    auth_client: str = Depends(require_edit),
):
    """
    Multipart 上传图片。

    【鉴权】只收文件、没有 JSON 请求体，所以 client_id 走 URL query：
        POST /api/images/upload?client_id=bot_astrbot
    网页上传与两个 bot 都走这一个接口。

    返回字段说明（供机器人等调用方判断结果）：
        success : 本次是否**新写入**了图片（重复时为 False）
        exists  : 该图此前**是否已存在**于库中（重复时为 True，新图时为 False）
        msg     : md5（新图）或说明文字

    沿用旧项目语义：`exists` 表示「本次上传前就已存在」= 命中重复。
    因此 `is_new = not exists` 是正确判据。
    把 success 与 exists 分开返回，是为了让调用方能区分两种 False：
        exists=True  -> 重复图片，属于正常情况，不是错误
        exists=False -> 真正失败（无文件/空内容等）
    """
    if not file.filename:
        return {"success": False, "exists": False, "msg": "no filename"}

    image_bytes = await file.read()
    if not image_bytes:
        return {"success": False, "exists": False, "msg": "empty file"}

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
            # 重复：exists=True 表示「图已在库里」，success=False 表示「本次没新增」
            return {"success": False, "exists": True, "msg": "duplicate", "md5": md5}

        # 读取尺寸
        width, height = 0, 0
        try:
            img = Image.open(io.BytesIO(image_bytes))
            width, height = img.size
        except Exception:
            pass

        # 保存原图（按分片规则落位）
        #
        # 【关键】扩展名以**文件头**为准，绝不信任 file.filename。
        # 机器人传的固定是 ("auto.gif", data, "image/gif")，直接用它会
        # 让 JPEG 存成 .gif（详见 image_format.resolve_upload_ext）。
        images_path = Path(settings.images_path)
        try:
            ext = resolve_upload_ext(image_bytes, file.filename)
        except ValueError as e:
            return {"success": False, "exists": False, "msg": str(e)}
        rel_filename = sharded_rel_path(md5, ext)
        file_path = images_path.joinpath(*rel_filename.split("/"))
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(image_bytes)

        # 生成缩略图（分片镜像结构）
        save_thumbnail(file_path, md5)

        # 写入数据库（filename 存分片相对路径）
        cursor.execute(
            """INSERT INTO images (filename, md5, tags, file_size, width, height)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (rel_filename, md5, "", len(image_bytes), width, height)
        )
        conn.commit()

    # 异步推到 R2（供 CDN 使用）。
    # 不 await、不影响响应：R2 慢或不可用都不会拖慢机器人收图，
    # 失败时本地文件仍在，前端会回退到 /images 接口。
    sync_async(file_path, rel_filename)

    # 新图：success=True，exists=False（此前**不**存在，本次才写入）
    return {"success": True, "exists": False, "msg": md5, "md5": md5}


@router.put("/{image_id}/tags", dependencies=[Depends(require_edit)])
@audit("update_tags")
async def update_image_tags(image_id: int, data: ImageUpdate):
    """更新图片标签（CAS）。需要登录。"""
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


@router.delete("/{image_id}", dependencies=[Depends(require_edit)])
async def delete_image(image_id: int):
    """删除图片。需要登录。"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 获取图片信息
        cursor.execute("SELECT filename, md5 FROM images WHERE id = ?", (image_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="图片不存在")

        # 删除原图（按分片相对路径解析）
        file_path = resolve_image_path(settings.images_path, row['filename'])
        if file_path and file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                pass

        # 顺带删除缩略图
        thumb = thumbnail_path(Path(settings.thumbnails_path), row['md5'])
        if thumb.exists():
            try:
                thumb.unlink()
            except OSError:
                pass

        # 删除数据库记录
        cursor.execute("DELETE FROM images WHERE id = ?", (image_id,))
        conn.commit()

        return {"success": True, "message": "图片已删除"}
