"""
BQBQ 后端 - FastAPI 主入口
"""
import hashlib
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pathlib import Path
from PIL import Image
import io

# 注册 HEIF/HEIC 解码器（可选依赖）
# 旧项目里有少量 HEIC/HEIF 图片，部分文件的扩展名还被写成了 .gif，
# 不注册的话 Pillow 会直接抛 UnidentifiedImageError，缩略图生成会失败。
try:
    from pillow_heif import register_heif_opener
except ImportError:
    register_heif_opener = None
else:
    register_heif_opener()

from .config import settings
from .database import init_database, get_connection, rebuild_tags_dict
from .image_format import resolve_upload_ext
from .sharding import (
    sharded_rel_path,
    thumbnail_path,
    resolve_image_path,
    extract_md5,
)
from .r2_sync import sync_async, check_config as r2_check_config, get_stats as r2_get_stats
from .thumbnail import create_thumbnail, create_thumbnail_for

# 创建应用
app = FastAPI(
    title="BQBQ API",
    description="表情标签管理系统 API",
    version="2.0.0",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip 压缩
#
# 【为什么需要】前端 build 后的 JS 是 311 KB，实测 gzip 后只有约 107 KB（省 65%）。
# 而实测公网链路约 0.6 Mbps，未压缩传输要 4.2 秒，压缩后约 1.4 秒。
# 本机环境测不出差别（回环带宽足够），但对公网穿透链路是明显改善。
#
# minimum_size=500：小于 500 字节的响应不压缩（压缩反而更大，且省不了几个字节）。
# 注意 middleware 的添加顺序是「后加的先执行」，放这里不影响 CORS。
app.add_middleware(GZipMiddleware, minimum_size=500)

# 延迟导入路由（避免循环导入）
from .routers import images, rules, search, system

# 注册路由
app.include_router(images.router, prefix="/api/images", tags=["图片"])
app.include_router(search.router, prefix="/api", tags=["搜索"])
app.include_router(rules.router, prefix="/api/rules", tags=["规则树"])
app.include_router(system.router, prefix="/api", tags=["系统"])

# 同一套路由再挂一份 /g2/api 前缀。
#
# 【为什么需要】前端固定用 /g2/api/xxx 调用（见 frontend/src/composables/useApi.ts），
# 以前由 Vite dev server 把 /g2/api 重写成 /api 转发给后端。
# 现在改由后端直接托管前端，没有那层重写了，所以后端自己也要认这个前缀。
#
# 两种前缀都保留，是为了兼容：本地开发仍可走 dev server 代理。
app.include_router(images.router, prefix="/g2/api/images", tags=["图片(g2)"], include_in_schema=False)
app.include_router(search.router, prefix="/g2/api", tags=["搜索(g2)"], include_in_schema=False)
app.include_router(rules.router, prefix="/g2/api/rules", tags=["规则树(g2)"], include_in_schema=False)
app.include_router(system.router, prefix="/g2/api", tags=["系统(g2)"], include_in_schema=False)

# =============================================================================
#  静态文件挂载（HTTP-only 安全版）
# =============================================================================
#
# 【为什么不用原生 StaticFiles】
# starlette 的 StaticFiles.__call__ 第一行就是：
#     assert scope["type"] == "http"
# 一旦有 WebSocket 请求打到挂载点，就会抛 AssertionError，
# uvicorn 打出一大段 traceback（实测复现）。
#
# 【什么时候会有 WebSocket 打进来】
# 前端曾用 Vite dev server（HMR 走 WebSocket），nginx 为此配置了：
#     proxy_set_header Upgrade $http_upgrade;
#     proxy_set_header Connection "upgrade";
# 换成 build 产物后前端已无 HMR，但 nginx 仍无条件升级连接，
# 于是 WebSocket 请求被转发到后端静态挂载点 —— 日志被 traceback 刷屏。
#
# 【处理方式】
# 子类化并覆盖 __call__：遇到非 HTTP 的 scope（websocket/lifespan）
# 直接优雅关闭连接，不打日志、不抛异常。
# 这样无论 nginx 怎么配、浏览器怎么请求，都不会再出现 AssertionError。
class HttpOnlyStaticFiles(StaticFiles):
    """只处理 HTTP 的 StaticFiles；遇到 WebSocket 等其它 scope 时安静拒绝。"""

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            # WebSocket：按协议要求先 accept 再 close，避免客户端报错。
            # lifespan 等其它类型直接忽略。
            if scope["type"] == "websocket":
                try:
                    await send({"type": "websocket.close", "code": 1000})
                except Exception:
                    pass
            return
        await super().__call__(scope, receive, send)


# 静态文件服务（图片）
images_path = Path(settings.images_path)
images_path.mkdir(exist_ok=True)
app.mount("/images", HttpOnlyStaticFiles(directory=images_path), name="images")

# 缩略图目录
thumbnails_path = Path(settings.thumbnails_path)
thumbnails_path.mkdir(exist_ok=True)

# =============================================================================
#  前端 build 产物托管（/g2/）
# =============================================================================
#
# 【为什么由后端托管】
# 原来前端跑 Vite dev server（5173），公网经 nginx 反代到它。但 dev 模式下
# 浏览器要逐个请求 .ts/.vue 源码（实测 28 个模块、约 2.6 MB 未压缩），
# 而且会加载 175 KB 的 HMR 客户端 —— 在公网链路上这就是几十秒。
#
# build 后全部合并成 1 个 JS + 1 个 CSS（约 310 KB + 48 KB），
# 由本后端直接托管即可，无需再跑 dev server、也无需额外反代。
#
# 访问方式不变：https://bqbq.mmc199.com/g2/
FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"


def _mount_frontend() -> None:
    """把 frontend/dist 挂到 /g2/。产物不存在时只提示，不影响后端启动。"""
    if not FRONTEND_DIST.is_dir():
        print(f"[Frontend] 未找到 build 产物: {FRONTEND_DIST}")
        print("[Frontend] 前端将不可用；请先执行: cd frontend && npm run build")
        return

    index_file = FRONTEND_DIST / "index.html"
    if not index_file.is_file():
        print(f"[Frontend] 目录存在但缺少 index.html: {FRONTEND_DIST}")
        return

    # html=True 让 /g2/ 自动返回 index.html
    # 用 HttpOnlyStaticFiles 而非原生 StaticFiles：前者遇到 WebSocket 会安静拒绝，
    # 不会抛 AssertionError 刷屏日志（nginx 仍可能转发 Upgrade 头）
    app.mount(
        "/g2",
        HttpOnlyStaticFiles(directory=FRONTEND_DIST, html=True),
        name="frontend",
    )

    assets = FRONTEND_DIST / "assets"
    n = len(list(assets.iterdir())) if assets.is_dir() else 0
    print(f"[Frontend] 已托管 build 产物: {FRONTEND_DIST} ({n} 个 asset)")
    print("[Frontend] 访问: http://127.0.0.1:8000/g2/")


_mount_frontend()


@app.get("/thumbnails/{filename:path}")
async def serve_thumbnail(filename: str):
    """提供缩略图服务；缺失时就地生成。

    【入参】前端传的是数据库里的 filename，即分片相对路径：
        7f/5d/7f5d377f8dae018434c9b5638d4a5cec.gif

    【为什么只保留这一条查找路径】
    实测全库 446,182 条记录的 filename **100% 都是标准分片路径**
    （无平铺名、无 trash_bin/ 之类目录前缀，且文件名与 md5 完全一致）。
    因此此前为"历史遗留形态"准备的四条回退分支（平铺名、带目录前缀、
    遍历 9 种扩展名猜原图、回查数据库兜底）全是死代码，只会让每次请求
    多做若干次无效的磁盘 is_file() 探测。现在按 md5 直接定位，一次命中。

    缩略图缺失时用原图就地生成 —— 这是原图新增/迁移后唯一需要兜底的场景。
    """
    requested = filename.replace("\\", "/").strip("/")
    md5 = extract_md5(requested)
    if not md5:
        raise HTTPException(status_code=404, detail="缩略图不存在")

    target = thumbnail_path(thumbnails_path, md5)
    if target.is_file():
        return FileResponse(target)

    # 缩略图缺失：用原图生成。
    # 原图路径直接由请求里的 filename 解析 —— 不需要遍历候选扩展名，
    # 因为数据库里的 filename 就是准确路径。
    original = resolve_image_path(images_path, requested)
    if original is None:
        raise HTTPException(status_code=404, detail="缩略图不存在")

    if create_thumbnail(original, target):
        return FileResponse(target)

    raise HTTPException(status_code=404, detail="缩略图不存在")


@app.post("/thumbnails/batch")
async def serve_thumbnail_batch(payload: dict):
    """
    批量打包缩略图（一次请求取回当前页全部缩略图）。

    【为什么要这个接口】
    生产链路是「中国服务器 → 内网穿透 → 美国服务器」，
    单次往返 RTT 约 200ms、带宽约 5Mbps。
    一页 50 张缩略图若逐个请求：
        9 轮 RTT × 200ms = 1800ms 的纯等待开销
    合并成 1 个请求后这部分开销降到 1 轮。

    【为什么用 ZIP_STORED（不压缩）】
    缩略图本身就是 JPEG，已经高度压缩，再套 deflate 通常只能省 1-2%，
    却要付出服务端 CPU 和前端解压时间的代价。
    实测 50 张仅多 ~0.5% 体积（ZIP 头开销），所以直接存储。

    【返回】
    application/zip，内部文件名＝ md5，前端按 md5 索引即可。
    缺失的缩略图会被跳过（不报错），前端对缺失项回退到原图接口。

    请求体：
        { "md5": ["...", "..."]  }     最多 200 个
    """
    import zipfile

    md5_list = payload.get("md5") or []
    if not isinstance(md5_list, list):
        raise HTTPException(status_code=400, detail="md5 必须是数组")
    # 限制单次数量，避免一次请求占用过多内存/带宽
    md5_list = [str(m).strip().lower() for m in md5_list if m][:200]
    if not md5_list:
        raise HTTPException(status_code=400, detail="md5 不能为空")

    # 先把要打包的文件读进内存（缩略图很小，平均约 36 KiB）
    buf = io.BytesIO()
    packed = 0
    missing: list[str] = []

    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        for md5 in md5_list:
            p = thumbnail_path(thumbnails_path, md5)
            if not p.is_file():
                missing.append(md5)
                continue
            try:
                zf.write(p, arcname=md5)   # 文件名就是 md5，前端直接索引
                packed += 1
            except OSError:
                missing.append(md5)

    if packed == 0:
        raise HTTPException(status_code=404, detail="本页缩略图均不存在")

    buf.seek(0)
    headers = {
        # 缩略图按 md5 命名，内容不变，可长缓存
        "Cache-Control": "public, max-age=86400",
        # 把缺失清单告知前端，便于回退
        "X-Packed-Count": str(packed),
        "X-Missing-Count": str(len(missing)),
    }
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers=headers,
    )


