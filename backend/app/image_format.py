"""
图片真实格式探测（按「文件头」而不是「文件名」）。

背景
----
机器人上传时用的是**写死的假文件名**：

    files={"file": ("auto.gif", data, "image/gif")}     # AstrBot 插件
    files={"file": ("auto.jpg", content, "image/jpeg")} # 旧 OneBot 插件

也就是说 `file.filename` 从来就不代表真实格式 —— 它只是个占位符。

迁移到 v2 之前，旧 Flask 后端用 PIL 的 `img.format` 判定真实格式；
迁移时这段逻辑丢了，改成直接读 `Path(file.filename).suffix`，
于是「插件说 gif 就当 gif」，把大量 JPEG/PNG 的字节存成了 `.gif` 名字。

实测污染规模（库中最新 3000 条，逐字节比对文件头）
------------------------------------------------
    .gif 实际是 JPEG -> 2185 条
    .gif 实际是 PNG  ->  144 条
    .gif 实际是 WEBP ->    9 条
    扩展名正确        ->  662 条

即最新样本里约 78% 的 `.gif` 名不副实。

为什么要紧
----------
落盘路径同时决定三件事，全都依赖扩展名：

1. 前端/浏览器按扩展名推断 `Content-Type`（JPEG 当 gif 会渲染异常）
2. R2 对象 key 与 CDN 缓存（`r2_sync.sync_async` 直推该路径）
3. 缩略图与检索时的扩展名过滤

因此：**以文件头为准**，探测不出来才退回文件名，且必须过白名单。
"""

from __future__ import annotations

from pathlib import Path

from .config import settings

__all__ = ["sniff_image_ext", "normalize_ext", "resolve_upload_ext"]


# magic bytes -> 规范扩展名
# 只列出白名单里常见的位图格式；HEIC/HEIF/AVIF 属于 ISO-BMFF，
# 首字节不是固定 magic，需要看 ftyp box（见 sniff_image_ext）。
_MAGIC_TABLE: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "jpg"),        # JPEG (JFIF / EXIF / raw)
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
    (b"BM", "bmp"),
)

# ISO-BMFF 的 major brand -> 扩展名
_FTYP_BRANDS: dict[bytes, str] = {
    b"avif": "avif",
    b"avis": "avif",
    b"heic": "heic",
    b"heix": "heic",
    b"hevc": "heic",
    b"hevx": "heic",
    b"heim": "heic",
    b"heis": "heic",
    b"hevm": "heic",
    b"hevs": "heic",
    b"mif1": "heif",
    b"msf1": "heif",
}


def normalize_ext(raw: str) -> str:
    """
    扩展名归一化：去前导点、转小写、jpeg 统一成 jpg。

    Args:
        raw: 原始扩展名，可带点（".JPEG"）或不带（"jpeg"）。

    Returns:
        规范扩展名，如 "jpg" / "gif"；输入为空时返回空串。
    """
    ext = (raw or "").strip().lower().lstrip(".")
    return "jpg" if ext == "jpeg" else ext


def sniff_image_ext(data: bytes) -> str | None:
    """
    按文件头判定图片真实扩展名。

    Args:
        data: 文件字节内容。

    Returns:
        规范扩展名（小写、不带点）；无法确定时返回 None。
        JPEG 统一归一为 "jpg"（不是 "jpeg"），与库中既有习惯一致。
    """
    if not data or len(data) < 12:
        return None

    # 1) 固定 magic bytes
    for magic, ext in _MAGIC_TABLE:
        if data.startswith(magic):
            return ext

    # 2) RIFF....WEBP
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"

    # 3) ISO-BMFF：偏移 4 起是 "ftyp"，紧随其后的 4 字节是 major brand
    if data[4:8] == b"ftyp":
        return _FTYP_BRANDS.get(data[8:12], "heic")

    return None


def resolve_upload_ext(image_bytes: bytes, filename: str | None) -> str:
    """
    决定本次上传应当使用的扩展名（**文件头优先**）。

    优先级：
        1. 文件头探测出的真实格式
        2. 文件名后缀（探测失败时的兜底，保持旧行为不误伤罕见格式）
        3. 都没有 -> 抛 ValueError

    最后统一过 `settings.allowed_extensions` 白名单。

    Args:
        image_bytes: 上传的字节内容。
        filename: 客户端给的文件名（通常形如 "auto.gif"，是假名字）。

    Returns:
        规范扩展名，如 "jpg" / "gif" / "png"。

    Raises:
        ValueError: 格式无法识别，或不在白名单内。
            调用方应据此返回 400。
    """
    allowed = {normalize_ext(e) for e in settings.allowed_extensions}
    allowed_text = ", ".join(sorted(allowed))

    sniffed = sniff_image_ext(image_bytes)
    if sniffed:
        if sniffed not in allowed:
            raise ValueError(f"不支持的图片格式: {sniffed}（仅支持 {allowed_text}）")
        return sniffed

    # 文件头认不出来 —— 退回文件名后缀
    fallback = normalize_ext(Path(filename).suffix) if filename else ""
    if fallback and fallback in allowed:
        print(f"[UPLOAD] ⚠ 文件头无法识别，回退文件名后缀: {fallback}")
        return fallback

    raise ValueError(f"无法识别的图片格式（仅支持 {allowed_text}）")
