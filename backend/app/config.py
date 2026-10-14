"""
配置管理
"""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # 数据库路径
    #
    # 【重要】必须锚定到 backend/ 目录，不能用相对路径 "meme.db"。
    # 原因：相对路径是相对「进程当前工作目录」解析的。
    # 如果从其它目录启动（例如 `uvicorn app.main:app` 在仓库根目录跑），
    # SQLite 会**静默新建一个空的 meme.db**，于是所有查询都变成
    # "no such table: images"，看起来像数据丢了。
    # 这里与 images_path 保持一致，统一锚定到 __file__ 所在位置。
    database_path: Path = Path(__file__).parent.parent / "meme.db"

    # 图片存储路径（软链接到旧项目位置）
    #
    # 【分片说明】旧项目已把 43 万张图片从「单目录平铺」改为
    # md5 两段式分片目录：<前2位>/<第3-4位>/<md5>.<ext>
    # 因此这里挂载的根目录下不再直接放图片，而是 256 个分片目录。
    # 具体路径规则见 app/sharding.py。
    images_path: Path = Path(__file__).parent.parent / "meme_images"

    # 缩略图存储路径（与 images_path 保持相同的分片镜像结构）
    thumbnails_path: Path = Path(__file__).parent.parent / "meme_images_thumbnail"

    # 缩略图最大尺寸
    thumbnail_max_size: int = 600

    # 允许的图片扩展名
    # 与旧项目 ALLOWED_EXTS 对齐，补上 heic/heif/avif
    # （数据集里确实存在 HEIC，且有个别文件扩展名被误写成 .gif）
    allowed_extensions: list[str] = [
        "jpg", "jpeg", "png", "gif", "webp", "bmp", "heic", "heif", "avif",
    ]

    # 分页默认值
    default_page_size: int = 20
    max_page_size: int = 100

    # CORS 配置
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # tags_dict 更新间隔（秒）
    tags_dict_update_interval: int = 900

    class Config:
        env_prefix = "BQBQ_"


settings = Settings()
