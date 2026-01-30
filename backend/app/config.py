"""
配置管理
"""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # 数据库路径
    database_path: Path = Path("meme.db")

    # 图片存储路径
    images_path: Path = Path("images")

    # 缩略图存储路径
    thumbnails_path: Path = Path("thumbnails")

    # 缩略图最大尺寸
    thumbnail_max_size: int = 600

    # 允许的图片扩展名
    allowed_extensions: list[str] = ["gif", "png", "jpg", "jpeg", "webp", "bmp"]

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
