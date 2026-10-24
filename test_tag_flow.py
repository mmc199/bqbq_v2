"""模拟 _cmd_tag 的完整流程，验证「未上传图片自动上传」是否生效。

用假的 ImageLibClient + 假 event，跑真实的 _cmd_tag 代码。
"""
import asyncio
import io
import re
import sys
import types

BASE = r"C:\000soft\AstrBotLauncher-0.2.0\AstrBot\data\plugins\astrbot_plugin_bqbq_collect"

# ---- 伪造 astrbot ----
fake = types.ModuleType("astrbot")
api = types.ModuleType("astrbot.api")
api.logger = types.SimpleNamespace(
    info=lambda *a, **k: None, warning=lambda *a, **k: print("  [WARN]", *a),
    error=lambda *a, **k: print("  [ERR]", *a),
)
ev = types.ModuleType("astrbot.api.event")
ev.AstrMessageEvent = type("AstrMessageEvent", (), {})


class _Filter:
    def command(self, *a, **k):
        return lambda f: f


ev.filter = _Filter()
sys.modules.update({
    "astrbot": fake, "astrbot.api": api, "astrbot.api.event": ev,
})

# ---- 伪造 .imagelib ----
imagelib = types.ModuleType("commands_test_imagelib")
imagelib.GRID_COLS = 3
imagelib.MAX_ROWS = 4
imagelib.MAX_VIEW = 3
imagelib.TRASH_TAG = "trash_bin"
imagelib._parse_index_list = lambda t: []
imagelib._parse_range = lambda t: []
imagelib.ImageLibClient = type("ImageLibClient", (), {})
sys.modules["commands_test_imagelib"] = imagelib

# ---- 读命令源码，替换相对导入 ----
src = io.open(BASE + r"\commands.py", encoding="utf-8").read()
src = src.replace("from .imagelib import", "from commands_test_imagelib import")
src = src.replace("from astrbot.api import logger", "logger = __import__('builtins').__dict__.get('_logger') or type('L',(),{'info':staticmethod(lambda *a,**k:None),'warning':staticmethod(lambda *a,**k:print('  [WARN]',*a)),'error':staticmethod(lambda *a,**k:None)})()")
src = src.replace("from astrbot.api.event import AstrMessageEvent", "AstrMessageEvent = type('AstrMessageEvent', (), {})")

mod = types.ModuleType("cmdmod")
mod.__dict__["__name__"] = "cmdmod"
exec(compile(src, "commands.py", "exec"), mod.__dict__)

LibCommands = mod.LibCommands
parse_command = mod.parse_command


# ---- 假的 ImageLibClient ----
class FakeClient:
    def __init__(self):
        self.db = {}          # md5 -> tags
        self.uploads = []

    def _md5(self, data):
        import hashlib
        return hashlib.md5(data).hexdigest()

    async def check_md5_ex(self, http, md5):
        if md5 in self.db:
            return True, f"xx/yy/{md5}.png", list(self.db[md5]), True
        return False, "", [], True

    async def upload(self, http, data):
        md5 = self._md5(data)
        self.uploads.append(md5)
        if md5 in self.db:
            return {"success": False, "exists": True}
        self.db[md5] = []
        return {"success": True, "exists": False, "md5": md5}

    async def update_tags(self, http, md5, tags):
        if md5 not in self.db:
            return False, "not found"
        self.db[md5] = list(tags)
        return True, ""


class FakeImageMarker:
    """类型名必须是 "Image"，_reply_images / has_quoted_image 按名判断。"""
    def __init__(self, data=None):
        self._data = data or b""
        self.url = ""
        self.file = ""
        self.path = ""


FakeImageMarker.__name__ = "Image"


class FakeComp(FakeImageMarker):
    """带 base64 url 的 Image，走 _fetch_component 的兜底路径。"""

    def __init__(self, data):
        super().__init__(data)

    def __getattribute__(self, name):
        if name == "url":
            import base64
            return "base64://" + base64.b64encode(object.__getattribute__(self, "_data")).decode()
        return object.__getattribute__(self, name)


FakeComp.__name__ = "Image"


class FakeReply:
    def __init__(self, chain):
        self.chain = chain


FakeReply.__name__ = "Reply"


class FakeEvent:
    def __init__(self, comps, text):
        self._comps = comps
        self.message_str = text

    def get_messages(self):
        return self._comps

    def plain_result(self, text):
        return ("PLAIN", text)


def run(text, image_data):
    """跑一次 _cmd_tag。"""
    client = FakeClient()
    lc = LibCommands(client, reply_result=True)

    img = FakeComp(image_data)
    # 关键：chain 必须是**实例属性**，且 Image 的类型名要真的是 "Image"
    event = FakeEvent([FakeReply([img])], text)

    has_quote = mod.has_quoted_image(event)
    cmd = parse_command(text, has_quote=has_quote)
    print(f"  命令={text!r}  引用={has_quote}  kind={cmd.kind}")

    results = []

    async def go():
        async for r in lc._cmd_tag(event, None, cmd.body, cmd.first, cmd.kind):
            results.append(r)

    asyncio.run(go())
    return results, client


print("=" * 70)
print("场景 A：引用一张【库里没有】的图，执行 add")
print("=" * 70)
data = b"\x89PNG\r\n\x1a\n" + b"FAKE" * 20
results, client = run("bqbq add 测试标签", data)
for kind, text in results:
    print(f"  回复: {text}")
print(f"  实际上传了: {client.uploads}")
print(f"  库内容: {client.db}")

print()
print("=" * 70)
print("场景 B：同一张图再 add 一次（应已存在，不再上传）")
print("=" * 70)
results, client2 = run("bqbq add 第二个", data)
for kind, text in results:
    print(f"  回复: {text}")
print(f"  实际上传了: {client2.uploads}")
print(f"  库内容: {client2.db}")
