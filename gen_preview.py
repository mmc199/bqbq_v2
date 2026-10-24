"""实际调用 stitch 渲染预览图，验证「编号+扩展名」的显示效果。

按行号精确截取 imagelib.py 的常量区与 stitch 方法，避免锚点漂移。
"""
import io
import sys
import types

BASE = r"C:\000soft\AstrBotLauncher-0.2.0\AstrBot\data\plugins\astrbot_plugin_bqbq_collect"

fake = types.ModuleType("astrbot")
api = types.ModuleType("astrbot.api")
api.logger = types.SimpleNamespace(
    info=lambda *a, **k: None, warning=lambda *a, **k: None, error=lambda *a, **k: None,
)
sys.modules.update({"astrbot": fake, "astrbot.api": api})

lines = open(BASE + r"\imagelib.py", encoding="utf-8").read().split("\n")

font_start_ln = next(i for i, l in enumerate(lines) if l.startswith("def _load_font"))
const_block = "\n".join(lines[109:font_start_ln])

font_start = next(i for i, l in enumerate(lines) if l.startswith("def _load_font"))
font_end = next(i for i in range(font_start + 1, len(lines)) if lines[i].startswith("def "))
font_block = "\n".join(lines[font_start:font_end])

st_start = next(i for i, l in enumerate(lines) if l.strip().startswith("def stitch("))
indent = len(lines[st_start]) - len(lines[st_start].lstrip())
st_end = st_start + 1
while st_end < len(lines):
    l = lines[st_end]
    if l.strip() and (len(l) - len(l.lstrip())) <= indent and l.strip().startswith(("def ", "class ")):
        break
    st_end += 1
st_block = "\n".join(lines[st_start:st_end])
if lines[st_start - 1].strip() == "@staticmethod":
    st_block = lines[st_start - 1] + "\n" + st_block

wrapper = (
    "import io, math\n"
    "from pathlib import Path\n"
    "from astrbot.api import logger\n\n"
    + const_block + "\n\n"
    + font_block + "\n\n"
    + "class _C:\n"
    + st_block
    + "\n"
)

ns = {"__name__": "img"}
exec(compile(wrapper, "imagelib_extract.py", "exec"), ns)
stitch = ns["_C"].stitch

from PIL import Image as PILImage


def make(color):
    b = PILImage.new("RGB", (200, 200), color)
    buf = io.BytesIO()
    b.save(buf, format="PNG")
    return buf.getvalue()


colors = [(240, 180, 60), (90, 200, 120), (100, 150, 240),
          (240, 120, 160), (160, 130, 240), (200, 200, 200)]
labels = [
    "1.jpg", "2.jpg", "3.jpg",
    "4.gif.可爱", "5.png", "6.jpg.长崎素世、长期素食",
]
pairs = [(make(c), lb) for c, lb in zip(colors, labels)]

out = stitch(pairs, header="找到 6 张", footer="获取原图：直接发编号（如 1 2 3）")
if out:
    path = r"C:\000soft\qqpy机器人-git\bqbq_v2\docs\preview-label-test.png"
    open(path, "wb").write(out)
    img = PILImage.open(io.BytesIO(out))
    print(f"OK 已生成 {path}")
    print(f"   尺寸: {img.size[0]}x{img.size[1]}")
else:
    print("!! stitch 返回 None")
