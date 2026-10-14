# -*- coding: utf-8 -*-
"""
R2 同步：把新增图片推到 Cloudflare R2（供 CDN 使用）

背景
----
前端原图走 CDN（`VITE_CDN_BASE_URL=https://bqbq-img.mmc199.com`），
而 CDN 背后是 R2 桶 `bqbq-memes`。
但后端上传图片只落在本地磁盘 —— 不同步到 R2 的话，新图在前端会 404。

设计
----
- **异步、非阻塞**：上传接口不等待 R2，避免拖慢机器人收图
- **失败不影响入库**：R2 推失败时本地文件仍在，前端会回退到本地接口
- **不重复推**：先查 R2 是否已有该对象，有则跳过
- **去重靠 MD5**：R2 本身不按内容去重，同名 key 会直接覆盖。
  但对象 key 就是 `<md5>.<ext>`，内容相同必然同 key，
  所以覆盖的也是同一个文件，不会出错。

关于「R2 会不会自动去重」
------------------------
实测结论：**不会**。
  · 同名 key、不同内容 -> 直接覆盖（旧内容丢失）
  · 不同 key、相同内容 -> 两个都存
对本项目没影响，因为 key 就是 MD5（内容指纹），天然唯一。

配置（环境变量，都可选）
------------------------
    BQBQ_R2_ENABLED       1/0，默认 1（有 rclone 就启用）
    BQBQ_R2_REMOTE        rclone remote 名，默认 "r2"
    BQBQ_R2_BUCKET        R2 桶名，默认 "bqbq-memes"
    BQBQ_R2_PREFIX        对象前缀，默认 "meme_images"
    BQBQ_R2_RCLONE        rclone 可执行文件路径，默认 "rclone"
"""
from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
R2_ENABLED = os.getenv("BQBQ_R2_ENABLED", "1").strip() not in ("0", "false", "False", "")
R2_REMOTE = os.getenv("BQBQ_R2_REMOTE", "r2").strip()
R2_BUCKET = os.getenv("BQBQ_R2_BUCKET", "bqbq-memes").strip()
R2_PREFIX = os.getenv("BQBQ_R2_PREFIX", "meme_images").strip().strip("/")
RCLONE = os.getenv("BQBQ_R2_RCLONE", "rclone").strip()

# 上传超时（秒）。图片通常几百 KB，给足余量
UPLOAD_TIMEOUT = int(os.getenv("BQBQ_R2_TIMEOUT", "120"))

# 最多并发几个同步线程，避免收图高峰时堆一堆 rclone
_MAX_WORKERS = int(os.getenv("BQBQ_R2_WORKERS", "4"))

_sem = threading.Semaphore(_MAX_WORKERS)
_stats_lock = threading.Lock()
_stats = {"ok": 0, "skip": 0, "fail": 0, "queued": 0}


def get_stats() -> dict:
    with _stats_lock:
        return dict(_stats)


def _bump(key: str, n: int = 1) -> None:
    with _stats_lock:
        _stats[key] = _stats.get(key, 0) + n


def r2_target(rel_path: str) -> str:
    """把分片相对路径映射为 R2 对象路径。"""
    rel = (rel_path or "").replace("\\", "/").lstrip("/")
    return f"{R2_REMOTE}:{R2_BUCKET}/{R2_PREFIX}/{rel}"


def _rclone_available() -> bool:
    return shutil.which(RCLONE) is not None


def object_exists(rel_path: str) -> bool:
    """查 R2 上是否已有该对象（避免重复推送）。"""
    try:
        r = subprocess.run(
            [RCLONE, "lsjson", r2_target(rel_path), "--no-mimetype", "--no-modtime"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            return False
        import json
        data = json.loads(r.stdout) if r.stdout.strip() else []
        return len(data) > 0
    except Exception:
        return False


def upload_file(local_path: Path | str, rel_path: str) -> bool:
    """
    把单个文件推到 R2。同步阻塞，调用方负责放到线程里。

    Returns:
        True 表示 R2 上已存在该对象（本次推送成功或本来就有）
    """
    local = Path(local_path)
    if not local.is_file():
        return False

    # 已经有了就跳过（省一次上传）
    if object_exists(rel_path):
        _bump("skip")
        return True

    try:
        r = subprocess.run(
            [RCLONE, "copyto", str(local), r2_target(rel_path),
             "--s3-no-check-bucket", "--retries", "3", "--low-level-retries", "10"],
            capture_output=True, text=True, timeout=UPLOAD_TIMEOUT,
        )
        if r.returncode == 0:
            _bump("ok")
            return True
        _bump("fail")
        print(f"[R2] 上传失败 {rel_path}: {r.stderr.strip()[:200]}")
        return False
    except subprocess.TimeoutExpired:
        _bump("fail")
        print(f"[R2] 上传超时 {rel_path}")
        return False
    except Exception as e:
        _bump("fail")
        print(f"[R2] 上传异常 {rel_path}: {e}")
        return False


def _worker(local_path: Path, rel_path: str) -> None:
    """线程体：带并发闸门，异常一律吞掉（绝不 back-propagate 到上传主流程）。"""
    try:
        with _sem:
            upload_file(local_path, rel_path)
    except Exception as e:  # noqa: BLE001
        _bump("fail")
        print(f"[R2] 同步线程异常 {rel_path}: {e}")


def sync_async(local_path: Path | str, rel_path: str) -> bool:
    """
    异步把文件推到 R2；立即返回，不阻塞调用方。

    上传接口（机器人收图）调用这个：R2 慢或挂了都不影响入库。

    Returns:
        True 表示已排入队列；False 表示未启用或环境不具备
    """
    if not R2_ENABLED:
        return False
    if not _rclone_available():
        # 只在首次提示，避免每张图都刷屏
        global _warned_no_rclone
        if not _warned_no_rclone:
            _warned_no_rclone = True
            print(f"[R2] 未找到 rclone（{RCLONE}），新图不会同步到 R2")
        return False

    _bump("queued")
    t = threading.Thread(
        target=_worker, args=(Path(local_path), rel_path),
        daemon=True, name=f"r2-sync-{Path(rel_path).name[:12]}",
    )
    t.start()
    return True


_warned_no_rclone = False


def check_config() -> dict:
    """启动时自检，返回当前 R2 配置状态（供日志展示）。"""
    return {
        "enabled": R2_ENABLED,
        "rclone_found": _rclone_available(),
        "rclone": RCLONE,
        "remote": R2_REMOTE,
        "bucket": R2_BUCKET,
        "prefix": R2_PREFIX,
        "target_example": r2_target("ab/cd/xxxxxxxx.gif"),
    }
