# -*- coding: utf-8 -*-
"""
把旧项目的 43 万张分片图片数据合并进 bqbq_v2。

背景
----
- 旧库 D:\\bqbq_backend\\db\\meme.db
    images(md5, filename, modified_time)          434027 行，filename 已是分片相对路径
    tags(id, name, ref_count) / image_tags(image_md5, tag_id)   规范化标签，仅 153 张图有标签
- 新库 bqbq_v2/backend/meme.db
    images(id, filename, md5, tags TEXT, created_at, file_size, width, height)
    tags 是「空格分隔的字符串」，FTS5 触发器和 rebuild_tags_dict() 都依赖这一列

两边标签模型不同，所以合并策略是：
1. 以新库结构为准（保持 FTS5 / 前端 / rebuild_tags_dict 全部可用）
2. 旧库的规范化标签 → 展开成空格分隔字符串，写进 tags 列
3. 旧库已有的 2590 行（含 29 张有标签的）全部保留，标签不会被覆盖
4. 旧库独有的 783 个 md5：如果图片文件实际存在，则复制进 D:\\bqbq_backend 的分片目录

用法
----
    python merge_into_v2.py --dry-run     # 只统计
    python merge_into_v2.py --apply       # 执行
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

# ---- 旧库（数据来源）----
OLD_DB = Path(r"D:\bqbq_backend\db\meme.db")
OLD_IMAGES = Path(r"D:\bqbq_backend\meme_images")
OLD_THUMBS = Path(r"D:\bqbq_backend\meme_images_thumbnail")

# ---- 新库（合并目标）----
NEW_DB = Path(r"C:\000soft\qqpy机器人-git\bqbq_v2\backend\meme.db")

# 旧项目里那些「v2 目录」下的独有文件
V2_DEV_IMAGES = Path(r"D:\bqbq_backend_dev\meme_images")
V2_DEV_THUMBS = Path(r"D:\bqbq_backend_dev\meme_images_thumbnail")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.sharding import sharded_rel_path, thumbnail_rel_path  # noqa: E402


def load_old_tags(old: sqlite3.Connection) -> dict[str, str]:
    """把旧库规范化标签展开成 {md5: '空格分隔的标签'}"""
    old.row_factory = sqlite3.Row
    cur = old.cursor()
    cur.execute("""
        SELECT it.image_md5 AS md5, t.name AS name
        FROM image_tags it
        JOIN tags t ON t.id = it.tag_id
        ORDER BY it.image_md5, t.name
    """)
    grouped: dict[str, list[str]] = {}
    for row in cur.fetchall():
        md5 = (row["md5"] or "").strip().lower()
        name = (row["name"] or "").strip()
        if md5 and name:
            grouped.setdefault(md5, []).append(name)
    return {md5: " ".join(names) for md5, names in grouped.items()}


def collect_old_images(old: sqlite3.Connection) -> list[tuple[str, str]]:
    """返回 [(md5, filename), ...]，只保留磁盘上真实存在的"""
    old.row_factory = sqlite3.Row
    rows = old.execute("SELECT md5, filename FROM images").fetchall()
    out = []
    missing = 0
    for r in rows:
        md5 = (r["md5"] or "").strip().lower()
        fn = (r["filename"] or "").replace("\\", "/")
        full = OLD_IMAGES.joinpath(*fn.split("/"))
        if full.is_file():
            out.append((md5, fn))
        else:
            missing += 1
    print(f"  旧库记录 {len(rows)} 条，磁盘存在 {len(out)} 条，缺失 {missing} 条")
    return out


def copy_v2_only_files(old_md5: set[str], wanted_md5: set[str], apply: bool) -> tuple[int, int]:
    """
    把 v2 目录里「旧库没有、但 v2 数据库里有记录」的图片，
    按分片规则补进 D:\\bqbq_backend。

    Args:
        old_md5: 旧库已有的 md5 集合（这些不用再复制）
        wanted_md5: v2 数据库里记录的全部 md5（只搬这些，避免把无关文件也扫进来）

    Returns:
        (copied_images, copied_thumbs)
    """
    if not V2_DEV_IMAGES.is_dir():
        print("  v2 dev 图片目录不存在，跳过")
        return 0, 0

    copied_img = copied_thm = 0
    for entry in os.scandir(V2_DEV_IMAGES):
        if not entry.is_file():
            continue
        stem, ext = os.path.splitext(entry.name)
        stem = stem.lower()
        ext = ext.lstrip(".")
        # 必须确实是 v2 数据库里记录的图片，且旧库/旧目录里还没有
        if stem not in wanted_md5 or stem in old_md5:
            continue

        dst_rel = sharded_rel_path(stem, ext)
        dst = OLD_IMAGES.joinpath(*dst_rel.split("/"))
        if dst.exists():
            continue

        if apply:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(entry.path, dst)
        copied_img += 1

        # 对应缩略图
        t_src = V2_DEV_THUMBS / f"{stem}_thumbnail.jpg"
        if t_src.is_file():
            t_rel = thumbnail_rel_path(stem)
            t_dst = OLD_THUMBS.joinpath(*t_rel.split("/"))
            if not t_dst.exists():
                if apply:
                    t_dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(t_src, t_dst)
                copied_thm += 1

        if copied_img % 200 == 0:
            print(f"    已补充 {copied_img} 张...", flush=True)

    return copied_img, copied_thm


def rebuild_fts(new: sqlite3.Connection) -> None:
    """
    重建 FTS5 索引。
    images_fts 是 external content 表，必须用 rebuild 指令重建，
    否则触发器只会补增量，全量插入后索引会不完整。
    """
    cur = new.cursor()
    try:
        cur.execute("INSERT INTO images_fts(images_fts) VALUES('rebuild')")
        new.commit()
        print("  FTS5 索引已重建")
    except sqlite3.OperationalError as e:
        print(f"  FTS rebuild 失败，改用触发器回填: {e}")
        cur.execute("DELETE FROM images_fts")
        cur.execute("""
            INSERT INTO images_fts(rowid, tags)
            SELECT id, COALESCE(tags, '') FROM images
        """)
        new.commit()
        print("  FTS5 索引已手工回填")


def merge(apply: bool) -> None:
    print(f"模式: {'APPLY' if apply else 'DRY-RUN'}\n")

    if not OLD_DB.is_file():
        raise SystemExit(f"旧库不存在: {OLD_DB}")
    if not NEW_DB.is_file():
        raise SystemExit(f"新库不存在: {NEW_DB}")

    old = sqlite3.connect(f"file:{OLD_DB}?mode=ro", uri=True)
    new = sqlite3.connect(NEW_DB)
    new.row_factory = sqlite3.Row

    try:
        old_tags = load_old_tags(old)
        print(f"旧库有标签的图片: {len(old_tags)}")

        old_images = collect_old_images(old)
        old_md5 = {m for m, _ in old_images}

        # 新库现状
        cur = new.cursor()
        existing = {
            r["md5"].lower(): (r["id"], r["tags"] or "")
            for r in cur.execute("SELECT id, md5, tags FROM images").fetchall()
        }
        print(f"新库现有记录: {len(existing)}")

        # 现有标签不能被覆盖
        to_insert = [(m, f) for m, f in old_images if m not in existing]
        already = [m for m, _ in old_images if m in existing]
        print(f"  需要新增: {len(to_insert)}")
        print(f"  新库已存在(保留其标签): {len(already)}")

        # 旧库有标签、且新库也存在的 -> 需要把旧标签并入（不覆盖已有标签）
        merge_tags = []
        for md5, old_tag_str in old_tags.items():
            if md5 in existing:
                _, new_tag_str = existing[md5]
                have = set((new_tag_str or "").split())
                want = set(old_tag_str.split())
                missing = want - have
                if missing:
                    merged = " ".join(sorted(have | want))
                    merge_tags.append((merged, md5))
        print(f"  需要补齐标签(新旧都有): {len(merge_tags)}")

        # 补充 v2 独有文件（v2 库里记录、但旧库/旧目录没有的）
        print("\n检查 v2 独有图片文件...")
        copied_img, copied_thm = copy_v2_only_files(old_md5, set(existing), apply)
        print(f"  补充图片 {copied_img} 张, 缩略图 {copied_thm} 张")

        # 这些新补充的文件也要进库
        extra_rows = []
        if copied_img:
            for entry in os.scandir(V2_DEV_IMAGES):
                if not entry.is_file():
                    continue
                stem, ext = os.path.splitext(entry.name)
                stem = stem.lower()
                if stem in old_md5 or stem not in existing:
                    continue
                extra_rows.append((stem, sharded_rel_path(stem, ext.lstrip("."))))
        print(f"  v2 独有需入库: {len(extra_rows)}")

        if not apply:
            print("\n(dry-run，未写入)")
            return

        t0 = time.time()
        cur.execute("BEGIN IMMEDIATE")

        # 1) 批量插入旧库图片
        print(f"\n插入 {len(to_insert)} 条...")
        cur.executemany(
            """INSERT INTO images (filename, md5, tags, created_at, file_size, width, height)
               VALUES (?, ?, '', CURRENT_TIMESTAMP, 0, 0, 0)""",
            [(fn, md5) for md5, fn in to_insert],
        )
        new.commit()
        print(f"  完成 ({time.time()-t0:.0f}s)")

        # 2) 写入旧库已有标签（针对刚插入的行）
        if old_tags:
            print(f"写入标签 {len(old_tags)} 张...")
            cur.execute("BEGIN IMMEDIATE")
            cur.executemany(
                "UPDATE images SET tags = ? WHERE md5 = ?",
                [(tag_str, md5) for md5, tag_str in old_tags.items()],
            )
            new.commit()
            print("  完成")

        # 3) 合并新旧都有的标签
        if merge_tags:
            print(f"合并标签 {len(merge_tags)} 条...")
            cur.execute("BEGIN IMMEDIATE")
            cur.executemany("UPDATE images SET tags = ? WHERE md5 = ?", merge_tags)
            new.commit()
            print("  完成")

        # 4) v2 独有文件入库（保留它们在 v2 里的标签与元数据）
        if extra_rows:
            print(f"插入 v2 独有 {len(extra_rows)} 条...")
            cur.execute("BEGIN IMMEDIATE")
            rows = []
            for md5, fn in extra_rows:
                _id, tag_str = existing.get(md5, (None, ""))
                meta = cur.execute(
                    "SELECT file_size, width, height, created_at FROM images WHERE md5 = ?",
                    (md5,),
                ).fetchone()
                rows.append((
                    fn, md5, tag_str or "",
                    meta["created_at"] if meta else None,
                    meta["file_size"] if meta else 0,
                    meta["width"] if meta else 0,
                    meta["height"] if meta else 0,
                ))
            # 先删掉旧的平铺记录，再按分片路径重新插入，避免同 md5 两条
            cur.executemany("DELETE FROM images WHERE md5 = ?", [(m,) for m, _ in extra_rows])
            cur.executemany(
                """INSERT INTO images (filename, md5, tags, created_at, file_size, width, height)
                   VALUES (?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP), ?, ?, ?)""",
                rows,
            )
            new.commit()
            print("  完成")

        # 5) 重建 FTS
        print("重建 FTS5...")
        rebuild_fts(new)

        total = cur.execute("SELECT COUNT(*) FROM images").fetchone()[0]
        tagged = cur.execute(
            "SELECT COUNT(*) FROM images WHERE tags IS NOT NULL AND tags != ''"
        ).fetchone()[0]
        print(f"\n合并完成: 共 {total} 行, 其中有标签 {tagged} 行")
        print(f"总耗时 {time.time()-t0:.0f}s")

    except Exception:
        new.rollback()
        raise
    finally:
        old.close()
        new.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not (args.dry_run or args.apply):
        ap.error("请指定 --dry-run 或 --apply")
    merge(apply=args.apply)


if __name__ == "__main__":
    main()
