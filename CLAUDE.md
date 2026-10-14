# CLAUDE.md

本文件为 AI 助手（Claude / Codex / 其他代理）在本仓库中工作时提供指导。

这份文档要同时满足两个目标：

1. **对 AI 清晰**：快速理解当前代码与迁移背景。
2. **对新手友好**：即使你主要依赖 AI 编程，也能看懂项目大致结构与修改入口。

---

## ⚠️ 最重要：代码编辑原则

**必须严格遵守以下原则，防止文件损坏或内容丢失：**

1. **分段编辑** - 每次只修改一小部分代码，不要一次性重写整个文件
2. **验证完整性** - 修改后读取文件确认内容正确
3. **避免大量写入** - 超过 200-300 行的修改应该分多次进行
4. **先读后写** - 写入文件前必须先读取，了解现有内容
5. **控制上下文** - 避免一次性读取大量无关文件，防止上下文过长导致遗漏细节
6. **乱码检查** - 修改后确认中文显示正常，必要时以 UTF-8 读取/写入
7. **文档联动** - 改动关键功能后，同步更新相关 `.md` 文档，不要让文档落后于代码
8. **保留示意图** - 架构图、流程图、迁移说明是高价值内容，更新时优先补充，不要轻易删掉

---

## 🔥 高频踩坑清单（改代码前先扫一眼）

这些是本项目**实际踩过**的坑，每条都有数据和源码依据。
AstrBot 插件相关的详细版见 [`ASTRBOT_PLUGIN.md`](ASTRBOT_PLUGIN.md)。

### 通用：先验证，再下结论

**最大的教训**：我曾基于源码推断「URL 一定是 https」，结果框架在中间
偷偷把图片下载到本地并覆盖了字段，推断全错，还差点把 bug 说成"平台限制"。

> **拿不准就写个只读钩子抓真实数据。** 24 条真实 dump 比看几小时源码有用。
> 已保留诊断插件 `astrbot_plugin_bqbq_probe_single` 供随时使用。

### ⚠️ 两套机器人的能力边界完全不同（别混淆）

| | 官方机器人 `bv199` | 非官方 `bqbq` |
| --- | --- | --- |
| 框架 | AstrBot（`qq_official_webhook`） | NoneBot2（OneBot v11） |
| **群内全部消息** | ❌ **收不到** | ✅ 能收到 |
| 私聊 / @机器人 | ✅ | ✅ |
| 收集方式 | **用户主动 @** | 可默默收集 |
| 代码位置 | `AstrBot\data\plugins\astrbot_plugin_bqbq_collect` | `D:\bqbq_bot_dev\...\plugins\bqbq` |

**QQ 官方机器人当前只能收到私聊和 @机器人的群消息。**

