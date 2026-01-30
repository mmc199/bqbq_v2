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
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES search_groups(id) ON DELETE CASCADE
            )
        """)

        # 添加 enabled 字段（如果不存在）
        try:
            cursor.execute("ALTER TABLE search_groups ADD COLUMN enabled INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass  # 字段已存在

        # 规则关键词表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                group_id INTEGER NOT NULL,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES search_groups(id) ON DELETE CASCADE
            )
        """)

        # 添加关键词 enabled 字段（如果不存在）
        try:
            cursor.execute("ALTER TABLE search_keywords ADD COLUMN enabled INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass  # 字段已存在

        # 层级关系表（闭包表，用于快速查询子节点）
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

        # 标签字典表（统计标签使用次数，用于建议排序）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags_dict (
                name TEXT PRIMARY KEY,
                use_count INTEGER DEFAULT 0
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

        # 创建性能优化索引
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords_group ON search_keywords(group_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hierarchy_ancestor ON search_hierarchy(ancestor_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hierarchy_descendant ON search_hierarchy(descendant_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_images_created ON images(created_at DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_images_size ON images(file_size DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_images_resolution ON images(height DESC, width DESC)")
        except sqlite3.OperationalError:
            pass  # 索引已存在

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


def get_conflict_info(base_version: int) -> dict:
    """
    获取版本冲突的详细信息。

    Args:
        base_version: 客户端的基础版本号

    Returns:
        包含冲突统计信息的字典
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # 统计期间有多少不同的修改者
        cursor.execute(
            "SELECT COUNT(DISTINCT client_id) FROM search_version_log WHERE version_id > ?",
            (base_version,)
        )
        row = cursor.fetchone()
        unique_modifiers = row[0] if row else 0

        return {
            "unique_modifiers": unique_modifiers
        }


def rebuild_tags_dict():
    """
    重建 tags_dict 表，统计所有图片中每个标签的实际使用次数。
    在后端启动时调用一次，确保数据准确。
    """
    print("[Tags Dict] Rebuilding tags dictionary...")

    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. 清空现有数据
        cursor.execute("DELETE FROM tags_dict")

        # 2. 获取所有图片的标签
        cursor.execute("SELECT tags FROM images WHERE tags IS NOT NULL AND tags != ''")
        rows = cursor.fetchall()

        # 3. 统计每个标签的使用次数
        tag_counts = {}
        for row in rows:
            tags = row['tags'].split(' ')
            for tag in tags:
                tag = tag.strip()
                if tag:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # 4. 批量插入
        if tag_counts:
            cursor.executemany(
                "INSERT INTO tags_dict (name, use_count) VALUES (?, ?)",
                [(name, count) for name, count in tag_counts.items()]
            )

        conn.commit()

    print(f"[Tags Dict] Rebuilt with {len(tag_counts)} unique tags.")
