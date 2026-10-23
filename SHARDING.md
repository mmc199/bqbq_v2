# SHARDING.md — 43 万张图片的分片接入说明

本文档记录 **bqbq_v2 接入旧项目 43 万张表情包数据** 的完整过程与约定。

如果你只想快速理解结论：

> 图片仍然放在 `D:\bqbq_backend`，采用的是 `ab/cd/<md5>.<ext>` 两段式分片目录。
> 数据库 `images.filename` 存的是**分片相对路径**（正斜杠分隔）。
> 前端继续用 `/images/${filename}` 拼 URL，不需要任何改动。

---

## 1. 为什么要做分片

旧项目原本把 **434,018 个条目塞在同一个目录**里：

| 指标 | 迁移前 | 迁移后 |
| --- | --- | --- |
| 单目录条目数 | 434,018 | 256（顶层分片目录） |
| 每叶子目录文件数 | — | 约 5–8 个 |
| 枚举一个顶层目录下 ~1694 个文件 | 极慢 | **0.016 秒** |
| 随机定位 5000 个 DB 路径 | 极慢 | **0.44 秒** |

Windows/NTFS 对单目录海量小文件非常不友好：资源管理器卡死、`dir` 极慢、
备份和同步工具也容易出问题。分片是 Git 对象库用的同样思路。

---

## 2. 目录与路径规则

### 磁盘结构

```text
D:\bqbq_backend\
├── meme_images\
│   ├── 00\ ... ff\          # 256 个一级分片
│   │   ├── 00\ ... ff\      # 每个下面 256 个二级分片
│   │   │   └── 000036806d0e3b598068479ac72b9ea4.jpg
│   └── .stfolder\           # Syncthing 元数据，扫描时跳过
└── meme_images_thumbnail\   # 与上面完全镜像的结构
    └── 00\00\000036806d0e3b598068479ac72b9ea4_thumbnail.jpg
```

### 路径规则（唯一真源：`backend/app/sharding.py`）

```text
<md5 前 2 位>/<md5 第 3-4 位>/<md5>.<ext>
```

例：`7f5d377f8dae018434c9b5638d4a5cec.gif`
→ `7f/5d/7f5d377f8dae018434c9b5638d4a5cec.gif`

### 数据库约定

`images.filename` **存分片相对路径**，正斜杠分隔：

```text
7f/5d/7f5d377f8dae018434c9b5638d4a5cec.gif
```

这样做的好处：

1. 前端 `MemeCard.vue` 直接 `/images/${filename}` 拼 URL，天然支持分片
2. FastAPI `StaticFiles` 挂载本身就是按 URL 路径取文件，天然支持分片
3. 分片规则只依赖 md5，与存放位置解耦，不会出现「库和磁盘对不上」

---

## 3. `sharding.py` 提供的函数

| 函数 | 用途 |
| --- | --- |
| `shard_parts(stem)` | 由主名推导 `["7f","5d"]` |
| `sharded_rel_path(md5, ext)` | 入库用的相对路径 |
| `sharded_path(root, md5, ext)` | 磁盘绝对路径 |
| `thumbnail_rel_path(md5)` / `thumbnail_path(root, md5)` | 缩略图路径 |
| `resolve_image_path(root, filename)` | 把库里的 filename 安全解析成磁盘路径（含越界防护） |
| `extract_md5(filename)` | 从 filename 提取 md5 |

**兜底行为**：如果 md5 不是规范十六进制串（历史脏数据），
`sharded_rel_path` 会退化成平铺文件名，保证不丢数据、不写错路径。

---

## 4. 数据库合并（旧库 → v2）

两边的标签模型**不一样**，这是合并的核心难点：

| | 旧库 `D:\bqbq_backend\db\meme.db` | v2 `backend/meme.db` |
| --- | --- | --- |
| 标签存储 | 规范化：`tags` + `image_tags` | 单列 `tags` TEXT（空格分隔） |
| FTS5 | 无 | **必需**（触发器 + `rebuild_tags_dict()` 依赖） |
| 行数 | 434,027 | 2,590 |
| 有标签的图 | 153 | 29 |

因为 v2 的 FTS5 触发器和 `rebuild_tags_dict()` 直接读 `tags` 列，
所以**以 v2 结构为准**，把旧库的规范化标签展开成空格分隔字符串写进去。

### 合并结果

| 项目 | 数量 |
| --- | --- |
| 新增（旧库有、v2 没有） | 432,220 |
| 保留（两边都有，标签已合并） | 1,807 |
| v2 独有并补入分片目录 | 782（含 782 张缩略图） |
| **合并后总计** | **434,810** |

