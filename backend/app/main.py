"""
BQBQ 后端 - FastAPI 主入口
"""
import hashlib
import os
import random
import threading
import time
import glob as glob_module
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from PIL import Image
import io

from .config import settings
from .database import init_database, get_connection, rebuild_tags_dict

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

# 延迟导入路由（避免循环导入）
from .routers import images, rules, search, system

# 注册路由
app.include_router(images.router, prefix="/api/images", tags=["图片"])
app.include_router(search.router, prefix="/api", tags=["搜索"])
app.include_router(rules.router, prefix="/api/rules", tags=["规则树"])
app.include_router(system.router, prefix="/api", tags=["系统"])

# 静态文件服务（图片）
images_path = Path(settings.images_path)
images_path.mkdir(exist_ok=True)
app.mount("/images", StaticFiles(directory=images_path), name="images")

# 缩略图目录
thumbnails_path = Path(settings.thumbnails_path)
thumbnails_path.mkdir(exist_ok=True)


def extract_random_frame(img: Image.Image) -> Image.Image:
    """如果是动图，随机抽取一帧"""
    try:
        if getattr(img, "is_animated", False) and img.n_frames > 1:
            img.seek(random.randint(0, img.n_frames - 1))
    except Exception:
        pass
    return img.copy()


def create_thumbnail(source_path: Path, thumb_path: Path) -> bool:
    """
    生成缩略图
    Returns:
        bool: True 表示成功，False 表示失败
    """
    try:
        with Image.open(source_path) as img:
            frame = extract_random_frame(img)

            # 转换模式，确保兼容 JPEG
            if frame.mode not in ("RGB", "L"):
                frame = frame.convert("RGB")
            elif frame.mode == "L":
                frame = frame.convert("RGB")

            # 缩放
            frame.thumbnail(
                (settings.thumbnail_max_size, settings.thumbnail_max_size),
                Image.LANCZOS
            )

            # 确保目录存在
            thumb_path.parent.mkdir(parents=True, exist_ok=True)

            # 保存为 JPEG
            frame.save(thumb_path, "JPEG", quality=85, optimize=True)
            return True

    except Exception as e:
        print(f"Thumbnail generation failed for {source_path}: {e}")
        # 尝试复制原图作为缩略图（降级方案）
        try:
            import shutil
            shutil.copy(source_path, thumb_path)
            return True
        except Exception:
            return False


@app.get("/thumbnails/{filename}")
async def serve_thumbnail(filename: str):
    """提供缩略图服务"""
    # 获取不带后缀的文件名（即 md5）
    base_name = os.path.splitext(filename)[0]

    # 拼接强制的 jpg 缩略图文件名
    thumb_name = f"{base_name}_thumbnail.jpg"
    thumb_path = thumbnails_path / thumb_name

    if thumb_path.exists():
        return FileResponse(thumb_path)

    # 如果缩略图不存在，尝试生成
    # 查找原图
    for ext in settings.allowed_extensions:
        original_path = images_path / f"{base_name}.{ext}"
        if original_path.exists():
            if create_thumbnail(original_path, thumb_path):
                return FileResponse(thumb_path)
            break

    raise HTTPException(status_code=404, detail="缩略图不存在")


