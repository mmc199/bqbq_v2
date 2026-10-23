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

        # 层级关系边表（旧项目语义：支持多父关系）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_hierarchy_edges (
                parent_id INTEGER NOT NULL,
                child_id INTEGER NOT NULL,
                PRIMARY KEY (parent_id, child_id)
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

        # =====================================================================
        #  登录鉴权
        # =====================================================================
        #
        # 【设计】client_id 直接作为凭据，不签发 token。
        # 浏览器 localStorage 里的 client_xxx 是一串随机值；陌生人打开网站
        # 会得到自己的 client_id，但它不在本表里，所以写操作仍被拒。
        # 安全性由「服务端的授权记录」保证，而不是 client_id 本身。

        # 已授权的客户端（永不过期）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_granted_clients (
                client_id   TEXT PRIMARY KEY,
                openid      TEXT,
                granted_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 待确认的验证码（4 位，5 分钟过期，用后即焚）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_pending_codes (
                code        TEXT PRIMARY KEY,
                client_id   TEXT NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at  TIMESTAMP NOT NULL,
                used        INTEGER DEFAULT 0
            )
        """)

        # 操作审计日志
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id   TEXT NOT NULL,
                openid      TEXT,
                action      TEXT NOT NULL,
                target      TEXT,
                detail      TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # =====================================================================
        #  购物车
        # =====================================================================

        # 用户的购物车（长期保留的收藏）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cart_items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id   TEXT NOT NULL,
                md5         TEXT NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(client_id, md5)
            )
        """)

        # 待取回队列（用户点「发送到 QQ」后进入这里，bot 取走即标记）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cart_outbox (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id   TEXT NOT NULL,
                md5         TEXT NOT NULL,
                status      TEXT DEFAULT 'pending',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                taken_at    TIMESTAMP
            )
        """)

        # 创建性能优化索引
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords_group ON search_keywords(group_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hierarchy_ancestor ON search_hierarchy(ancestor_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hierarchy_descendant ON search_hierarchy(descendant_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hierarchy_edges_child ON search_hierarchy_edges(child_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_images_created ON images(created_at DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_images_size ON images(file_size DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_images_resolution ON images(height DESC, width DESC)")
            # 鉴权 / 审计 / 购物车
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_client ON audit_log(client_id, created_at DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cart_client ON cart_items(client_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_outbox_status ON cart_outbox(status, client_id)")
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


def rebuild_tags_dict(force: bool = False):
    """
    重建 tags_dict 表，统计所有图片中每个标签的实际使用次数。

    【两个调用方，语义相反，不要混用】
      · 启动阶段（startup）：`rebuild_tags_dict()` —— 已有数据就复用。
        目的是避免每次启动都白跑一遍，冷启动更快。
      · 定时刷新（start_tags_dict_updater）：`rebuild_tags_dict(force=True)`
        —— 必须真的重建，否则字典永远不会更新。

    【成本】实测一次完整重建约 0.34 秒：全库 45 万行里只有约 188 行
    带标签，其它被 `WHERE tags != ''` 过滤，真正参与统计的标签很少。
    """
    if not force:
        try:
            with get_connection() as conn:
                cnt = conn.execute("SELECT COUNT(*) AS c FROM tags_dict").fetchone()["c"]
            if cnt > 0:
                print(f"[Tags Dict] 启动复用已有标签字典（{cnt} 个标签）")
                return
        except Exception:
            pass  # 表不存在等问题 -> 走下面的完整重建

    print("[Tags Dict] Rebuilding tags dictionary...")

    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. 清空现有数据
        cursor.execute("DELETE FROM tags_dict")

        # 2. 获取所有图片的标签
        cursor.execute("SELECT tags FROM images_fts WHERE tags IS NOT NULL AND tags != ''")
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


def ensure_hierarchy_edges(conn: sqlite3.Connection) -> None:
    """确保旧项目层级边表存在并用现有 parent_id 补齐一次"""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) as cnt FROM search_hierarchy_edges")
    except sqlite3.OperationalError:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_hierarchy_edges (
                parent_id INTEGER NOT NULL,
                child_id INTEGER NOT NULL,
                PRIMARY KEY (parent_id, child_id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hierarchy_edges_child ON search_hierarchy_edges(child_id)")
        cursor.execute("SELECT COUNT(*) as cnt FROM search_hierarchy_edges")

    cnt = cursor.fetchone()['cnt']
    if cnt == 0:
        cursor.execute("SELECT id, parent_id FROM search_groups WHERE parent_id IS NOT NULL")
        rows = cursor.fetchall()
        if rows:
            cursor.executemany(
                "INSERT OR IGNORE INTO search_hierarchy_edges (parent_id, child_id) VALUES (?, ?)",
                [(row['parent_id'], row['id']) for row in rows if row['parent_id'] is not None]
            )
    conn.commit()


def rebuild_hierarchy_from_edges(conn: sqlite3.Connection) -> None:
    """基于 search_hierarchy_edges 重建闭包表 search_hierarchy"""
    cursor = conn.cursor()
    ensure_hierarchy_edges(conn)

    cursor.execute("DELETE FROM search_hierarchy")
    cursor.execute("SELECT id FROM search_groups")
    ids = [row['id'] for row in cursor.fetchall()]
    if ids:
        cursor.executemany(
            "INSERT OR IGNORE INTO search_hierarchy (ancestor_id, descendant_id, depth) VALUES (?, ?, 0)",
            [(gid, gid) for gid in ids]
        )

    cursor.execute("SELECT parent_id, child_id FROM search_hierarchy_edges WHERE parent_id != 0")
    edges = cursor.fetchall()
    if edges:
        cursor.executemany(
            "INSERT OR IGNORE INTO search_hierarchy (ancestor_id, descendant_id, depth) VALUES (?, ?, 1)",
            [(row['parent_id'], row['child_id']) for row in edges]
        )

        cursor.execute("""
            WITH RECURSIVE rel(ancestor_id, descendant_id, depth, path) AS (
                SELECT parent_id, child_id, 1, printf('%d,%d', parent_id, child_id)
                FROM search_hierarchy_edges
                WHERE parent_id != 0
                UNION ALL
                SELECT r.ancestor_id, e.child_id, r.depth + 1, r.path || ',' || e.child_id
                FROM rel r
                JOIN search_hierarchy_edges e ON r.descendant_id = e.parent_id
                WHERE e.parent_id != 0
                  AND instr(r.path, printf(',%d', e.child_id)) = 0
            )
            INSERT OR IGNORE INTO search_hierarchy (ancestor_id, descendant_id, depth)
            SELECT ancestor_id, descendant_id, depth FROM rel
        """)

    conn.commit()
