"""
openid 身份备注管理。

用途：bot 只能拿到 openid（一串 32 位大写十六进制），
久了就忘了它对应哪个 QQ。这里提供几个简单的标记命令。

用法
----
    # 查看所有 openid（含备注、关联的 client_id 数量）
    python manage_openid.py list

    # 给 openid 加备注
    python manage_openid.py set A22C9E2359E63789C8E775ECD4A373B3 --remark "我自己" --qq 123456

    # 标记为站长本人
    python manage_openid.py set A22C9E... --remark "我自己" --owner

    # 删除某个 openid 的全部授权（踢下线所有设备）
    python manage_openid.py revoke A22C9E...

    # 查某个备注是谁
    python manage_openid.py find "我自己"
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parent / "meme.db"


def connect() -> sqlite3.Connection:
    if not DB.exists():
        sys.exit(f"找不到数据库：{DB}")
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def cmd_list(_: argparse.Namespace) -> None:
    conn = connect()
    rows = conn.execute(
        """SELECT openid, remark, qq, is_owner, client_count,
                  client_ids, first_granted, last_granted
           FROM v_openid_summary
           ORDER BY is_owner DESC, first_granted"""
    ).fetchall()

    if not rows:
        print("还没有任何 openid 记录。")
        return

    print(f"共 {len(rows)} 个 openid\n")
    print(f"{'openid':36s} {'备注':14s} {'QQ':13s} {'设备':4s} {'最近登录':20s}")
    print("-" * 96)
    for r in rows:
        owner = " ★" if r["is_owner"] else ""
        remark = (r["remark"] or "(未备注)") + owner
        print(
            f"{r['openid']:36s} {remark:14s} {(r['qq'] or '-'):13s} "
            f"{r['client_count']:<4d} {r['last_granted'] or '-':20s}"
        )

    print("\n提示：用 `python manage_openid.py set <openid> --remark \"名字\"` 加备注")
    conn.close()


def cmd_set(args: argparse.Namespace) -> None:
    conn = connect()
    exists = conn.execute(
        "SELECT 1 FROM openid_profiles WHERE openid = ?", (args.openid,)
    ).fetchone()

    if not exists:
        conn.execute(
            "INSERT INTO openid_profiles (openid) VALUES (?)", (args.openid,)
        )

    fields, values = [], []
    if args.remark is not None:
        fields.append("remark = ?")
        values.append(args.remark)
    if args.qq is not None:
        fields.append("qq = ?")
        values.append(args.qq)
    if args.owner:
        fields.append("is_owner = 1")

    if not fields:
        print("没有要修改的字段。用 --remark / --qq / --owner 指定。")
        return

    fields.append("updated_at = CURRENT_TIMESTAMP")
    values.append(args.openid)
    conn.execute(f"UPDATE openid_profiles SET {', '.join(fields)} WHERE openid = ?", values)
    conn.commit()

    row = conn.execute(
        "SELECT * FROM openid_profiles WHERE openid = ?", (args.openid,)
    ).fetchone()
    print(f"已更新：{row['openid']}")
    print(f"  备注   : {row['remark'] or '(空)'}")
    print(f"  QQ     : {row['qq'] or '(空)'}")
    print(f"  站长   : {'是' if row['is_owner'] else '否'}")
    conn.close()


def cmd_revoke(args: argparse.Namespace) -> None:
    conn = connect()
    rows = conn.execute(
        "SELECT client_id FROM auth_granted_clients WHERE openid = ?", (args.openid,)
    ).fetchall()
    if not rows:
        print(f"该 openid 没有授权记录：{args.openid}")
        return

    conn.execute("DELETE FROM auth_granted_clients WHERE openid = ?", (args.openid,))
    conn.commit()
    print(f"已撤销 {len(rows)} 个 client_id：")
    for r in rows:
        print(f"  {r['client_id']}")
    print("对应浏览器下次写操作会要求重新登录。")
    conn.close()


def cmd_find(args: argparse.Namespace) -> None:
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM v_openid_summary WHERE remark LIKE ?",
        (f"%{args.keyword}%",),
    ).fetchall()
    if not rows:
        print(f"没有备注包含「{args.keyword}」的记录。")
        return
    for r in rows:
        print(f"{r['openid']}  备注={r['remark'] or '-'}  QQ={r['qq'] or '-'}  设备={r['client_count']}")
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="openid 身份备注管理")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="列出所有 openid")
    p_list.set_defaults(func=cmd_list)

    p_set = sub.add_parser("set", help="设置备注")
    p_set.add_argument("openid")
    p_set.add_argument("--remark", help="备注名，如「我自己」")
    p_set.add_argument("--qq", help="对应 QQ 号")
    p_set.add_argument("--owner", action="store_true", help="标记为站长本人")
    p_set.set_defaults(func=cmd_set)

    p_rev = sub.add_parser("revoke", help="撤销某 openid 的全部授权")
    p_rev.add_argument("openid")
    p_rev.set_defaults(func=cmd_revoke)

    p_find = sub.add_parser("find", help="按备注搜索")
    p_find.add_argument("keyword")
    p_find.set_defaults(func=cmd_find)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