def scan_and_import_folder():
    """
    启动时扫描 images 文件夹，自动导入未在数据库中的图片。
    处理文件验证、重命名、去重、缩略图生成。
    """
    print("[Folder Scan] Starting automatic import from images folder...")

    img_folder = images_path
    if not img_folder.exists():
        print(f"[Folder Scan] Image folder not found: {img_folder}")
        return

    # 支持的图片格式
    supported_patterns = [f"*.{ext}" for ext in settings.allowed_extensions]

    # 收集所有文件路径
    all_files = []
    for pattern in supported_patterns:
        all_files.extend(img_folder.glob(pattern))
        # 也扫描大写扩展名
        all_files.extend(img_folder.glob(pattern.upper()))

    # 去重
    all_files = list(set(all_files))
    total_files = len(all_files)

    if total_files == 0:
        print("[Folder Scan] No image files found.")
        return

    print(f"[Folder Scan] Found {total_files} files to process...")

    # 获取数据库中已存在的 MD5 集合
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT md5, filename FROM images")
        rows = cursor.fetchall()
        existing_md5s = {row['md5'] for row in rows}
        md5_to_filename = {row['md5']: row['filename'] for row in rows}

    counters = {'skipped': 0, 'renamed': 0, 'error': 0}
    batch_insert_data = []

    def process_single_file(file_path: Path):
        """处理单个文件"""
        try:
            if not file_path.exists():
                return ('skipped', None)

            # 计算文件 MD5
            with open(file_path, 'rb') as f:
                file_data = f.read()

            md5 = hashlib.md5(file_data).hexdigest()
            current_filename = file_path.name

            # 检查是否已存在于数据库
            if md5 in existing_md5s:
                return ('skipped', None)

            # 新文件处理
            ext = file_path.suffix.lower() or '.jpg'
            standard_filename = f"{md5}{ext}"
            standard_path = img_folder / standard_filename

            # 重命名为标准格式
            if file_path != standard_path:
                if standard_path.exists():
                    # 目标文件已存在，删除当前重复文件
                    file_path.unlink()
                    return ('skipped', None)
                else:
                    file_path.rename(standard_path)

            # 获取图片尺寸
            try:
                with Image.open(standard_path) as img:
                    w, h = img.size
            except Exception:
                w, h = 0, 0

            file_size = len(file_data)
            file_mtime = standard_path.stat().st_mtime

            return ('new', {
                'md5': md5,
                'filename': standard_filename,
                'path': standard_path,
                'width': w,
                'height': h,
                'size': file_size,
                'mtime': file_mtime
            })

        except Exception as e:
            print(f"[Folder Scan] Error processing {file_path}: {e}")
            return ('error', None)

    def generate_thumbnail_for_item(item):
        """生成单个缩略图"""
        try:
            thumb_filename = f"{item['md5']}_thumbnail.jpg"
            thumb_path = thumbnails_path / thumb_filename
            create_thumbnail(Path(item['path']), thumb_path)
            return True
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
            elif status == 'renamed':
                counters['renamed'] += 1
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
                    "INSERT INTO images (md5, filename, created_at, width, height, file_size, tags) VALUES (?, ?, datetime(?, 'unixepoch'), ?, ?, ?, '')",
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
    print(f"  - Renamed: {counters['renamed']}")
    print(f"  - Errors: {counters['error']}")
    if thumbnail_errors > 0:
        print(f"  - Thumbnail errors: {thumbnail_errors}")
    print(f"[Folder Scan] Automatic import completed.\n")


def start_tags_dict_updater(interval_seconds: int = 900):
    """
    启动后台线程，定时更新 tags_dict。
    """
    def loop():
        while True:
            time.sleep(interval_seconds)
            try:
                rebuild_tags_dict()
            except Exception as e:
                print(f"[Tags Dict] Scheduled update failed: {e}")

    t = threading.Thread(target=loop, daemon=True, name="TagsDictUpdater")
    t.start()
    print(f"[Tags Dict] Scheduled updater started (interval: {interval_seconds}s)")


@app.on_event("startup")
async def startup():
    """应用启动时初始化"""
    init_database()

    # 扫描并导入图片文件夹
    scan_and_import_folder()

    # 重建标签字典
    rebuild_tags_dict()

    # 启动定时更新任务
    start_tags_dict_updater(settings.tags_dict_update_interval)


@app.get("/")
async def root():
    """根路径"""
    return {"message": "BQBQ API v2.0", "docs": "/docs"}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传图片文件（FormData 方式）"""
    # 验证文件类型
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    ext = file.filename.split('.')[-1].lower()
    if ext not in settings.allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")

    # 读取文件内容
    content = await file.read()

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
            return {"success": False, "error": "图片已存在（已更新时间戳）", "md5": md5}

        # 获取图片尺寸
        try:
            img = Image.open(io.BytesIO(content))
            width, height = img.size
        except Exception:
            width, height = 0, 0

        # 生成文件名（使用 MD5 避免重名）
        filename = f"{md5}.{ext}"
        file_path = images_path / filename
        file_path.write_bytes(content)

        # 生成缩略图
        thumb_filename = f"{md5}_thumbnail.jpg"
        thumb_path = thumbnails_path / thumb_filename
        create_thumbnail(file_path, thumb_path)

        # 保存到数据库
        cursor.execute(
            """INSERT INTO images (filename, md5, tags, file_size, width, height)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (filename, md5, "", len(content), width, height)
        )
        conn.commit()

        return {
            "success": True,
            "msg": "上传成功",
            "id": cursor.lastrowid,
            "filename": filename,
            "md5": md5
        }
