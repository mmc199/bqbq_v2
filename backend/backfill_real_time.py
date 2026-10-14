# -*- coding: utf-8 -*-
"""
用旧库的 modified_time 回填 v2 的 created_at（真实时间）。

背景
----
v2 现有的 43 万行 created_at 是「合并写入时刻」——全部集中在
2026-10-03 02:10:52 ~ 02:11:21 这 29 秒内，只有 73 个不同取值。
这导致：
  - 按时间排序时，同一秒内 1 万张图顺序随机
  - 无法反映图片的真实新旧

而旧库 D:\\bqbq_backend\\db\\meme.db 的 images.modified_time
保存的是**文件真实修改时间**，跨 2026-04 ~ 2026-10 共 7 个月份。
已验证它与磁盘 mtime 完全一致（差 0 秒），数据可信。

回填优先级
----------
  1) 旧库 modified_time（非 0）      -> 231,904 行
  2) 磁盘文件 mtime（旧库该值为 0）  -> 202,123 行
  3) 保留原 created_at               -> 783 行（v2 独有，旧库没有）

用法
----
    python backfill_real_time.py --dry-run
    python backfill_real_time.py --apply
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

OLD_DB = Path(r"D:\bqbq_backend\db\meme.db")
NEW_DB = Path(r"C:\000soft\qqpy机器人-git\bqbq_v2\backend\meme.db")
IMAGES = Path(r"D:\bqbq_backend\meme_images")


def ms_to_sql(ms: int) -> str:
    """
    毫秒时间戳 -> 'YYYY-MM-DD HH:MM:SS'（本地时区）。

    注意：v2 的 created_at 是 SQLite 的 CURRENT_TIMESTAMP 格式（UTC，无时区标记），
    但旧库 modified_time 是本地时间的 epoch 毫秒。
    这里统一按本地时间写入，保证与磁盘 mtime 语义一致、排序直观。
    """
    return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M:%S")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--sample", type=int, default=10, help="打印多少条样例")
    args = ap.parse_args()
    if not (args.dry_run or args.apply):
        ap.error("请指定 --dry-run 或 --apply")
    apply = args.apply

    if not OLD_DB.is_file():
        raise SystemExit(f"旧库不存在: {OLD_DB}")

    old = sqlite3.connect(f"file:{OLD_DB}?mode=ro", uri=True)
    old.row_factory = sqlite3.Row
    new = sqlite3.connect(NEW_DB)
    new.row_factory = sqlite3.Row

    try:
        print("=== 读取旧库 modified_time ===")
        old_rows = old.execute(
            "SELECT md5, filename, modified_time FROM images"
        ).fetchall()
        print(f"  旧库记录: {len(old_rows)}")

        # 建索引：md5 -> (modified_time, filename)
        old_map: dict[str, tuple[int, str]] = {}
        for r in old_rows:
            md5 = (r["md5"] or "").strip().lower()
            if md5:
                old_map[md5] = (r["modified_time"] or 0, r["filename"] or "")

        print("\n=== 读取新库 ===")
        new_rows = new.execute("SELECT id, md5, filename, created_at FROM images").fetchall()
        print(f"  新库记录: {len(new_rows)}")

        updates: list[tuple[str, int]] = []
        from_db = 0        # 来自旧库 modified_time
        from_disk = 0      # 来自磁盘 mtime
        kept = 0           # 保留原值（旧库没有 / 都取不到）
        missing_file = 0

        t0 = time.time()
        for i, r in enumerate(new_rows, 1):
            md5 = (r["md5"] or "").strip().lower()
            entry = old_map.get(md5)

            ms = 0
            if entry:
                ms = entry[0]

            src = None
            if ms and ms > 0:
                src = "db"
            else:
                # 旧库没有时间（或为 0）-> 用磁盘 mtime
                rel = (r["filename"] or "").replace("\\", "/")
                p = IMAGES.joinpath(*rel.split("/")) if rel else None
                if p and p.is_file():
                    try:
                        ms = int(p.stat().st_mtime * 1000)
                        src = "disk"
                    except OSError:
                        ms = 0
                else:
                    missing_file += 1
                    ms = 0

            if not ms or ms <= 0:
                kept += 1
                continue

            new_ts = ms_to_sql(ms)
            if new_ts == (r["created_at"] or "")[:19]:
                kept += 1
                continue

            updates.append((new_ts, r["id"]))
            if src == "db":
                from_db += 1
            else:
                from_disk += 1

            if i % 100000 == 0:
                print(f"    已扫描 {i}/{len(new_rows)} ...", flush=True)

        print(f"\n=== 结果统计（{time.time()-t0:.1f}s）===")
        print(f"  来自旧库 modified_time : {from_db}")
        print(f"  来自磁盘 mtime         : {from_disk}")
        print(f"  保留原值               : {kept}")
        print(f"  文件不存在             : {missing_file}")
        print(f"  合计需更新             : {len(updates)}")

        # 展示更新后的时间分布
        print(f"\n=== 更新后时间分布（前 {args.sample} 个年份月份）===")
        from collections import Counter
        cnt = Counter(u[0][:7] for u in updates)
        for ym in sorted(cnt)[:args.sample]:
            print(f"    {ym}  {cnt[ym]:>7}")
        print(f"    ... 共 {len(cnt)} 个月份")

        # 展示新旧对比样例
        print(f"\n=== 新旧对比样例 ===")
        id_to_old = {r["id"]: r["created_at"] for r in new_rows}
        for ts, rid in updates[:6]:
            print(f"    id={rid:>7}  {id_to_old[rid]}  ->  {ts}")

        if not apply:
            print("\n(dry-run，未写入)")
            return

        print(f"\n=== 写入 {len(updates)} 行 ===")
        cur = new.cursor()
        cur.execute("BEGIN IMMEDIATE")
        cur.executemany("UPDATE images SET created_at = ? WHERE id = ?", updates)
        new.commit()
        print("  已提交")

        # 重建索引（时间变了，索引要跟上；SQLite 会自动维护，这里只是确保统计更新）
        cur.execute("ANALYZE")
        new.commit()
        print("  已 ANALYZE")

        # 验证
        row = new.execute(
            "SELECT COUNT(DISTINCT created_at) FROM images"
        ).fetchone()
        print(f"\n  created_at 不同取值数: {row[0]}")
        print("  顶部 5 条（created_at DESC, id DESC）:")
        for r in new.execute(
            "SELECT id, created_at, filename FROM images "
            "ORDER BY created_at DESC, id DESC LIMIT 5"
        ):
            print(f"    id={r['id']:>7} {r['created_at']} {r['filename'][:42]}")

    except Exception:
        new.rollback()
        raise
    finally:
        old.close()
        new.close()


if __name__ == "__main__":
    main()
