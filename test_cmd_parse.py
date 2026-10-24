"""命令解析全量测试。直接跑真实代码，不依赖 AstrBot 运行时。

用法：python test_cmd_parse.py
"""
import re

BASE = r"C:\000soft\AstrBotLauncher-0.2.0\AstrBot\data\plugins\astrbot_plugin_bqbq_collect"

# 从 commands.py 截取 parse_command 与词表，自己补上被依赖的小工具函数，
# 这样不需要 astrbot / PIL 等运行时依赖。
src = open(BASE + r"\commands.py", encoding="utf-8").read()

start = src.find("CMD_NONE =")
# 截到 is_lib_command 之前 —— 这样 parse_command 和 has_quoted_image 都包含在内
end = src.find("def is_lib_command")
snippet = src[start:end]

# is_index_only / strip_prefix / _first_token 若在 snippet 之外，需另取
for fn in ("is_index_only", "strip_prefix", "_first_token"):
    if f"def {fn}(" not in snippet:
        i = src.find(f"def {fn}(")
        if i > 0:
            j = src.find("\ndef ", i + 5)
            snippet = src[i:j] + "\n\n" + snippet

class AstrMessageEvent:
    """占位，供 parse_command / has_quoted_image 的类型注解求值。"""


ns = {"re": re, "AstrMessageEvent": AstrMessageEvent}
exec(snippet, ns)
parse_command = ns["parse_command"]

print("=" * 74)
print(f"{'输入':26s} {'引用图':7s} {'结果':16s} {'判定'}")
print("=" * 74)

cases = [
    # 看图：只有直接发编号
    ("1", False, "VIEW"),
    ("1 3 5", False, "VIEW"),
    ("1,3,5", False, "VIEW"),
    ("1-5", False, "VIEW"),
    ("bqbq 1", False, "SEARCH"),          # bqbq 后的数字当搜索词
    ("bqbq看 1", False, "SEARCH"),        # 该入口已删
    # 搜索
    ("bqbq 猫", False, "SEARCH"),
    ("bqbq 猫 可爱", False, "SEARCH"),
    ("bqbq 加 可爱", False, "SEARCH"),     # 中文词不再是命令
    ("bqbq 覆盖 猫", False, "SEARCH"),
    ("bqbq 删 可爱", False, "SEARCH"),
    # 标签：只认英文 + 必须引用图
    ("bqbq add 可爱", True, "ADD"),
    ("bqbq tag 猫", True, "TAG"),
    ("bqbq del 可爱", True, "DEL"),
    ("bqbq del", True, "DEL"),
    ("bqbq add 可爱", False, "SEARCH"),    # 没引用图 -> 搜索
    ("bqbq tag 猫", False, "SEARCH"),
    ("bqbq del 可爱", False, "SEARCH"),
    # 保留词
    ("bqbq 帮助", False, "SUB:help"),
    ("bqbq help", False, "SUB:help"),
    ("bqbq 统计", False, "SUB:stats"),
    ("bqbq 重置", False, "SUB:reset"),
    ("bqbq 绑定", False, "SUB:bind"),
    ("bqbq 白名单", False, "SUB:whitelist"),
    ("bqbq 登录 4821", False, "SUB:login"),
    ("bqbq 取回", False, "SUB:fetch"),
    # 其它
    ("随便说句话", False, "NONE"),
    ("bqbq", False, "COLLECT"),
]

ok = fail = 0
for text, quote, expect in cases:
    r = parse_command(text, has_quote=quote)
    got = f"SUB:{r.name}" if r.name else r.kind.upper()
    good = got == expect
    ok += good
    fail += not good
    print(f"{'OK' if good else '!!'} {text:24s} {str(quote):7s} {got:16s} {'' if good else '期望 ' + expect}")

print("=" * 74)
print(f"通过 {ok} / {ok + fail}")

# ---------------------------------------------------------------- 引用检测
print()
print("=" * 74)
print("has_quoted_image（add/tag/del 能否生效的前提）")
print("=" * 74)


class Image:
    def __init__(self, url=""): self.url = url


class Reply:
    def __init__(self, chain): self.chain = chain


class Plain:
    def __init__(self, text=""): self.text = text


class _Evt:
    def __init__(self, comps): self._c = comps
    def get_messages(self): return self._c


hq = ns["has_quoted_image"]
q_cases = [
    ("引用图片", [Reply([Plain("hi"), Image("u")]), Plain("bqbq add x")], True),
    ("引用文字", [Reply([Plain("只有文字")])], False),
    ("无引用", [Plain("bqbq add x")], False),
    ("引用多图", [Reply([Image("a"), Image("b")])], True),
    ("chain 为 None", [Reply(None)], False),
]
qok = 0
for label, comps, expect in q_cases:
    got = hq(_Evt(comps))
    good = got == expect
    qok += good
    print(f"{'OK' if good else '!!'} {label:12s} 期望={str(expect):5s} 实际={str(got):5s}")
print(f"has_quoted_image: {qok}/{len(q_cases)}")
