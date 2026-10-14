# -*- coding: utf-8 -*-
"""用「构造 gchat.qpic.cn URL」的方式，抢救日志里遗漏的表情包。

背景
----
合并转发里的图片 URL 带 rkey，有时效；rkey 失效后原链接就下载不了。
但 QQ 的 gchatpic 缓存仍可按 **MD5 构造**出一条稳定 URL：

    https://gchat.qpic.cn/gchatpic_new/0/0-0-{MD5}/0/{MD5}.jpg
        ?term=255&is_origin=0&client_proto=qq&client_appid=537325647
        &client_type=android&client_ver=9.1.95&client_down_type=auto&client_aio_type=aio

实测命中率约 74% —— 失败的通常是 QQ 服务器已清理的旧图，
与 URL 构造方式无关（换 6 种变体都取不到）。

用法
----
    python rescue_by_construct.py --md5-file md5s.txt --apply
    python rescue_by_construct.py --md5 83F73AFE... --apply
    python rescue_by_construct.py --md5-file md5s.txt            # 只探测不下载
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.config import settings  # noqa: E402
from app.r2_sync import sync_async  # noqa: E402
from app.sharding import sharded_rel_path, thumbnail_path  # noqa: E402

# 构造 URL 的公共查询串（与 bqbq 插件的 _build_construct_urls 保持一致）
QUERY = (
    "?term=255&is_origin=0&client_proto=qq&client_appid=537325647"
    "&client_type=android&client_ver=9.1.95&client_down_type=auto&client_aio_type=aio"
)
UA = {"User-Agent": "QQ/9.1.95.29869 CFNetwork/1568.100.1 Darwin/24.0.0"}
MAGIC = (b"GIF8", b"\x89PNG", b"\xff\xd8\xff", b"RIFF", b"BM")


def construct_urls(md5: str) -> list[str]:
    """给出该 md5 的候选构造 URL（按命中率排序）。

    Args:
        md5: 32 位 md5（大小写均可）。

    Returns:
        候选 URL 列表。
    """
    m = md5.upper()
    return [
        f"https://gchat.qpic.cn/gchatpic_new/0/0-0-{m}/0/{m}.jpg{QUERY}",
        f"https://gchat.qpic.cn/gchatpic_new/0/0-0-{m}/0/{m}.png{QUERY}",
        f"https://gchat.qpic.cn/gchatpic_new/0/0-0-{m}/0/{m}.gif{QUERY}",
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md5", action="append", default=[], help="单个 md5，可重复")
    ap.add_argument("--md5-file", help="每行一个 md5 的文件")
    ap.add_argument("--apply", action="store_true", help="真正下载并入库")
    args = ap.parse_args()

    md5s: list[str] = list(args.md5)
    if args.md5_file:
        md5s += [
            line.strip()
            for line in Path(args.md5_file).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
    if not md5s:
        ap.error("请提供 --md5 或 --md5-file")

    print(f"待处理 {len(md5s)} 个 md5")
    ok = fail = skip = 0

    with httpx.Client(timeout=60, trust_env=False, follow_redirects=True) as c:
        for i, md5 in enumerate(md5s, 1):
            md5 = md5.strip().lower()
            if len(md5) != 32:
                print(f"  [{i}] {md5} 非法 md5，跳过")
                fail += 1
                continue

            # 已入库则跳过（省一次下载）
            try:
                r = c.get(f"http://127.0.0.1:8000/api/images/check-md5/{md5}")
                if r.status_code == 200 and r.json().get("exists"):
                    print(f"  [{i}] {md5[:16]}... 后端已有，跳过")
                    skip += 1
                    continue
            except Exception:
                pass

            data = None
            for url in construct_urls(md5):
                try:
                    resp = c.get(url, headers=UA)
                    if resp.status_code == 200 and resp.content[:4].startswith(MAGIC):
                        data = resp.content
                        break
                except Exception:
                    continue

            if data is None:
                print(f"  [{i}] {md5[:16]}... ❌ 构造 URL 取不到（QQ 已清理）")
                fail += 1
                continue

            if not args.apply:
                print(f"  [{i}] {md5[:16]}... ✅ 可取 {len(data)} 字节（未下载）")
                ok += 1
                continue

            # 上传到后端（后端负责分片、缩略图、写库、同步 R2）
            try:
                up = c.post(
                    "http://127.0.0.1:8000/api/images/upload",
                    files={"file": ("auto.gif", data, "image/gif")},
                )
                if up.status_code == 200:
                    j = up.json()
                    tag = "新增" if not j.get("exists") else "重复"
                    print(f"  [{i}] {md5[:16]}... ✅ {len(data)} 字节 -> {tag}")
                    ok += 1
                else:
                    print(f"  [{i}] {md5[:16]}... ❌ 上传失败 HTTP {up.status_code}")
                    fail += 1
            except Exception as e:
                print(f"  [{i}] {md5[:16]}... ❌ 上传异常 {e}")
                fail += 1

    print(f"\n完成: 成功 {ok}, 失败 {fail}, 跳过 {skip}")
    if not args.apply:
        print("（探测模式，未下载。加 --apply 执行）")


if __name__ == "__main__":
    main()
