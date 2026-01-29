"""
BQBQ 后端 - FastAPI 主入口
"""
import hashlib
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from PIL import Image
import io

from .config import settings
from .database import init_database, get_connection
from .routers import images, rules, search, system

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

# 注册路由
app.include_router(images.router, prefix="/api/images", tags=["图片"])
app.include_router(search.router, prefix="/api", tags=["搜索"])
app.include_router(rules.router, prefix="/api/rules", tags=["规则树"])
app.include_router(system.router, prefix="/api", tags=["系统"])

# 静态文件服务（图片）
images_path = Path(settings.images_path)
images_path.mkdir(exist_ok=True)
app.mount("/images", StaticFiles(directory=images_path), name="images")


@app.on_event("startup")
async def startup():
    """应用启动时初始化数据库"""
    init_database()


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
        if cursor.fetchone():
            return {"success": False, "error": "图片已存在", "md5": md5}

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
