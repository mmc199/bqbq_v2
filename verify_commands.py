"""全命令链路静态核查：解析 -> 分发 -> 依赖。

逐条列出每个命令从入口到实现的完整路径，标出依赖的函数是否存在。
"""
import ast
import io

BASE = r"C:\000soft\AstrBotLauncher-0.2.0\AstrBot\data\plugins\astrbot_plugin_bqbq_collect"

cmd_src = io.open(BASE + r"\commands.py", encoding="utf-8").read()
main_src = io.open(BASE + r"\main.py", encoding="utf-8").read()
lib_src = io.open(BASE + r"\imagelib.py", encoding="utf-8").read()

cmd_tree = ast.parse(cmd_src)
main_tree = ast.parse(main_src)


def methods(tree, cls_name):
    for n in ast.walk(tree):
        if isinstance(n, ast.ClassDef) and n.name == cls_name:
            return [m.name for m in n.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
    return []


lib_methods = methods(cmd_tree, "LibCommands")
plugin_methods = methods(main_tree, "BqbqCollectPlugin")

print("=" * 78)
print("LibCommands 的方法")
print("=" * 78)
for m in lib_methods:
    print(f"  {m}")

print()
print("=" * 78)
print("命令链路核查")
print("=" * 78)

# 每条命令 -> 依赖
chains = [
    ("搜索  bqbq 猫", "CMD_SEARCH", "_cmd_search", ["_ensure_expand_map", "expand"]),
    ("看图  1 3", "CMD_VIEW", "_cmd_view", []),
    ("加标签 bqbq add X", "CMD_ADD", "_cmd_tag", ["_reply_images", "_fetch_component", "check_md5_ex", "update_tags"]),
    ("覆盖  bqbq tag X", "CMD_TAG", "_cmd_tag", ["_reply_images", "_fetch_component"]),
    ("删除  bqbq del", "CMD_DEL", "_cmd_tag", ["_reply_images", "_fetch_component"]),
    ("查标签 引用+bqbq", "CMD_COLLECT", "_cmd_check", ["_reply_images", "_fetch_component"]),
]

for label, kind, handler, deps in chains:
    h_ok = handler in lib_methods
    print(f"\n{label}")
    print(f"  kind={kind}  ->  {handler}  {'OK' if h_ok else 'MISSING'}")

    for d in deps:
        # 在 LibCommands 或 ImageLibClient 或模块级找
        found_in = None
        if d in lib_methods:
            found_in = "LibCommands"
        elif d in lib_src:
            found_in = "imagelib/ImageLibClient"
        elif f"def {d}" in cmd_src or f"async def {d}" in cmd_src:
            found_in = "commands(模块级)"
        print(f"     {d:24s} {'OK  ' + found_in if found_in else '!! 缺失'}")

# 保留词
print()
print("=" * 78)
print("保留词 -> _handle_reserved 分支")
print("=" * 78)
import re
reserved = re.findall(r'"([^"]+)":\s*"(\w+)"', cmd_src[cmd_src.find("RESERVED"):cmd_src.find("TAG_WORDS")])
names = sorted(set(v for _, v in reserved))
for name in names:
    has = f'if name == "{name}":' in main_src
    print(f"  {name:12s} {'OK' if has else '!! 缺少分支'}")

print()
print("=" * 78)
print("上传通道（两条独立路径）")
print("=" * 78)
checks = [
    ("main.py _upload 带 client_id", "?client_id={self.bot_client_id}" in main_src),
    ("imagelib upload 带 client_id", "_with_cid" in lib_src),
    ("imagelib update_tags 带 client_id", "_body" in lib_src),
]
for label, ok in checks:
    print(f"  {'OK' if ok else '!!'}  {label}")