def scan_and_import_folder():
    """
    扫描图片目录，导入未在数据库中的图片。

    【何时运行】
    **不再在启动时自动运行**（见 startup 的说明）。现在只在手动执行
    `python scan_folder.py` 时调用，用于库外的意外改动需要核对时。

    【分片改造要点】
    1. 目录是 ab/cd/md5.ext 两段式分片结构，必须递归扫描，不能用
       glob("*.jpg")，否则一张图都扫不到。
    2. 已入库的文件直接跳过，不重新计算 MD5：
       45 万张图全量算一遍 MD5 要读 134GB，耗时不可接受。
    3. 新文件按分片规则落位，不再平铺到根目录。
    4. 文件名已经是 md5 的，直接采用文件名作为 md5，不用读文件内容。
    """
    print("[Folder Scan] Starting import from images folder...")

    img_folder = images_path
    if not img_folder.exists():
        print(f"[Folder Scan] Image folder not found: {img_folder}")
        return

    allowed = {e.lower().lstrip(".") for e in settings.allowed_extensions}

    # 1) 先取数据库现状：md5 集合
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT md5, filename FROM images")
        rows = cursor.fetchall()
        existing_md5s = {row["md5"].lower() for row in rows}

    print(f"[Folder Scan] DB 中已有 {len(existing_md5s)} 条记录")

    # 2) 递归收集文件（跳过垃圾目录）
    #
    # 【性能】刻意不用 Path.rglob：45 万文件下 rglob 会为每个条目构造
    # Path 对象并反复 stat，实测 60s+。改用 os.scandir 显式走两层分片目录，
    # DirEntry 自带缓存属性，快得多。
    def iter_image_files():
        try:
            with os.scandir(img_folder) as top:
                for d1 in top:
                    if not d1.is_dir(follow_symlinks=False):
                        # 根目录下偶尔残留的文件也要处理
                        if d1.is_file(follow_symlinks=False):
                            if d1.name.rsplit(".", 1)[-1].lower() in allowed:
                                yield Path(d1.path)
                        continue
                    if d1.name.startswith("."):
                        continue
                    with os.scandir(d1.path) as mid:
                        for d2 in mid:
                            if d2.is_dir(follow_symlinks=False):
                                # 分片第二层
                                with os.scandir(d2.path) as leaf:
                                    for f in leaf:
                                        if not f.is_file(follow_symlinks=False):
                                            continue
                                        if f.name.rsplit(".", 1)[-1].lower() in allowed:
                                            yield Path(f.path)
                            elif d2.is_file(follow_symlinks=False):
                                # 兼容 trash_bin 这类历史单层目录
                                if d2.name.rsplit(".", 1)[-1].lower() in allowed:
                                    yield Path(d2.path)
        except OSError as e:
            print(f"[Folder Scan] 目录遍历失败: {e}")

    all_files = list(iter_image_files())
    total_files = len(all_files)
    print(f"[Folder Scan] 磁盘上发现 {total_files} 个图片文件")

    if total_files == 0:
        print("[Folder Scan] No image files found.\n")
        return

    counters = {"skipped": 0, "moved": 0, "error": 0}
    batch_insert_data = []

    def process_single_file(file_path: Path):
        """处理单个文件：判断是否需要入库 / 是否需要挪进分片目录"""
        try:
            stem = file_path.stem.lower()
            ext = file_path.suffix.lower().lstrip(".")

            # 主名已经是 32 位十六进制（md5 命名）时，直接用主名当 md5，
            # 避免为了算 md5 而读取整个文件。
            is_md5_name = len(stem) == 32 and all(
                c in "0123456789abcdef" for c in stem
            )

            if is_md5_name and stem in existing_md5s:
                return ("skipped", None)

            if not is_md5_name:
                # 非 md5 命名：需要读内容算 md5（少量文件，可接受）
                with open(file_path, "rb") as f:
                    md5 = hashlib.md5(f.read()).hexdigest()
                if md5 in existing_md5s:
                    return ("skipped", None)
            else:
                md5 = stem

            # 计算标准分片位置
            rel = sharded_rel_path(md5, ext)
            standard_path = img_folder.joinpath(*rel.split("/"))

            # 如果不在标准位置，挪过去（同一卷内是元数据 rename，很快）
            if file_path != standard_path:
                if standard_path.exists():
                    try:
                        file_path.unlink()  # 目标已存在，删掉这个重复文件
                    except OSError:
                        pass
                    return ("skipped", None)
                standard_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    file_path.rename(standard_path)
                except OSError as e:
                    print(f"[Folder Scan] 移动失败 {file_path}: {e}")
                    return ("error", None)

            # 读取尺寸与大小（只对新文件做，数量少）
            try:
                with Image.open(standard_path) as img:
                    w, h = img.size
            except Exception:
                w, h = 0, 0

            return ("new", {
                "md5": md5,
                "filename": rel,
                "path": standard_path,
                "width": w,
                "height": h,
                "size": standard_path.stat().st_size,
                "mtime": standard_path.stat().st_mtime,
            })

        except Exception as e:
            print(f"[Folder Scan] Error processing {file_path}: {e}")
            return ("error", None)

    def generate_thumbnail_for_item(item):
        """生成单个缩略图（按分片规则落位）"""
        try:
            return create_thumbnail_for(Path(item['path']), item['md5'])
        except Exception as e:
            print(f"[Folder Scan] Thumbnail error for {item['md5']}: {e}")
            return False

    # 并行处理文件
    print("[Folder Scan] Phase 1: Processing files (MD5, rename, dimensions)...")
    max_workers = min(8, os.cpu_count() or 4)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_single_file, fp): fp for fp in all_files}

        processed = 0
        for future in as_completed(futures):
            processed += 1
            try:
                status, data = future.result()
            except Exception:
                status, data = 'error', None

            if status == 'skipped':
                counters['skipped'] += 1
            elif status == 'error':
                counters['error'] += 1
            elif status == 'new' and data:
                batch_insert_data.append(data)

            if processed % 100 == 0:
                print(f"[Folder Scan] Progress: {processed}/{total_files} files processed...")

    # 批量插入数据库
    imported_count = 0
    if batch_insert_data:
        print(f"[Folder Scan] Phase 2: Batch inserting {len(batch_insert_data)} records to database...")

        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(
                    """INSERT INTO images (md5, filename, created_at, width, height, file_size, tags)
                       VALUES (?, ?, datetime(?, 'unixepoch'), ?, ?, ?, '')""",
                    [(item['md5'], item['filename'], item['mtime'], item['width'], item['height'], item['size'])
                     for item in batch_insert_data]
                )
                conn.commit()
            imported_count = len(batch_insert_data)
        except Exception as e:
            print(f"[Folder Scan] Database insert error: {e}")
            counters['error'] += len(batch_insert_data)

    # 并行生成缩略图
    thumbnail_errors = 0
    if batch_insert_data:
        print(f"[Folder Scan] Phase 3: Generating {len(batch_insert_data)} thumbnails in parallel...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(generate_thumbnail_for_item, item) for item in batch_insert_data]

            completed = 0
            for future in as_completed(futures):
                completed += 1
                try:
                    if not future.result():
                        thumbnail_errors += 1
                except Exception:
                    thumbnail_errors += 1

                if completed % 100 == 0:
                    print(f"[Folder Scan] Thumbnails: {completed}/{len(batch_insert_data)} generated...")

    print(f"\n[Folder Scan] Summary:")
    print(f"  - Imported: {imported_count}")
    print(f"  - Skipped (already in DB): {counters['skipped']}")
    print(f"  - Errors: {counters['error']}")
    if thumbnail_errors > 0:
        print(f"  - Thumbnail errors: {thumbnail_errors}")

    print(f"[Folder Scan] Import completed.\n")


def start_tags_dict_updater(interval_seconds: int = 900):
    """
    启动后台线程，定时重建 tags_dict。

    【为什么这里必须 force=True】
    rebuild_tags_dict() 非 force 时的语义是「已有数据就复用」，那是给
    **启动阶段**省时间的（见 startup）。定时任务恰好相反：它的整个存在
    意义就是**刷新**。若在这里也走"非空就跳过"，字典将永远不会更新。

    【成本】实测一次完整重建约 0.34 秒 —— 全库 45 万行里只有约 188 行
    带标签，其余被 `WHERE tags != ''` 过滤掉了，真正要统计的标签很少。
    因此每 15 分钟跑一次的开销可以忽略，无需再做"变了才重建"的优化
    （那需要先算一个 0.29 秒的签名，反而几乎省不下时间）。
    """
    def loop():
        while True:
            time.sleep(interval_seconds)
            try:
                rebuild_tags_dict(force=True)
            except Exception as e:
                print(f"[Tags Dict] Scheduled update failed: {e}")

    t = threading.Thread(target=loop, daemon=True, name="TagsDictUpdater")
    t.start()
    print(f"[Tags Dict] Scheduled updater started (interval: {interval_seconds}s)")


@app.on_event("startup")
async def startup():
    """应用启动时初始化。

    【为什么启动时不再扫描图片目录】
    目录已是规范的 ab/cd/md5.ext 分片结构，且所有入库路径（机器人上传、
    网页上传）都走 API 并写数据库 —— 数据库就是权威来源，磁盘不需要回扫。
    而扫描 45 万文件/6.5 万分片目录，冷启动要 5-70 秒，是启动最慢的一环。

    需要核对磁盘与数据库时，手动执行：
        python scan_folder.py            # 增量（按分片 mtime 只查变化的分片）
        python scan_folder.py --force    # 全量逐个比对
    详见 backend/scan_folder.py。
    """
    init_database()

    # 重建标签字典
    rebuild_tags_dict()

    # 启动定时更新任务
    start_tags_dict_updater(settings.tags_dict_update_interval)

    # R2 同步自检：把状态打到日志，便于确认新图会不会推上 CDN
    cfg = r2_check_config()
    if not cfg["enabled"]:
        print("[R2] 同步已禁用（BQBQ_R2_ENABLED=0）")
    elif not cfg["rclone_found"]:
        print(f"[R2] ⚠ 未找到 rclone（{cfg['rclone']}），新图不会同步到 R2")
        print("[R2]    前端原图走 CDN，新图可能 404；请安装 rclone 或设 BQBQ_R2_ENABLED=0")
    else:
        print(f"[R2] 同步已启用: {cfg['target_example']}")
        print(f"[R2]    源目录: {images_path}")


@app.get("/")
async def root():
    """根路径"""
    return {"message": "BQBQ API v2.0", "docs": "/docs"}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    上传图片文件（FormData 方式）。

    返回字段与 /api/images/upload 保持一致：
        exists=True  表示本次上传前该图已存在（命中重复）
        exists=False 且 success=True 表示新图已写入
    """
    # 验证文件类型
    if not file.filename:
        return {"success": False, "exists": False, "msg": "no filename"}

    # 读取文件内容
    content = await file.read()
    if not content:
        return {"success": False, "exists": False, "msg": "empty file"}

    # 【关键】扩展名以**文件头**为准，绝不信任 file.filename。
    # 机器人传的固定是 ("auto.gif", data, "image/gif")，直接用会让
    # JPEG 存成 .gif（详见 image_format.resolve_upload_ext）。
    try:
        ext = resolve_upload_ext(content, file.filename)
    except ValueError as e:
        return {"success": False, "exists": False, "msg": str(e)}

    # 计算 MD5
    md5 = hashlib.md5(content).hexdigest()

    # 检查是否已存在
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM images WHERE md5 = ?", (md5,))
        existing = cursor.fetchone()
        if existing:
            # 重复图片：更新上传时间
            cursor.execute("UPDATE images SET created_at = CURRENT_TIMESTAMP WHERE md5 = ?", (md5,))
            conn.commit()
            return {"success": False, "exists": True, "msg": "duplicate", "md5": md5}

        # 获取图片尺寸
        try:
            img = Image.open(io.BytesIO(content))
            width, height = img.size
        except Exception:
            width, height = 0, 0

        # 生成文件名（使用 MD5 避免重名）并按分片规则落盘
        rel_filename = sharded_rel_path(md5, ext)
        file_path = images_path.joinpath(*rel_filename.split("/"))
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)

        # 生成缩略图（同样按分片规则）
        create_thumbnail_for(file_path, md5)

        # 保存到数据库（filename 存分片相对路径）
        cursor.execute(
            """INSERT INTO images (filename, md5, tags, file_size, width, height)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (rel_filename, md5, "", len(content), width, height)
        )
        conn.commit()

    # 异步推到 R2（供 CDN 使用），不阻塞响应
    sync_async(file_path, rel_filename)

    return {"success": True, "exists": False, "msg": md5, "md5": md5}