标签合并是**并集**，不覆盖：旧库的 `疑惑 黑人问号 ？` 和 v2 原有标签都保住了。

### 合并用到的脚本

| 脚本 | 作用 |
| --- | --- |
| `backend/merge_into_v2.py` | 主合并（`--dry-run` / `--apply`） |
| `backend/normalize_filenames.py` | 把残留的平铺 filename 改写成分片路径 |
| `backend/backfill_metadata.py` | 回填 `file_size` / `width` / `height` |

---

## 5. 代码改动清单

| 文件 | 改动 |
| --- | --- |
| `app/sharding.py` | **新增**，分片规则唯一真源 |
| `app/config.py` | `allowed_extensions` 补 `heic/heif/avif`；补分片注释 |
| `app/main.py` | 启动扫描改递归 + 快速路径；缩略图路由改 `{filename:path}`；上传/缩略图按分片落位；注册 HEIF 解码器 |
| `app/routers/images.py` | 上传、Base64 建图、删除、缩略图全部按分片落位；注册 HEIF 解码器 |
| `frontend/src/components/MemeCard.vue` | `extLabel` 先取文件名；下载名不带动目录前缀 |

### 修掉的三个真实 Bug

1. **启动扫描看不到任何图片**
   原来用 `glob("*.jpg")`（非递归），分片后一张都扫不到。改成 `os.scandir` 显式走两层。

2. **启动会读 134GB**
   原来对每个文件都「全量读入内存算 MD5」。43 万张图每次启动重算会卡死。
   现在：文件名已是 32 位 md5 就直接采用，且已入库的直接跳过。

3. **18 张图无法生成缩略图**
   数据集里有 HEIC/HEIF 图片（个别扩展名还被误写成 `.gif`）。
   v2 从未 `register_heif_opener()`，导致 Pillow 抛 `UnidentifiedImageError`。已补注册。

### 性能

| 操作 | 改动前 | 改动后 |
| --- | --- | --- |
| 启动扫描 | 100s（且扫不到） | **8.5s**（计数一致时直接跳过） |
| 缩略图请求 | 404 / 失败 | 命中率 100% |

---

## 6. 验证方式

```bash
cd backend
python -c "import app.main"                 # 能否正常导入
python merge_into_v2.py --dry-run           # 合并演练
python normalize_filenames.py --dry-run     # 路径归一演练
python backfill_metadata.py --sizes --dry-run
```

接口自测（随机抽样全链路）：

```python
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
c.get("/api/images?page=1&page_size=3").json()   # 拿到分片 filename
c.get("/images/00/be/00be....jpg")               # 原图 200
c.get("/thumbnails/00/be/00be....jpg")           # 缩略图 200
```

### 实测结果

- 随机 40 张：原图 **40/40** 返回 200，缩略图 **40/40** 返回 200
- 搜索 `total` = 434,810
- 按标签搜索命中正确
- 排序（大小/分辨率）恢复正常
- 元数据缺失：**0**（尺寸 0 缺、大小 0 缺）

---

## 7. 注意事项与后续维护

### 新增图片必须走分片

任何写图片的地方都要用 `sharding.sharded_rel_path()`，
**不要**再写 `images_path / f"{md5}.jpg"`，否则根目录会重新堆积。

### 手动扫描磁盘

**启动时不再自动扫描图片目录**（扫 45 万文件冷启动要 5-70 秒，而几乎所有
情况结论都是"没有新图"）。所有入库路径都走 API 并写库，数据库即权威来源。

确实手工往 `meme_images/` 里丢过图片、或怀疑库与磁盘不一致时：

```bash
cd backend
python scan_folder.py
```

脚本会：
- 把库外新增的图片入库并生成缩略图
- 把不在分片位置的文件挪到标准路径
- 已在库中的文件跳过（不重算 MD5）

### 备份

| 备份 | 位置 |
| --- | --- |
| v2 合并前 | `backend/backup_before_merge/meme_v2_*.db` |
| 旧库迁移前 | `D:\bqbq_backend\db\backup_before_sharding\` |

### 仍然存在的历史遗留

- `trash_bin` 目录本身已不存在，回收站语义现在**只靠 `tags` 里的 `trash_bin` 标签**表达
  （3 条历史 `trash_bin/` 路径已在本次一并归一）
- 有 1 张图库里的扩展名与真实内容不符（`.png` 实为 JPEG），
  已按磁盘真实文件修正为 `.jpg`
