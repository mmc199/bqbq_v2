# -*- coding: utf-8 -*-
"""分析 probe 插件 dump 出来的消息结构。

用法（在 AstrBot 目录下执行）：
    venv\\Scripts\\python.exe analyze_probe.py

重点看合并转发消息里：
  1. 图片 URL 出现在 raw_data / msg_elements / components 的哪一层
  2. components 里有没有 Node / Nodes / Image 组件
  3. 文件名（MD5）能否作为去重依据
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

DUMP = Path(
    r"C:\000soft\AstrBotLauncher-0.2.0\AstrBot\data\plugin_data"
    r"\astrbot_plugin_bqbq_probe\probe_dump.jsonl"
)


def walk(node, path="$", depth=0, out=None):
    """遍历结构，记录每个键的路径与类型。"""
    if out is None:
        out = []
    if depth > 8:
        return out
    if isinstance(node, dict):
        for k, v in node.items():
            p = f"{path}.{k}"
            out.append((p, type(v).__name__, len(v) if isinstance(v, (list, dict, str)) else ""))
            walk(v, p, depth + 1, out)
    elif isinstance(node, list):
        for i, v in enumerate(node[:5]):  # 只看前几个，避免爆量
            p = f"{path}[{i}]"
            out.append((p, type(v).__name__, len(v) if isinstance(v, (list, dict, str)) else ""))
            walk(v, p, depth + 1, out)
    return out


def main() -> None:
    if not DUMP.exists():
        print(f"未找到 dump 文件: {DUMP}")
        print("请确认：1) 插件已加载  2) 已发送含图片/合并转发的消息")
        return

    lines = DUMP.read_text(encoding="utf-8").splitlines()
    print(f"=== dump 文件: {len(lines)} 条记录 ===\n")

    records = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except Exception:
            pass

    # 找合并转发（url 数最多的那条最可能是）
    records.sort(key=lambda r: r.get("url_count", 0), reverse=True)

    for idx, rec in enumerate(records[:3], 1):
        print(f"{'='*70}")
        print(f" 记录 #{idx}  时间={rec.get('ts')}  urls={rec.get('url_count')}")
        print(f"{'='*70}")
        print(f"  平台      : {rec.get('platform')}")
        print(f"  群/发送者 : {rec.get('group_id')} / {rec.get('sender_id')}")
        print()

        print("  --- components（AstrBot 解析出的组件链）---")
        comps = rec.get("components") or []
        if not comps:
            print("    (空)")
        for c in comps:
            cls = c.get("__class__") if isinstance(c, dict) else type(c).__name__
            print(f"    {cls}: {json.dumps(c, ensure_ascii=False)[:160]}")
        print()

        print("  --- raw_data 顶层键 ---")
        rd = rec.get("raw_data")
        if isinstance(rd, dict):
            for k, v in rd.items():
                t = type(v).__name__
                sz = len(v) if isinstance(v, (list, dict, str)) else ""
                print(f"    {k:22} {t:8} {sz}")
        else:
            print(f"    (无，值={rd})")
        print()

        print("  --- msg_elements ---")
        me = rec.get("msg_elements")
        if isinstance(me, list) and me:
            print(f"    共 {len(me)} 个元素")
            for i, el in enumerate(me[:4]):
                if isinstance(el, dict):
                    print(f"    [{i}] keys={list(el.keys())}")
                    print(f"        {json.dumps(el, ensure_ascii=False)[:250]}")
        else:
            print(f"    (无或空，值={str(me)[:80]})")
        print()

        print("  --- 提取到的 URL（前 5 条）---")
        for u in (rec.get("urls") or [])[:5]:
            print(f"    {u[:130]}")
        print()

        # 关键判断
        print("  --- 初步判断 ---")
        has_nodes = any(
            (c.get("__class__") if isinstance(c, dict) else "") in
            ("Node", "Nodes", "Forward")
            for c in comps
        )
        print(f"    components 含 Node/Nodes/Forward : {has_nodes}")
        print(f"    raw_data 存在                    : {isinstance(rd, dict) and bool(rd)}")
        print(f"    msg_elements 存在                : {isinstance(me, list) and bool(me)}")
        rc = rec.get("url_count", 0)
        src = []
        if rc:
            # 判断 URL 来自哪一层
            def count_urls(n):
                c = 0
                if isinstance(n, str) and n.startswith("http"):
                    c += 1
                elif isinstance(n, dict):
                    for v in n.values():
                        c += count_urls(v)
                elif isinstance(n, list):
                    for v in n:
                        c += count_urls(v)
                return c
            src.append(f"raw_data={count_urls(rd)}")
            src.append(f"msg_elements={count_urls(me)}")
            src.append(f"message_str={count_urls(rec.get('message_str'))}")
        print(f"    URL 来源分布                    : {', '.join(src) if src else 'n/a'}")
        print()

    # 全局统计
    print(f"{'='*70}")
    print(" 全局统计")
    print(f"{'='*70}")
    c = Counter()
    for r in records:
        c[r.get("url_count", 0)] += 1
    print(f"  各记录 URL 数分布: {dict(sorted(c.items()))}")
    print(f"  有 raw_data 的记录: {sum(1 for r in records if r.get('raw_data'))}/{len(records)}")
    print(f"  有 msg_elements 的记录: {sum(1 for r in records if r.get('msg_elements'))}/{len(records)}")


if __name__ == "__main__":
    main()
