# -*- coding: utf-8 -*-
"""
把 v2 库里残留的「平铺 filename」统一改写成「分片相对路径」。

合并脚本保留了 v2 原有行的 filename 原值（为了不破坏数据），
但它们的磁盘文件其实已经在分片目录里，所以需要一次性归一。

规则与 app/sharding.py 完全一致：
    <md5 前2位>/<md5 第3-4位>/<md5>.<真实扩展名>

扩展名以「磁盘上真实存在的文件」为准：
旧项目早期做过「按真实内容修正扩展名」，所以库里的扩展名可能和磁盘不符
（例如库里 .png 实际是 JPEG）。这种情况下以磁盘为准，避免 404。

用法：
    python normalize_filenames.py --dry-run
    python normalize_filenames.py --apply
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.sharding import sharded_rel_path  # noqa: E402

DB = Path(r"C:\000soft\qqpy机器人-git\bqbq_v2\backend\meme.db")
IMAGES = Path(r"D:\bqbq_backend\meme_images")
THUMBS = Path(r"D:\bqbq_backend\meme_images_thumbnail")

# 候选扩展名（按优先级）
CANDIDATE_EXTS = ["jpg", "jpeg", "png", "gif", "webp", "heic", "heif", "avif"]


def find_real_file(md5: str, preferred_ext: str) -> tuple[str, str] | None:
    """
    在分片目录里找这个 md5 真实存在的文件。

    Returns:
        (相对路径, 扩展名) 或 None
    """
    exts = [preferred_ext] + [e for e in CANDIDATE_EXTS if e != preferred_ext]
    for ext in exts:
        rel = sharded_rel_path(md5, ext)
        if IMAGES.joinpath(*rel.split("/")).is_file():
            return rel, ext
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not (args.dry_run or args.apply):
        ap.error("请指定 --dry-run 或 --apply")

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, md5, filename FROM images").fetchall()

    updates: list[tuple[str, int]] = []
    unresolved: list[str] = []
    ext_fixed = 0

    for r in rows:
        fn = (r["filename"] or "").replace("\\", "/")
        if "/" in fn:
            continue  # 已经是分片路径

        md5 = (r["md5"] or "").strip().lower()
        preferred = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""

        found = find_real_file(md5, preferred)
        if not found:
            unresolved.append(fn)
            continue

        rel, real_ext = found
        if real_ext != preferred:
            ext_fixed += 1
        if rel != fn:
            updates.append((rel, r["id"]))

    print(f"平铺行总数        : {sum(1 for r in rows if '/' not in (r['filename'] or ''))}")
    print(f"需要改写          : {len(updates)}")
    print(f"其中修正扩展名    : {ext_fixed}")
    print(f"找不到真实文件    : {len(unresolved)}")
    for u in unresolved[:10]:
        print(f"   ! {u}")

    if updates[:5]:
        print("\n样例:")
        for rel, _id in updates[:5]:
            print(f"   -> {rel}")

    if not args.apply:
        print("\n(dry-run，未写入)")
        conn.close()
        return

    cur = conn.cursor()
    cur.execute("BEGIN IMMEDIATE")
    cur.executemany("UPDATE images SET filename = ? WHERE id = ?", updates)
    conn.commit()

    left = conn.execute(
        "SELECT COUNT(*) FROM images WHERE filename NOT LIKE '%/%'"
    ).fetchone()[0]
    print(f"\n已提交 {len(updates)} 条；剩余平铺行: {left}")
    conn.close()


if __name__ == "__main__":
    main()
