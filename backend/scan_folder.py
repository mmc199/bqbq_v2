"""
手动扫描图片目录，把库外新增的图片导入数据库。

【为什么是独立脚本，而不是启动时自动跑】
目录已是规范的 ab/cd/md5.ext 分片结构，且所有入库路径（机器人上传、
网页上传）都走 API 并写数据库 —— 数据库就是权威来源。启动时回扫磁盘
要遍历 45 万个文件 / 6.5 万个分片目录，冷启动实测 5-70 秒，
是启动最慢的一环，而绝大多数情况下结论都是"没有新图"。

因此改为按需执行：确实往 meme_images/ 里手工丢过图片、或怀疑库与磁盘
不一致时，跑一次本脚本即可。网站启动不再受磁盘扫描拖累。

用法
----
    cd backend
    python scan_folder.py

产出
----
· 库外新增的图片 -> 入库并生成缩略图
· 非分片位置的文件 -> 自动挪到标准分片路径
· 已在库中的文件 -> 跳过（不重算 MD5）
"""
import sys

from app.database import init_database
from app.main import scan_and_import_folder


def main() -> int:
    print("=== 手动扫描图片目录 ===")
    print("提示：网站启动时已不再自动扫描，这里是唯一的扫盘入口。\n")

    init_database()
    scan_and_import_folder()
    return 0


if __name__ == "__main__":
    sys.exit(main())
