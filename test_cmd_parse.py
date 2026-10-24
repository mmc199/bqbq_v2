"""命令解析全量测试。直接跑真实代码，不依赖 AstrBot 运行时。"""
import importlib.util
import sys
import types

# ---- 伪造 astrbot 依赖，让 commands.py 能独立导入 ----
fake_astrbot = types.ModuleType("astrbot")
fake_api = types.ModuleType("astrbot.api")
fake_api.logger = types.SimpleNamespace(
    info=lambda *a, **k: None,
    warning=lambda *a, **k: None,
    error=lambda *a, **k: None,
)
fake_event = types.ModuleType("astrbot.api.event")


class _AstrMessageEvent:
    pass


fake_event.AstrMessageEvent = _AstrMessageEvent
fake_event.filter = types.SimpleNamespace()
sys.modules["astrbot"] = fake_astrbot
sys.modules["astrbot.api"] = fake_api
sys.modules["astrbot.api.event"] = fake_event

BASE = r"C:\000soft\AstrBotLauncher-0.2.0\AstrBot\data\plugins\astrbot_plugin_bqbq_collect"

# imagelib 只取词表常量，直接读源码避免拉入 PIL/httpx
src = open(BASE + r"\imagelib.py", encoding="utf-8").read()
ns = {}
for name in ("VIEW_WORDS", "ADD_WORDS", "TAG_WORDS", "DEL_WORDS", "TRASH_TAG"):
    i = src.find(name + " = ")
    j = src.find("\n", i)
    exec(src[i:j], ns)

print("词表:")
for k in ("VIEW_WORDS", "ADD_WORDS", "TAG_WORDS", "DEL_WORDS"):
    print(f"  {k:12s} = {ns[k]}")

# 单独解析 commands.py 的 parse_command（剥离 astrbot/imagelib 依赖）
csrc = open(BASE + r"\commands.py", encoding="utf-8").read()
start = csrc.find("CMD_NONE =")
end = csrc.find("def is_lib_command")
snippet = csrc[start:end]

header = (
    "import re\n"
    "class AstrMessageEvent: pass\n"
    "def has_quoted_image(event): return False\n"
    f"VIEW_WORDS = {ns['VIEW_WORDS']!r}\n"
    f"ADD_WORDS = {ns['ADD_WORDS']!r}\n"
    f"TAG_WORDS = {ns['TAG_WORDS']!r}\n"
    f"DEL_WORDS = {ns['DEL_WORDS']!r}\n"
    "def is_index_only(t): return bool(re.fullmatch(r'\\s*\\d+([\\s,，]+\\d+)*\\s*', t or ''))\n"
    "def strip_prefix(t):\n"
    "    m = re.match(r'^\\s*/?\\s*bqbq', t, re.IGNORECASE)\n"
    "    return t[m.end():].strip() if m else t.strip()\n"
    "def _first_token(b):\n"
    "    parts = b.split()\n"
    "    return parts[0].lower() if parts else ''\n"
)

mod = {}
exec(header + snippet, mod)
parse_command = mod["parse_command"]

print()
print("=" * 76)
print(f"{'输入':30s} {'引用图':6s} {'结果':22s} {'判定'}")
print("=" * 76)

cases = [
    # 搜索
    ("bqbq 猫", False, "SEARCH"),
    ("bqbq 统计", False, "SUB:stats"),
    ("bqbq 帮助", False, "SUB:help"),
    ("bqbq 登录 4821", False, "SUB:login"),
    ("bqbq 取回", False, "SUB:fetch"),
    ("bqbq 绑定", False, "SUB:bind"),
    ("bqbq 白名单", False, "SUB:whitelist"),
    ("bqbq 重置", False, "SUB:reset"),
    # 看图
    ("1", False, "VIEW"),
    ("1 3 5", False, "VIEW"),
    ("bqbq看 1 3", False, "VIEW"),
    ("bqbq看 1", True, "VIEW"),
    ("bqbq view 2", False, "VIEW"),
    # 标签类：有引用才生效
    ("bqbq 加 可爱", True, "ADD"),
    ("bqbq 加 可爱", False, "SEARCH"),
    ("bqbq 覆盖 猫", True, "TAG"),
    ("bqbq 覆盖 猫", False, "SEARCH"),
    ("bqbq 删 可爱", True, "DEL"),
    ("bqbq 删", True, "DEL"),
    ("bqbq 删", False, "SEARCH"),
    # 英文别名
    ("bqbq add x", True, "ADD"),
    ("bqbq tag x", True, "TAG"),
    ("bqbq del x", True, "DEL"),
    # 已删除的词 -> 搜索
    ("bqbq 添加 x", True, "SEARCH"),
    ("bqbq 查看 1", False, "SEARCH"),
    ("bqbq ban x", True, "SEARCH"),
    # 无前缀
    ("随便说句话", False, "NONE"),
    ("bqbq", False, "COLLECT"),
]

ok = fail = 0
for text, quote, expect in cases:
    r = parse_command(text, has_quote=quote)
    if r.kind == "sub":
        got = f"SUB:{r.sub}"
    else:
        got = r.kind.upper()
    good = got == expect
    ok += good
    fail += not good
    mark = "OK" if good else "!!"
    print(f"{mark} {text:28s} {str(quote):6s} {got:22s} {'' if good else '期望 ' + expect}")

print("=" * 76)
print(f"通过 {ok} / {ok + fail}")
