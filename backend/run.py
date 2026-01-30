"""
BQBQ 后端启动脚本
"""
import os
import sys
import uvicorn

# Windows 启用 ANSI 颜色支持
if sys.platform == "win32":
    os.system("")  # 启用虚拟终端处理

if __name__ == "__main__":
    print("\033[92m=== BQBQ 后端服务器 ===\033[0m")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        access_log=True,
    )
