# -*- coding: utf-8 -*-
"""
数据库迁移脚本：从旧项目迁移到新项目
旧数据库: D:/bqbq_backend_dev/meme.db
新数据库: ./meme.db
"""
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

OLD_DB = Path("D:/bqbq_backend_dev/meme.db")
NEW_DB = Path("./meme.db")
OLD_IMAGES = Path("D:/bqbq_backend_dev/meme_images")
NEW_IMAGES = Path("./images")

def migrate():
    print("=" * 50)
    print("开始数据库迁移")
    print("=" * 50)

    # 检查旧数据库
    if not OLD_DB.exists():
        print(f"错误: 旧数据库不存在 {OLD_DB}")
        return

    # 连接旧数据库
    old_conn = sqlite3.connect(OLD_DB)
    old_conn.row_factory = sqlite3.Row

    # 创建新数据库（先删除旧的）
    if NEW_DB.exists():
        NEW_DB.unlink()
        print(f"已删除旧的新数据库")

    # 初始化新数据库
    from app.database import init_database, get_connection
    init_database()
    print("新数据库初始化完成")

    with get_connection() as new_conn:
        cursor = new_conn.cursor()

        # 1. 迁移图片数据
        print("\n[1/4] 迁移图片数据...")
        old_images = old_conn.execute("SELECT * FROM images").fetchall()
        old_fts = {r['md5']: r['tags_text'] for r in old_conn.execute("SELECT md5, tags_text FROM images_fts").fetchall()}

        migrated = 0
        for img in old_images:
            md5 = img['md5']
            tags = old_fts.get(md5, '') or ''

            # 转换时间戳
            created_at = img['created_at']
            if created_at:
                created_at = datetime.fromtimestamp(created_at).strftime('%Y-%m-%d %H:%M:%S')
            else:
                created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            cursor.execute("""
                INSERT INTO images (filename, md5, tags, created_at, file_size, width, height)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                img['filename'],
                md5,
                tags,
                created_at,
                img['size'] or 0,
                img['width'] or 0,
                img['height'] or 0
            ))
            migrated += 1

        print(f"   迁移了 {migrated} 条图片记录")

        # 2. 迁移规则组
        print("\n[2/4] 迁移规则组...")
        old_groups = old_conn.execute("SELECT * FROM search_groups").fetchall()
        group_id_map = {}  # 旧ID -> 新ID

        for g in old_groups:
            cursor.execute("""
                INSERT INTO search_groups (name, parent_id)
                VALUES (?, NULL)
            """, (g['group_name'],))
            group_id_map[g['group_id']] = cursor.lastrowid

        print(f"   迁移了 {len(old_groups)} 个规则组")

        # 3. 迁移关键词
        print("\n[3/4] 迁移关键词...")
        old_keywords = old_conn.execute("SELECT * FROM search_keywords").fetchall()
        kw_count = 0

        for kw in old_keywords:
            old_group_id = kw['group_id']
            if old_group_id in group_id_map:
                cursor.execute("""
                    INSERT INTO search_keywords (keyword, group_id)
                    VALUES (?, ?)
                """, (kw['keyword'], group_id_map[old_group_id]))
                kw_count += 1

        print(f"   迁移了 {kw_count} 个关键词")

        # 4. 迁移层级关系（转换为 parent_id 方式）
        print("\n[4/4] 迁移层级关系...")
        old_hierarchy = old_conn.execute("SELECT * FROM search_hierarchy").fetchall()

        for h in old_hierarchy:
            old_parent = h['parent_id']
            old_child = h['child_id']
            if old_parent in group_id_map and old_child in group_id_map:
                new_parent = group_id_map[old_parent]
                new_child = group_id_map[old_child]
                cursor.execute("""
                    UPDATE search_groups SET parent_id = ? WHERE id = ?
                """, (new_parent, new_child))

        print(f"   迁移了 {len(old_hierarchy)} 条层级关系")

        # 5. 迁移版本号
        old_meta = old_conn.execute("SELECT * FROM system_meta WHERE key='rules_state'").fetchone()
        if old_meta:
            cursor.execute("""
                UPDATE system_meta SET value = ? WHERE key = 'rules_version'
            """, (str(old_meta['version_id']),))
            print(f"\n版本号已设置为: {old_meta['version_id']}")

        new_conn.commit()

    old_conn.close()

    # 复制图片文件
    print("\n[额外] 检查图片文件...")
    NEW_IMAGES.mkdir(exist_ok=True)

    if OLD_IMAGES.exists():
        existing = list(NEW_IMAGES.glob("*"))
        if len(existing) == 0:
            print(f"   需要复制图片，源目录: {OLD_IMAGES}")
            print(f"   建议手动复制或创建软链接:")
            print(f"   mklink /D \"{NEW_IMAGES.absolute()}\" \"{OLD_IMAGES.absolute()}\"")
        else:
            print(f"   新图片目录已有 {len(existing)} 个文件")

    print("\n" + "=" * 50)
    print("迁移完成!")
    print("=" * 50)

if __name__ == "__main__":
    migrate()
