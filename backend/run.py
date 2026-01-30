"""
BQBQ 后端启动脚本
"""
import logging
import uvicorn
from uvicorn.config import LOGGING_CONFIG

# 禁用 uvicorn 日志颜色
LOGGING_CONFIG["formatters"]["default"]["use_colors"] = False
LOGGING_CONFIG["formatters"]["access"]["use_colors"] = False

if __name__ == "__main__":
    print("=== BQBQ 后端服务器 ===")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        access_log=True,
        log_config=LOGGING_CONFIG,
    )
