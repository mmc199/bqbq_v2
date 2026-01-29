"""
数据库连接和初始化
"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

from .config import settings


def get_db_path() -> Path:
    """获取数据库路径"""
    return settings.database_path


def init_database():
    """初始化数据库表结构"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 图片表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                md5 TEXT UNIQUE NOT NULL,
                tags TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_size INTEGER DEFAULT 0,
                width INTEGER DEFAULT 0,
                height INTEGER DEFAULT 0
            )
        """)

        # FTS5 全文搜索索引
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS images_fts USING fts5(
                tags,
                content='images',
                content_rowid='id'
            )
        """)

        # FTS 触发器
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS images_ai AFTER INSERT ON images BEGIN
                INSERT INTO images_fts(rowid, tags) VALUES (new.id, new.tags);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS images_ad AFTER DELETE ON images BEGIN
                INSERT INTO images_fts(images_fts, rowid, tags) VALUES('delete', old.id, old.tags);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS images_au AFTER UPDATE ON images BEGIN
                INSERT INTO images_fts(images_fts, rowid, tags) VALUES('delete', old.id, old.tags);
                INSERT INTO images_fts(rowid, tags) VALUES (new.id, new.tags);
            END
        """)

        # 规则组表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_id INTEGER DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES search_groups(id) ON DELETE CASCADE
            )
        """)

        # 规则关键词表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                group_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES search_groups(id) ON DELETE CASCADE
            )
        """)

        # 层级关系表（用于快速查询子节点）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_hierarchy (
                ancestor_id INTEGER NOT NULL,
                descendant_id INTEGER NOT NULL,
                depth INTEGER NOT NULL,
                PRIMARY KEY (ancestor_id, descendant_id),
                FOREIGN KEY (ancestor_id) REFERENCES search_groups(id) ON DELETE CASCADE,
                FOREIGN KEY (descendant_id) REFERENCES search_groups(id) ON DELETE CASCADE
            )
        """)

        # 系统元数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # 版本日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_version_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_id INTEGER NOT NULL,
                client_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 初始化版本号
        cursor.execute("""
            INSERT OR IGNORE INTO system_meta (key, value) VALUES ('rules_version', '0')
        """)

        conn.commit()


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """获取数据库连接（上下文管理器）"""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def get_rules_version() -> int:
    """获取当前规则版本号"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM system_meta WHERE key = 'rules_version'")
        row = cursor.fetchone()
        return int(row['value']) if row else 0


def increment_rules_version(conn: sqlite3.Connection, client_id: str, operation: str, details: str = "") -> int:
    """递增规则版本号并记录日志"""
    cursor = conn.cursor()

    # 递增版本号
    cursor.execute("""
        UPDATE system_meta SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT)
        WHERE key = 'rules_version'
    """)

    # 获取新版本号
    cursor.execute("SELECT value FROM system_meta WHERE key = 'rules_version'")
    new_version = int(cursor.fetchone()['value'])

    # 记录日志
    cursor.execute("""
        INSERT INTO search_version_log (version_id, client_id, operation, details)
        VALUES (?, ?, ?, ?)
    """, (new_version, client_id, operation, details))

    return new_version
