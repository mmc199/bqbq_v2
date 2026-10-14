"""
缩略图生成（全项目唯一实现）。

背景
----
此前存在**两套**参数不一致的生成逻辑：

    main.py  create_thumbnail()      访问时按需生成
    routers/images.py  save_thumbnail()   上传时生成

二者差异：

    项目            create_thumbnail    save_thumbnail（旧）
    --------------- ------------------- --------------------
    动图取帧        随机抽一帧          固定第一帧
    重采样          LANCZOS             PIL 默认(BICUBIC)
    optimize        True                未设置
    失败降级        复制原图            静默 pass（无缩略图）

后果是同一张 GIF 经不同路径导入时，缩略图封面帧不一致 —— 图库里
看起来"同一张图有两个封面"。现已统一到本模块，两个调用点共用。

统一后的规则
------------
    · 最大边长 settings.thumbnail_max_size（默认 600），等比缩放、不放大
    · 动图随机抽一帧作为封面
    · LANCZOS 重采样
    · 强制 RGB，JPEG 质量 85、optimize=True
    · 落位：<thumbnails_path>/<md5前2位>/<md5第3-4位>/<md5>_thumbnail.jpg
"""
from __future__ import annotations

import random
import shutil
from pathlib import Path

from PIL import Image

from .config import settings
from .sharding import thumbnail_path


def extract_random_frame(img: Image.Image) -> Image.Image:
    """动图随机抽取一帧作为封面。

    【为什么随机而不是第一帧】表情包动图的第一帧常常是黑屏、空白或
    过渡帧，用它当封面会让图库看起来"糊了一片"。随机取一帧观感更好。

    单帧图或抽取失败时原样返回（不抛错，保证缩略图始终能生成）。
    """
    try:
        if getattr(img, "is_animated", False) and img.n_frames > 1:
            img.seek(random.randint(0, img.n_frames - 1))
    except Exception:
        pass
    return img.copy()


def create_thumbnail(source_path: Path, thumb_path: Path) -> bool:
    """由磁盘上的原图生成缩略图。

    Args:
        source_path: 原图路径
        thumb_path:  缩略图输出路径（父目录会自动创建）

    Returns:
        True 表示成功（含降级方案），False 表示彻底失败。
    """
    try:
        with Image.open(source_path) as img:
            frame = extract_random_frame(img)

            # 统一转 RGB：JPEG 不支持 RGBA/P/LA 等模式
            if frame.mode != "RGB":
                frame = frame.convert("RGB")

            # 等比缩放，且不会放大小图（Pillow thumbnail 的语义）
            frame.thumbnail(
                (settings.thumbnail_max_size, settings.thumbnail_max_size),
                Image.LANCZOS,
            )

            thumb_path.parent.mkdir(parents=True, exist_ok=True)
            frame.save(thumb_path, "JPEG", quality=85, optimize=True)
            return True

    except Exception as e:
        print(f"Thumbnail generation failed for {source_path}: {e}")
        # 降级：直接复制原图当缩略图。
        # 扩展名虽是 .jpg 但内容可能是别的格式 —— 浏览器按文件头渲染，
        # 实际能正常显示，比"什么都拿不到"好。
        try:
            thumb_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(source_path, thumb_path)
            return True
        except Exception:
            return False


def create_thumbnail_for(original_path: Path, md5: str) -> bool:
    """按分片规则落位生成缩略图（调用方只需给原图路径和 md5）。

    这是上传、扫描导入、按需生成三条路径共用的入口。
    """
    stem = (md5 or "").strip().lower()
    if not stem:
        return False
    target = thumbnail_path(Path(settings.thumbnails_path), stem)
    return create_thumbnail(original_path, target)
