# -*- coding: utf-8 -*-
"""
回填 images 表的 file_size / width / height。

背景
----
合并旧项目 43 万行时只写了 filename/md5/tags，这三列留空（0）。
但 v2 的搜索支持按「文件大小」「分辨率」排序，
如果这些列全是 0，排序结果就没有意义。

策略
----
- file_size：用 os.stat 取，极快（43 万次 stat 约几十秒）
- width/height：需要真正解码图片，比较慢。
  用线程池并发，并且默认只处理前 N 张（--limit），可以分批跑。

用法
----
    python backfill_metadata.py --sizes                 # 只补文件大小（快）
    python backfill_metadata.py --dims --limit 50000    # 分批补尺寸
    python backfill_metadata.py --dims                  # 全量补尺寸（慢）
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.sharding import resolve_image_path  # noqa: E402

DB = Path(r"C:\000soft\qqpy机器人-git\bqbq_v2\backend\meme.db")
IMAGES = Path(r"D:\bqbq_backend\meme_images")


def backfill_sizes(apply: bool) -> None:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, md5, filename FROM images WHERE file_size = 0"
    ).fetchall()
    print(f"需要补 file_size 的行: {len(rows)}")
    if not rows:
        conn.close()
        return

    t0 = time.time()
    updates = []
    missing = 0
    for r in rows:
        p = resolve_image_path(IMAGES, r["filename"])
        if p is None:
            missing += 1
            continue
        try:
            updates.append((p.stat().st_size, r["id"]))
        except OSError:
            missing += 1

    print(f"  解析到 {len(updates)} 个, 缺失 {missing}, 耗时 {time.time()-t0:.0f}s")

    if apply and updates:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        cur.executemany("UPDATE images SET file_size = ? WHERE id = ?", updates)
        conn.commit()
        left = conn.execute("SELECT COUNT(*) FROM images WHERE file_size = 0").fetchone()[0]
        print(f"  已提交 {len(updates)} 条；剩余 file_size=0: {left}")
    elif not apply:
        print("  (dry-run)")

    conn.close()


def backfill_dims(apply: bool, limit: int | None, workers: int) -> None:
    from PIL import Image

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    sql = "SELECT id, md5, filename FROM images WHERE width = 0 OR height = 0"
    if limit:
        sql += f" LIMIT {int(limit)}"
    rows = conn.execute(sql).fetchall()
    print(f"本次需要补尺寸的行: {len(rows)}")
    if not rows:
        conn.close()
        return

    def measure(row):
        p = resolve_image_path(IMAGES, row["filename"])
        if p is None:
            return None
        try:
            with Image.open(p) as im:
                w, h = im.size
            return (w, h, row["id"])
        except Exception:
            return None

    t0 = time.time()
    updates = []
    failed = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(measure, r) for r in rows]
        for i, f in enumerate(as_completed(futs), 1):
            res = f.result()
            if res is None:
                failed += 1
            else:
                updates.append(res)
            if i % 5000 == 0:
                rate = i / max(time.time() - t0, 1e-6)
                print(f"  {i}/{len(rows)}  速度 {rate:.0f}/s  ok={len(updates)} fail={failed}",
                      flush=True)

    print(f"  测量完成: ok={len(updates)} fail={failed}, 耗时 {time.time()-t0:.0f}s")

    if apply and updates:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        cur.executemany("UPDATE images SET width = ?, height = ? WHERE id = ?", updates)
        conn.commit()
        left = conn.execute(
            "SELECT COUNT(*) FROM images WHERE width = 0 OR height = 0"
        ).fetchone()[0]
        print(f"  已提交 {len(updates)} 条；剩余未补: {left}")
    elif not apply:
        print("  (dry-run)")

    conn.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", action="store_true", help="补 file_size")
    ap.add_argument("--dims", action="store_true", help="补 width/height")
    ap.add_argument("--limit", type=int, default=None, help="本次最多处理多少行")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not (args.sizes or args.dims):
        ap.error("请指定 --sizes 或 --dims")
    apply = args.apply and not args.dry_run

    if args.sizes:
        print("=== 回填 file_size ===")
        backfill_sizes(apply)
    if args.dims:
        print("=== 回填 width/height ===")
        backfill_dims(apply, args.limit, args.workers)


if __name__ == "__main__":
    main()