⚠️ **注意原因**：不是技术不支持，而是**权限未开放**。
API 是存在的（`GROUP_MESSAGE_CREATE` 全量模式），但
[官方 FAQ](https://bot.q.qq.com/wiki/bot_FAQ/) 说明：

> 公开全量使用：当前该能力正在对**企业开发者灰度**，
> 后续会推全到个人认证，请耐心等待。

且需要**群主**在手机 QQ 的群机器人设置里允许"接收群内全部消息"
（是群主侧开关，不是开发者后台配置）。

**所以：官方机器人上「自动收集群里所有表情包」当前做不到**，
只能靠用户主动 @ 触发。若将来权限开放，这个结论要改。

### ⚠️ 私聊与群聊的结构完全不同（写代码必须分开处理）

| | **私聊** | **群聊（@机器人 / 引用）** |
| --- | --- | --- |
| `get_group_id()` | `''` 空 | 群 openid |
| `raw_message_type` | `0` | `103`（引用） |
| **components** | `[At, Plain, Image]` | `[Reply, At, Plain]` |
| **图片在哪** | 顶层 `Image` | **`Reply.chain` 里** |
| **`message_str`** | `''` / `'[表情]'` | `'bqbq收图'` |

**两个后果**：

1. **私聊没有文字** → 不能用触发词把关，否则永远收不到
2. **群聊图片在 `Reply.chain`** → 只过滤顶层 `Image` 会漏

所以：私聊发图即收；群聊必须带触发词 `bqbq收图`。

### AstrBot：`should_call_llm()` 参数是**反的**

```python
# 消费端判断（stage.py:59）：and not event.call_llm
event.should_call_llm(True)    # ✅ 跳过 LLM
event.should_call_llm(False)   # ❌ 无效（默认值本来就是 False）
```

**方法名说"是否调用"，但要"禁止"必须传 `True`。**

### AstrBot：框架会覆盖 Image 组件的字段

`preprocess_stage` 把图片下载到 `data/temp/`，然后把
`url` / `file` / `path` **全部覆盖成本地路径**。

**普通消息应当直接读本地文件**，拿本地路径去 httpx 会抛
`UnsupportedProtocol`。但**合并转发不会**被本地化（图片藏在 `Plain.text` 里）。

### 解析逐行文本：**绝不能开 `re.DOTALL`**

```python
r"(?P<mid>.*?)"  + re.DOTALL   # ❌ 跨行吞掉下一条，md5 与 URL 张冠李戴
r"[^\n]*?"                     # ✅ 限定同一行
```

**测试用例必须覆盖"缺字段"的情况**，否则测不出这类 bug。

### 排查下载失败：两种情况必须区分

| 来源 | 信号 | 含义 |
| --- | --- | --- |
| 原链接 `multimedia.nt.qq.com.cn` | `x-errno: -5503042` | rkey 过期 |
| 构造 URL `gchat.qpic.cn` | `x-errno: -6101` | 存储层无此对象 |

两种错误码**都在 `x-errno` 响应头里**，只看 JSON body 会漏。

### 分页/滚动加载：必须补"内容是否可滚动"检查

只挂 `scroll` 事件会在「一屏装得下」时**永久卡死**
（`scrollHeight == clientHeight` → 没有滚动条 → 永不触发）。
详见 [`BUILD_TROUBLESHOOTING.md`](BUILD_TROUBLESHOOTING.md) 第三节。

### Windows 环境

- **含中文的 PowerShell 脚本必须存成 UTF-8 with BOM**，否则 PS 5.1 读成乱码
- **`npm run build` 需要 Node ≥ 26**，Node 24.12.0 会崩（`0xC0000409`）
- 杀进程前**先查命令行和端口占用**：`Get-CimInstance Win32_Process`。
  我曾误判 `python main.py` 是自己的残留，实际是**别人的 AstrBot 和公网 API**

---

## 语言偏好

本项目使用 **中文** 进行问答、说明和大部分注释。请始终使用中文回复。

如果要给新手解释问题，优先采用：

- 先说结论
- 再说原因
- 最后指出代码位置

---

## 项目背景（非常重要）

这个仓库并不是从零开始的新项目，而是一次**旧项目重构迁移**：

- **旧项目**：`C:\000soft\qqpy机器人-git\bqbq_backend-1\精确搜索SQLite端(旧)`
- **新项目**：`C:\000soft\qqpy机器人-git\bqbq_v2`

### 迁移目标

把旧项目从：

- Flask + 原生 JavaScript + 单文件重逻辑前端

迁移到：

- FastAPI + Vue 3 + TypeScript + Pinia + Vite

### 迁移时保留的旧项目思想

虽然技术栈换了，但下面这些“旧项目理念”被大量保留了：

1. **语义森林 / 关键词膨胀**
2. **基于版本号的 CAS 并发控制**
3. **LocalStorage / 缓存优先的前端体验**
4. **FTS5 搜索 + 标签体系**
5. **尽量兼容旧接口字段和旧交互习惯**

也就是说：

- **代码已经是新架构**
- **产品逻辑和交互心智仍然大量继承旧项目**

这也是为什么文档必须保留“迁移说明风格”。

---

## 项目概述

BQBQ v2（表情标签）是一个基于**语义森林**的图片标签管理系统，用于组织、搜索和维护表情包 / 梗图。

### 当前技术栈

- 前端：Vue 3 + TypeScript + Vite + Tailwind CSS + Pinia
- 后端：FastAPI + Pydantic + SQLite3 + FTS5 + Pillow

### 当前运行形态

- 前后端分离开发
- 前端通常运行在 `http://localhost:5173`
- 后端通常运行在 `http://localhost:8000`
- 用户常常自己启动前后端热更新服务，所以**小改动不必反复整站 build**

### 相关文档

- `SHARDING.md` - **43 万张图片的分片接入说明（重要，改动图片路径前必读）**
- `PAGINATION_PERF.md` - 分页性能优化、时间戳回填、语义修复
- `BUILD_TROUBLESHOOTING.md` - **构建崩溃根因（Node 版本）+ 缩略图批量加载**
- `R2_UPLOAD.md` - R2 上传与 CDN 配置
- `ARCHITECTURE.md` - 架构设计与流程图
- `MIGRATION_STATUS.md` - 迁移状态、差异说明、历史整理
- `frontend/README.md` - 前端项目说明

---

## ⚠️ 环境要求：Node 必须 ≥ 26

**Node 24.12.0 在 Windows 上会导致 `npm run build` 崩溃**
（退出码 `0xC0000409`，无错误信息）。

| Node | `npm run build` |
| --- | --- |
| 24.12.0 | ❌ 崩溃（9/9 稳定复现） |
| **26.7.0** | ✅ 成功 |

升级：`winget install --id OpenJS.NodeJS`

> 注意包名是 `OpenJS.NodeJS`，不是 `OpenJS.NodeJS.22` 这类固定大版本。
> 详细排查过程见 `BUILD_TROUBLESHOOTING.md`。

`npm run dev`（热更新）不受此问题影响。

---

## ⚠️ 图片存储：md5 两段式分片（必读）

当前 `meme_images` / `meme_images_thumbnail` 采用的是 **Git 对象库风格的分片目录**：

```text
meme_images/<md5 前2位>/<md5 第3-4位>/<md5>.<ext>
meme_images/7f/5d/7f5d377f8dae018434c9b5638d4a5cec.gif
```

原因：数据集有 **43 万张图片**，平铺在单目录会让 Windows 枚举极慢。

### 三条硬性约定

1. **`images.filename` 存分片相对路径**（正斜杠分隔），例如 `7f/5d/xxx.gif`。
   不要存绝对路径，也不要只存文件名。
2. **任何新增/移动图片都必须调用 `app/sharding.py`**：
   ```python
   from .sharding import sharded_rel_path, thumbnail_path, resolve_image_path
   rel  = sharded_rel_path(md5, ext)        # 入库用
   path = images_path.joinpath(*rel.split("/"))
   ```
   禁止再写 `images_path / f"{md5}.{ext}"`，否则根目录会重新堆积。
3. **不要用 `glob("*.jpg")` 扫描图片目录**，必须递归
   （`os.scandir` 两层或 `rglob`），否则一张都扫不到。

详细说明、验证方式与踩坑记录见 `SHARDING.md`。

---

## 快速开始

```bash
# 后端
cd backend
pip install -r requirements.txt
python run.py
# API 文档: http://localhost:8000/docs

# 前端
cd frontend
npm install
npm run dev
# 访问: http://localhost:5173
```

### 一键启动（推荐，Windows）

在项目根目录执行：

```powershell
.\start.ps1              # build 模式（默认，公网访问用这个）
.\start.ps1 -DevMode     # dev 模式（改前端代码时用）
```

| 模式 | 访问地址 | 前端资源加载量 |
| --- | --- | --- |
| **build**（默认） | `http://127.0.0.1:8000/g2/` | **1 个 JS，gzip 后约 104 KiB** |
| dev | `http://localhost:5173/g2/` | 28 个模块，约 2.6 MB |

**公网访问必须用 build 模式** —— dev 模式下浏览器要逐个拉 `.ts`/`.vue` 源码，
在实测约 0.6 Mbps 的公网链路上要 35 秒（build 只要 2 秒）。

build 模式下前端由**后端 8000 直接托管**，不需要再跑 5173，
所以 nginx 的上游也要指向 8000（`https://bqbq.mmc199.com/g2/`）。

其他参数：

| 参数 | 说明 |
| --- | --- |
| `-DevMode` | 前端跑 Vite dev server（5173），改代码热更新 |
| `-Build` | 强制重新构建前端 |
| `-BackendOnly` / `-FrontendOnly` | 只启动其中一个 |
| `-Force` | 端口被占用时自动结束占用进程 |

脚本还会：检查 `python`/`node`、前端依赖不存在时自动 `npm install`、
**检测源码是否比 build 产物新**（有则自动重建）。

详见 `FRONTEND_DEPLOY.md`。

> ⚠️ 该脚本含中文，已保存为 **UTF-8 with BOM**。
> 若用编辑器重存，请保留 BOM，否则 Windows PowerShell 5.1
> 会把中文读成乱码并报出莫名其妙的「语法错误」。

停止服务：直接关闭对应窗口即可。

---

## 当前项目结构

```text
bqbq_v2/
├── CLAUDE.md                 # AI 协作指南（本文件）
├── ARCHITECTURE.md           # 架构与流程文档
├── MIGRATION_STATUS.md       # 迁移状态与差异说明
├── SHARDING.md               # 43 万图片分片接入说明
├── R2_UPLOAD.md              # R2 上传与 CDN 配置说明
├── start.ps1                 # 一键启动（前后端各开一个窗口）
├── scripts/                  # 运维脚本（R2 上传等）
│
├── backend/                  # FastAPI 后端
│   ├── run.py               # 启动脚本
│   ├── requirements.txt     # Python 依赖
│   ├── meme.db              # SQLite 数据库（434,810 行，含 43 万图片索引）
│   ├── merge_into_v2.py     # 【新增】把旧库 43 万数据合并进 v2
│   ├── normalize_filenames.py  # 【新增】平铺 filename -> 分片路径
│   ├── backfill_metadata.py    # 【新增】回填 file_size / width / height
│   └── app/
│       ├── main.py          # 应用入口 / 静态挂载 / 缩略图 / 启动任务
│       ├── config.py        # 配置管理
│       ├── sharding.py      # 【新增】md5 分片路径规则（唯一真源）
│       ├── database.py      # 数据库连接 / 初始化 / tags_dict 重建
│       ├── models/
│       │   ├── image.py     # 图片 / 搜索模型
│       │   └── rule.py      # 规则树模型
│       └── routers/
│           ├── images.py    # 图片 CRUD / 上传 / MD5
│           ├── search.py    # 搜索 / 标签建议
│           ├── rules.py     # 规则树 / 层级 / 兼容旧接口
│           └── system.py    # 导入导出 / 版本 / 统计 / 兼容接口
│
└── frontend/                 # Vue 3 前端
    ├── package.json         # 依赖配置
    ├── README.md            # 前端说明
    └── src/
        ├── main.ts          # 入口
        ├── App.vue          # 根组件（当前直接挂 Gallery）
        ├── style.css        # 全局样式
        ├── types/index.ts   # TypeScript 类型定义
        ├── stores/
        │   └── useGlobalStore.ts
        ├── composables/
        │   ├── useApi.ts
        │   ├── useToast.ts
        │   └── useOptimisticUpdate.ts
        ├── views/
        │   └── Gallery.vue  # 当前主页面 / 业务主控层
        └── components/
            ├── TagInput.vue
            ├── MemeCard.vue
            ├── RuleTree.vue
            ├── RuleGroupNode.vue
            ├── FloatingButtons.vue
            └── ToastContainer.vue
```

> 说明：旧项目里曾有 `UploadModal`、`ImageEditModal` 等拆分概念；新项目目前把相关主流程收束到了 `Gallery.vue` 与 `MemeCard.vue` 中。

---

## 核心概念

### 1. 语义森林（关键词膨胀）

- 搜索“车辆”时，可以自动匹配子节点“汽车”“自行车”“卡车”等
- 核心依赖：`search_groups` + `search_keywords` + `search_hierarchy`
- 后端搜索可根据规则树自动做关键词膨胀

### 2. 乐观锁（CAS）

- 所有规则树写操作都需要 `client_id + base_version`
- 版本冲突时，服务端返回 `409`
- 前端 `useOptimisticUpdate.ts` 会尝试自动重放操作

### 3. 标签系统

- 空格分隔多个标签
- `-tag` 表示排除标签
- `tag1,tag2` 表示同义词组
- `-tag1,tag2` 表示交集排除逻辑输入形式

### 4. 双层兼容

这个项目同时有两层兼容目标：

1. **兼容旧项目的产品逻辑和数据结构**
2. **兼容新前端内部更现代的组件/类型拆分方式**

所以 AI 修改代码时，不要只看“当前文件很新”，还要意识到它可能在兼容旧项目行为。

---

## 修改代码时优先查看哪些文件

### 改搜索逻辑

优先查看：

- `backend/app/routers/search.py`
- `backend/app/models/image.py`
- `frontend/src/views/Gallery.vue`
- `frontend/src/composables/useApi.ts`
- `frontend/src/types/index.ts`

### 改规则树逻辑

优先查看：

- `backend/app/routers/rules.py`
- `backend/app/models/rule.py`
- `backend/app/database.py`
- `frontend/src/components/RuleTree.vue`
- `frontend/src/components/RuleGroupNode.vue`
- `frontend/src/composables/useApi.ts`
- `frontend/src/stores/useGlobalStore.ts`

### 改图片卡片 / 标签编辑

优先查看：

- `frontend/src/components/MemeCard.vue`
- `frontend/src/components/TagInput.vue`
- `frontend/src/views/Gallery.vue`
- `backend/app/routers/system.py`
- `backend/app/routers/images.py`

### 改导入导出

优先查看：

- `backend/app/routers/system.py`
- `backend/app/database.py`
- `frontend/src/composables/useApi.ts`
- `frontend/src/views/Gallery.vue`

---

## 文件修改指南

### 添加新 API

1. 在 `backend/app/routers/` 下对应文件添加路由
2. 在 `backend/app/models/` 添加 Pydantic 模型（如需要）
3. 在 `frontend/src/composables/useApi.ts` 添加调用函数
4. 在 `frontend/src/types/index.ts` 添加类型定义
5. 必要时更新 `ARCHITECTURE.md` / `MIGRATION_STATUS.md`

### 添加新组件

1. 在 `frontend/src/components/` 创建 `.vue` 文件
2. 使用 `<script setup lang="ts">`
3. 在需要的页面导入使用
4. 如果属于主流程组件，补文档中的组件关系图

### 修改数据库结构

1. 修改 `backend/app/database.py` 中的 `init_database()`
2. 检查导入导出逻辑是否也要改
3. 检查旧字段兼容逻辑是否会受影响
4. 开发阶段如需重建数据库，再考虑删除 `backend/meme.db`

---

## 代码规范

- **Python**：PEP 8，尽量带类型提示
- **TypeScript**：优先显式类型，不要随意 `any`
- **Vue**：组合式 API，逻辑清晰分块
- **命名**：组件 PascalCase，函数 camelCase
- **文档**：保留迁移说明、架构图和示意图
- **修改风格**：尽量“对齐旧行为 + 兼容现结构”，不要盲目重设计

---

## API 端点速查（按当前代码）

### 图片 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/images` | 图片列表 |
| GET | `/api/images/{id}` | 获取单张图片 |
| GET | `/api/images/check-md5/{md5}` | 检查 MD5 是否存在 |
| POST | `/api/images/check_md5` | 兼容式 MD5 检查 |
| POST | `/api/images` | Base64 上传图片 |
| POST | `/api/images/upload` | Multipart 上传图片 |
| PUT | `/api/images/{id}/tags` | 更新标签（CAS） |
| DELETE | `/api/images/{id}` | 删除图片 |
| POST | `/api/upload` | 主入口中的兼容上传接口 |

### 搜索 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/search` | 统一搜索入口（简单/高级 payload 自动识别） |
| GET | `/api/tags` | 获取所有标签 |
| GET | `/api/meta/tags` | 获取标签建议 |

### 规则树 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/rules` | 获取规则树（支持 ETag） |
| POST | `/api/rules/groups` | 创建规则组 |
| POST | `/api/rules/groups/{id}/keywords` | 添加关键词 |
| DELETE | `/api/rules/groups/{id}` | 删除规则组 |
| DELETE | `/api/rules/keywords/{id}` | 删除关键词 |
| POST | `/api/rules/keywords/{id}/toggle` | 启用/禁用关键词 |
| PUT | `/api/rules/groups/{id}` | 更新规则组 |
| POST | `/api/rules/groups/{id}/toggle` | 启用/禁用规则组 |
| POST | `/api/rules/groups/batch` | 批量操作组 |
| POST | `/api/rules/hierarchy/add` | 添加层级关系 |
| POST | `/api/rules/hierarchy/remove` | 删除层级关系 |
| POST | `/api/rules/hierarchy/batch_move` | 批量移动层级 |

### 规则树兼容旧接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/rules/group/add` | 旧式创建组 |
| POST | `/api/rules/group/update` | 旧式更新组 |
| POST | `/api/rules/group/toggle` | 旧式启禁组 |
| POST | `/api/rules/group/delete` | 旧式删除组 |
| POST | `/api/rules/group/batch` | 旧式批量组操作 |
| POST | `/api/rules/keyword/add` | 旧式添加关键词 |
| POST | `/api/rules/keyword/remove` | 旧式删除关键词 |

### 系统 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/version` | 获取规则版本 |
| POST | `/api/check_md5` | 系统兼容 MD5 检查 |
| POST | `/api/update_tags` | 兼容式标签更新 |
| GET | `/api/export` | 导出数据 |
| GET | `/api/export/all` | 全量导出 |
| POST | `/api/import` | 导入数据 |
| POST | `/api/import/all` | 全量导入 |
| GET | `/api/stats` | 获取统计信息 |

### 静态资源 / 特殊路径

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/images/{filename}` | 原图 |
| GET | `/thumbnails/{filename}` | 缩略图（含回退/生成逻辑） |
| GET | `/` | API 根路径 |

---

## 当前已确认的重要事实

1. 前端虽然安装了 `vue-router`，**当前没有真正启用路由**。
2. `App.vue` 当前直接渲染 `Gallery.vue`。
3. `/api/search` 已经兼容简单搜索和旧版高级搜索 payload。
4. 规则树读取结果仍偏向旧项目扁平结构，前端在 `useApi.ts` 内做树形组装。
5. `MemeCard.vue` 当前用于“点击外部关闭编辑”的是 `editorRef`，**卡片根节点已不再依赖额外模板 ref**。
6. `backend/app/main.py` 在启动时会扫描图片目录、重建 `tags_dict`，并启动后台线程周期刷新。
7. **图片目录是 md5 两段式分片结构**，`images.filename` 存分片相对路径。
   `backend/meme_images` 与 `backend/meme_images_thumbnail` 是指向
   `D:\bqbq_backend\` 下真实目录的**符号链接**。
8. 数据库共 **434,810 行**，其中 181 行有标签（多数图片尚未打标签）。
9. 启动扫描在「磁盘文件数 == 库记录数」时会走快速路径跳过逐文件校验；
   需要强制核对时设置环境变量 `BQBQ_FORCE_FOLDER_SCAN=1`。
10. 数据集里有 HEIC/HEIF 图片，`main.py` 与 `routers/images.py` 都已注册
    `pillow_heif.register_heif_opener()`，**不要删掉这段注册**，否则那些图会生成不了缩略图。

---

## 推荐验证方式

### 小型前端改动

- 先检查 `props / emits / ref / watch / 事件名`
- 再看用户本地 `npm run dev` 热更新是否生效
- 非必要不要整站 build

### 小型后端改动

- 检查 Pydantic 模型、路由参数、返回结构
- 看用户本地 `python run.py` 是否已自动热重载

### 文档改动

- 优先保留旧文档里高价值内容：
  - 架构图
  - ER 图
  - 流程图
  - 迁移摘要
  - 新手向解释

---

## 开发环境（当前仓库）

| 项目 | 信息 |
|------|------|
| 项目路径 | `C:\000soft\qqpy机器人-git\bqbq_v2` |
| 旧项目路径 | `C:\000soft\qqpy机器人-git\bqbq_backend-1\精确搜索SQLite端(旧)` |
| 后端端口 | `8000` |
| 前端端口 | `5173` |
| 数据库 | `backend/meme.db` |
| 原图目录 | `backend/meme_images` |
| 缩略图目录 | `backend/meme_images_thumbnail` |

---

## AI 协作建议

如果你是 AI 助手，请优先这样理解这个项目：

1. **先把它当成“旧项目语义 + 新技术栈外壳”**
2. **先找兼容逻辑，再找现代封装层**
3. **改完代码后别忘了改文档**
4. **不要把示意图和迁移说明当成“可删的废话”**

---

## 迁移参考

详细的迁移状态、保留行为、现存差异和阶段性总结，请参考：

- `MIGRATION_STATUS.md`
- `ARCHITECTURE.md`

