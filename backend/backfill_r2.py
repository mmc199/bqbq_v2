# -*- coding: utf-8 -*-
"""
补传遗漏的图片到 R2。

用途
----
在「上传后自动同步 R2」功能上线**之前**，机器人收的图只落在本地，
R2 上是缺的。这个脚本按数据库记录逐条核对，把缺的补上去。

也可以随时运行来修复任何原因造成的不同步。

用法
----
    python backfill_r2.py --dry-run      # 只列出缺哪些
    python backfill_r2.py --apply        # 真正补传
    python backfill_r2.py --since 435592 # 只处理 id 大于该值的记录
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.config import settings  # noqa: E402
from app.r2_sync import r2_target, RCLONE  # noqa: E402

IMAGES_ROOT = Path(settings.images_path)


def r2_exists(rel_path: str) -> bool:
    """查 R2 上是否已有该对象。"""
    try:
        r = subprocess.run(
            [RCLONE, "lsjson", r2_target(rel_path), "--no-mimetype", "--no-modtime"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            return False
        data = json.loads(r.stdout) if r.stdout.strip() else []
        return len(data) > 0
    except Exception:
        return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--since", type=int, default=0,
                    help="只处理 id 大于该值的记录（默认全部）")
    ap.add_argument("--limit", type=int, default=0, help="最多处理多少条（0=不限）")
    args = ap.parse_args()
    if not (args.dry_run or args.apply):
        ap.error("请指定 --dry-run 或 --apply")

    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    sql = "SELECT id, md5, filename FROM images"
    params: list = []
    if args.since:
        sql += " WHERE id > ?"
        params.append(args.since)
    sql += " ORDER BY id"
    if args.limit:
        sql += f" LIMIT {int(args.limit)}"
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    print(f"待检查记录: {len(rows)}  (since={args.since})")

    missing = []
    missing_file = 0
    t0 = time.time()
    for i, r in enumerate(rows, 1):
        rel = r["filename"]
        local = IMAGES_ROOT.joinpath(*rel.split("/"))
        if not local.is_file():
            missing_file += 1
            continue
        if not r2_exists(rel):
            missing.append((r["id"], rel, local))
        if i % 200 == 0:
            print(f"  已检查 {i}/{len(rows)}, 缺失 {len(missing)}, "
                  f"本地缺文件 {missing_file}", flush=True)

    print(f"\n检查完成（{time.time()-t0:.0f}s）")
    print(f"  R2 缺失   : {len(missing)}")
    print(f"  本地也没  : {missing_file}")
    for _, rel, _ in missing[:20]:
        print(f"    {rel}")

    if not args.apply:
        print("\n(dry-run，未上传)")
        return

    if not missing:
        print("\n无需补传")
        return

    print(f"\n开始补传 {len(missing)} 个...")
    ok = fail = 0
    for i, (rid, rel, local) in enumerate(missing, 1):
        try:
            r = subprocess.run(
                [RCLONE, "copyto", str(local), r2_target(rel),
                 "--s3-no-check-bucket", "--retries", "3"],
                capture_output=True, text=True, timeout=120,
            )
            if r.returncode == 0:
                ok += 1
            else:
                fail += 1
                print(f"  ✗ {rel}: {r.stderr.strip()[:100]}")
        except Exception as e:
            fail += 1
            print(f"  ✗ {rel}: {e}")
        if i % 20 == 0:
            print(f"  进度 {i}/{len(missing)}  成功 {ok}  失败 {fail}", flush=True)

    print(f"\n补传完成: 成功 {ok}, 失败 {fail}")


if __name__ == "__main__":
    main()
