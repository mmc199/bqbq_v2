"""
MD5 分片路径工具（与旧项目 shard_migration.py 使用完全相同的规则）

背景
----
旧项目原本把 43 万张图片平铺在单个目录里，在 Windows/NTFS 上会造成
目录枚举极慢、资源管理器卡死等问题。迁移脚本已将其改为 Git 对象库风格的
两段式分片目录：

    meme_images/<md5 前2位>/<md5 第3-4位>/<md5>.<ext>

例如：
    7f5d377f8dae018434c9b5638d4a5cec.gif
    -> meme_images/7f/5d/7f5d377f8dae018434c9b5638d4a5cec.gif

缩略图目录保持镜像结构：
    meme_images_thumbnail/7f/5d/7f5d377f8dae018434c9b5638d4a5cec_thumbnail.jpg

重要约定
--------
数据库 `images.filename` 字段存的是**相对于图片根目录的相对路径**，
使用正斜杠 `/` 分隔，例如 `7f/5d/7f5d377f8dae018434c9b5638d4a5cec.gif`。

这样做的原因：
    - 前端直接把 filename 拼进 URL（`/images/${filename}`），天然支持分片
    - 静态挂载 StaticFiles 本身就是按 URL 路径取文件，天然支持分片
    - 分片规则只依赖文件名（md5），与存放位置解耦，迁移和查询不会不一致
"""
from __future__ import annotations

from pathlib import Path

# 分片参数：两层，每层 2 个十六进制字符 -> 256 x 256 = 65536 个叶子目录
SHARD_DEPTH = 2
SHARD_WIDTH = 2

_HEX = set("0123456789abcdef")


def shard_parts(stem: str) -> list[str] | None:
    """
    由文件主名（通常是 md5）推导分片目录分量。

    Args:
        stem: 不含扩展名的文件名，例如 "7f5d377f8dae018434c9b5638d4a5cec"

    Returns:
        ["7f", "5d"]；如果不是合法十六进制前缀则返回 None（调用方需自行兜底）
    """
    if not stem or len(stem) < SHARD_DEPTH * SHARD_WIDTH:
        return None

    parts: list[str] = []
    for i in range(SHARD_DEPTH):
        seg = stem[i * SHARD_WIDTH:(i + 1) * SHARD_WIDTH].lower()
        if not set(seg) <= _HEX:
            return None
        parts.append(seg)
    return parts


def sharded_rel_path(md5: str, ext: str = "") -> str:
    """
    生成入库用的相对路径（正斜杠分隔）。

    Args:
        md5: 文件 md5
        ext: 扩展名，可带或不带点，例如 "jpg" 或 ".jpg"

    Returns:
        "7f/5d/7f5d377f8dae018434c9b5638d4a5cec.gif"

    如果 md5 不是规范的十六进制串（例如历史遗留的脏数据文件名），
    则退化为平铺文件名，保证不丢数据、不写错路径。
    """
    stem = (md5 or "").strip().lower()
    suffix = (ext or "").lstrip(".").lower()

    parts = shard_parts(stem)
    name = f"{stem}.{suffix}" if suffix else stem

    if parts is None:
        return name
    return "/".join(parts + [name])


def sharded_path(root: Path, md5: str, ext: str = "") -> Path:
    """
    生成磁盘绝对路径。

    Args:
        root: 图片/缩略图根目录
        md5: 文件 md5
        ext: 扩展名
    """
    rel = sharded_rel_path(md5, ext)
    return Path(root).joinpath(*rel.split("/"))


def thumbnail_rel_path(md5: str) -> str:
    """缩略图相对路径：分片目录 + <md5>_thumbnail.jpg"""
    stem = (md5 or "").strip().lower()
    parts = shard_parts(stem)
    name = f"{stem}_thumbnail.jpg"
    if parts is None:
        return name
    return "/".join(parts + [name])


def thumbnail_path(thumb_root: Path, md5: str) -> Path:
    """缩略图磁盘绝对路径"""
    rel = thumbnail_rel_path(md5)
    return Path(thumb_root).joinpath(*rel.split("/"))


def resolve_image_path(images_root: Path, filename: str) -> Path | None:
    """
    把数据库中的 filename 解析为磁盘路径，并做安全检查。

    filename 可能是：
      - 分片相对路径："7f/5d/xxx.gif"
      - 带 trash_bin 前缀："trash_bin/xxx.jpg"
      - 历史遗留平铺文件名："xxx.gif"

    Returns:
        存在的磁盘路径；不存在或越界则返回 None
    """
    if not filename:
        return None

    root = Path(images_root).resolve()
    rel = filename.replace("\\", "/").strip("/")
    candidate = root.joinpath(*rel.split("/"))

    try:
        resolved = candidate.resolve()
    except OSError:
        return None

    # 防止 ../ 越界访问
    if not str(resolved).startswith(str(root)):
        return None

    return resolved if resolved.is_file() else None


def extract_md5(filename: str) -> str:
    """
    从 filename 中提取 md5（不含目录、不含扩展名）。
    旧项目里 md5 就是文件主名。
    """
    base = Path((filename or "").replace("\\", "/")).name
    return base.rsplit(".", 1)[0].lower() if "." in base else base.lower()
