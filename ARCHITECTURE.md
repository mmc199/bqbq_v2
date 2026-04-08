# ARCHITECTURE.md

BQBQ v2 架构设计文档。

这份文档不是纯理论设计图，而是**基于当前仓库真实代码**整理出的“可读版地图”。

同时它也承担一个额外职责：

- 帮助新手理解这个项目
- 帮助 AI 理解“这个项目是从旧项目重构迁移而来”的背景

---

## 迁移背景

本项目来自旧仓库重构迁移：

- **旧项目**：`C:\000soft\qqpy机器人-git\bqbq_backend-1\精确搜索SQLite端(旧)`
- **新项目**：`C:\000soft\qqpy机器人-git\bqbq_v2`

### 旧项目 vs 新项目

| 维度 | 旧项目 | 新项目 |
|------|--------|--------|
| 后端 | Flask | FastAPI |
| 前端 | 原生 JavaScript + 单文件重逻辑 | Vue 3 + TypeScript + Pinia |
| 架构风格 | 重前端、LocalStorage 优先 | 组件化前端 + 更清晰的数据分层 |
| 核心逻辑 | 语义森林、CAS、FTS5 | 继续保留 |
| 迁移目标 | 功能可用 | 保留旧逻辑 + 提高可维护性 |

### 当前迁移策略

不是“完全推翻旧项目”，而是：

1. **保留旧项目最有价值的产品逻辑**
2. **把实现方式迁移到更清晰的前后端结构**
3. **尽量兼容旧接口字段与用户操作习惯**

所以你会在新项目里同时看到两类东西：

- 很新的 Vue / TS / FastAPI 结构
- 很明显的旧项目兼容痕迹

这不是混乱，而是迁移过程中的有意识设计。

---

## 系统整体架构

```text
┌──────────────────────────────────────────────────────────────────┐
│                          前端 (Vue 3)                            │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                    App.vue / Gallery.vue                  │   │
│  │                  （当前单页主控制器）                     │   │
│  └───────────────┬───────────────────────────────┬──────────┘   │
│                  │                               │              │
│        ┌─────────▼────────┐           ┌──────────▼────────┐     │
│        │  图片区 / MemeCard │           │  规则树 / RuleTree │     │
│        │  TagInput / FAB    │           │  RuleGroupNode    │     │
│        └─────────┬────────┘           └──────────┬────────┘     │
│                  │                               │              │
│        ┌─────────▼───────────────────────────────▼────────┐     │
│        │        Composables (useApi / useToast /         │     │
│        │              useOptimisticUpdate)               │     │
│        └──────────────────────┬──────────────────────────┘     │
│                               │                                │
│                    ┌──────────▼──────────┐                     │
│                    │ Pinia Store         │                     │
│                    │ useGlobalStore      │                     │
│                    └──────────┬──────────┘                     │
└───────────────────────────────┼────────────────────────────────┘
                                │ HTTP
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                        后端 (FastAPI)                            │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐         │
│  │ images   │ │ search   │ │ rules    │ │ system       │         │
│  │ router   │ │ router   │ │ router   │ │ router       │         │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘         │
│       │            │            │              │                 │
│       └────────────┴────────────┴──────────────┘                 │
│                           │                                      │
│               ┌───────────▼───────────┐                          │
│               │ database.py           │                          │
│               │ SQLite + FTS5         │                          │
│               │ tags_dict / version   │                          │
│               └───────────┬───────────┘                          │
│                           │                                      │
│         ┌─────────────────▼──────────────────┐                   │
│         │  meme.db / images / thumbnails     │                   │
│         └────────────────────────────────────┘                   │
└──────────────────────────────────────────────────────────────────┘
```

### 当前实际情况说明

- 前端虽然安装了 `vue-router`，**当前没有启用路由**。
- `Gallery.vue` 实际上承担了旧项目里很多“主控制器”的职责。
- 规则树与搜索接口仍保留较强的旧项目兼容特征。

---

## 目录结构与职责

```text
bqbq_v2/
├── CLAUDE.md
├── ARCHITECTURE.md
├── MIGRATION_STATUS.md
│
├── backend/
│   ├── run.py
│   ├── requirements.txt
│   ├── meme.db
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── models/
│       │   ├── image.py
│       │   └── rule.py
│       └── routers/
│           ├── images.py
│           ├── search.py
│           ├── rules.py
│           └── system.py
│
└── frontend/
    ├── package.json
    ├── README.md
    └── src/
        ├── main.ts
        ├── App.vue
        ├── style.css
        ├── types/index.ts
        ├── stores/useGlobalStore.ts
        ├── composables/
        │   ├── useApi.ts
        │   ├── useToast.ts
        │   └── useOptimisticUpdate.ts
        ├── views/Gallery.vue
        └── components/
            ├── TagInput.vue
            ├── MemeCard.vue
            ├── RuleTree.vue
            ├── RuleGroupNode.vue
            ├── FloatingButtons.vue
            └── ToastContainer.vue
```

---

## 后端架构

### 1. 启动入口

`backend/run.py` 用于本地开发启动 Uvicorn。

`backend/app/main.py` 是后端真正入口，主要负责：

- 创建 FastAPI 应用
- 配置 CORS
- 注册路由
- 挂载 `/images`
- 实现 `/thumbnails/{filename}`
- 启动时初始化数据库
- 启动时扫描图片目录并补录数据库
- 重建 `tags_dict`
- 启动后台线程定期更新 `tags_dict`

### 2. 启动流程图

```text
python run.py
   ↓
Uvicorn 启动 app.main:app
   ↓
FastAPI startup event
   ↓
init_database()
   ↓
scan_and_import_folder()
   ↓
rebuild_tags_dict()
   ↓
start_tags_dict_updater()
   ↓
服务可用
```

### 3. 路由分层

| 路由文件 | 主要职责 |
|------|------|
| `routers/images.py` | 图片列表、单图、上传、MD5、删除、更新标签 |
| `routers/search.py` | 搜索、标签聚合、标签建议 |
| `routers/rules.py` | 规则树读取、修改、层级移动、旧接口兼容 |
| `routers/system.py` | 导入导出、版本、统计、兼容式标签更新 |

### 4. 特殊静态路由

#### `/images/{filename}`

- 直接提供原图访问

#### `/thumbnails/{filename}`

这个路由很重要，因为它不是单纯静态目录映射，而是带有兼容和回退逻辑：

```text
请求 /thumbnails/xxx.jpg
   ↓
优先找缩略图目录中的同名文件
   ↓
若不存在，尝试回退到原图目录 / trash_bin 等路径
   ↓
若找到原图，则动态生成缩略图
   ↓
返回缩略图文件
```

这部分是对旧项目实际图片组织方式的一种适配。

---

## 数据库设计

### ER 图（更新版）

```text
┌──────────────┐       ┌──────────────────┐       ┌─────────────────┐
│    images    │       │  search_groups   │       │ search_keywords │
├──────────────┤       ├──────────────────┤       ├─────────────────┤
│ id (PK)      │       │ id (PK)          │◄──────│ id (PK)         │
│ filename     │       │ name             │       │ keyword         │
│ md5 (UNIQUE) │       │ parent_id*       │       │ group_id (FK)   │
│ tags         │       │ enabled          │       │ enabled         │
│ file_size    │       │ created_at       │       │ created_at      │
│ width        │       └──────────────────┘       └─────────────────┘
│ height       │                 │
│ created_at   │                 │
└──────┬───────┘                 │
       │                         │
       │               ┌─────────▼──────────┐
       │               │ search_hierarchy   │
       │               ├────────────────────┤
       │               │ ancestor_id        │
       │               │ descendant_id      │
       │               │ depth              │
       │               └─────────┬──────────┘
       │                         │
┌──────▼───────┐      ┌──────────▼──────────┐      ┌─────────────────┐
│  images_fts  │      │search_hierarchy_edges│      │ search_version_ │
├──────────────┤      ├──────────────────────┤      │      log        │
│ rowid        │      │ parent_id            │      ├─────────────────┤
│ tags         │      │ child_id             │      │ version_id      │
└──────────────┘      └──────────────────────┘      │ modifier_id     │
                                                    │ updated_at      │
┌──────────────┐      ┌──────────────────────┐      │ operation       │
│  tags_dict   │      │    system_meta       │      └─────────────────┘
├──────────────┤      ├──────────────────────┤
│ tag          │      │ key                  │
│ count        │      │ value                │
└──────────────┘      └──────────────────────┘
```

> 说明：`search_groups.parent_id` 仍存在，但当前更核心的层级维护依赖 `search_hierarchy`（闭包表）和 `search_hierarchy_edges`（边表）。

### 表说明

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| `images` | 图片元数据 | `md5` 唯一标识，`tags` 为空格分隔 |
| `images_fts` | FTS5 全文索引 | 与 `images.tags` 同步 |
| `search_groups` | 规则组 | `enabled`、显示名称 |
| `search_keywords` | 关键词 | 归属某个组，可启用/禁用 |
| `search_hierarchy` | 闭包表 | 快速查询祖先/后代 |
| `search_hierarchy_edges` | 边表 | 记录真实父子关系，便于恢复/导入导出 |
| `tags_dict` | 标签词典 | 标签计数缓存，用于建议/补全 |
| `system_meta` | 系统配置 | `rules_version` 等 |
| `search_version_log` | 版本日志 | CAS 写操作记录 |

### 触发器与索引

#### FTS 触发器

后端会为 `images` 建立 3 个触发器：

- 插入时更新 FTS
- 删除时更新 FTS
- 更新时重写 FTS

#### 常用索引

- `idx_keywords_group`
- `idx_hierarchy_ancestor`
- `idx_hierarchy_descendant`
- `idx_hierarchy_edges_child`
- `idx_images_created`
- `idx_images_size`
- `idx_images_resolution`

---

## 核心算法与流程

### 1. 关键词膨胀（Keyword Expansion）

```text
输入: 搜索词 "车辆"
  ↓
查找包含“车辆”关键词的规则组
  ↓
通过 search_hierarchy 找到所有子孙组
  ↓
收集这些组下的全部关键词
  ↓
输出: ["车辆", "汽车", "自行车", "卡车", ...]
```

示意 SQL：

```sql
SELECT DISTINCT sk.keyword
FROM search_keywords sk
JOIN search_hierarchy sh ON sk.group_id = sh.descendant_id
WHERE sh.ancestor_id = ?
```

### 2. 搜索双模式兼容

当前后端 `POST /api/search` 不是单一协议，而是兼容两类输入：

#### 简单搜索 payload

```json
{
  "include_tags": ["猫"],
  "exclude_tags": ["狗"],
  "page": 1,
  "page_size": 20,
  "expand": true
}
```

#### 高级搜索 payload（旧风格）

```json
{
  "keywords": [["猫", "小猫"]],
  "excludes": [["狗"]],
  "excludes_and": [],
  "offset": 0,
  "limit": 40,
  "sort_by": "date_desc"
}
```

流程示意：

```text
前端发起 /api/search
   ↓
后端检查 payload 结构
   ↓
简单模式？──────────是────────→ SearchRequest
   │
   否
   ↓
AdvancedSearchRequest
   ↓
统一生成 SQL 条件
   ↓
SQLite / FTS5 查询
   ↓
返回 { total, results }
```

### 3. 乐观锁（CAS）流程

```text
客户端                              服务端
   │                                  │
   │ 1. 读取规则树 + version_id       │
   │◄─────────────────────────────────│
   │                                  │
   │ 2. 携带 base_version 发起修改    │
   │─────────────────────────────────►│
   │                                  │
   │          3. 检查当前版本         │
   │                                  │
   │   不一致 → 409 + latest_data     │
   │◄─────────────────────────────────│
   │                                  │
   │   一致 → 执行写入 + version++    │
   │◄─────────────────────────────────│
   │ 4. 返回 new_version              │
```

前端的 `useOptimisticUpdate.ts` 负责：

- 先做本地乐观更新
- 如果收到 `409`：
  - 更新本地最新版本
  - 必要时拉最新数据
  - 最多重试 3 次

### 4. `tags_dict` 更新机制

```text
应用启动
   ↓
rebuild_tags_dict()
   ↓
后台线程每隔 N 秒重建一次
   ↓
标签建议 / 标签列表接口读取该缓存表
```

这个设计能减少前端每次建议查询时的实时聚合开销。

### 5. 缩略图生成流程

```text
上传图片 / 首次访问缩略图
   ↓
Pillow 打开原图
   ↓
若是动图，随机抽取一帧
   ↓
缩放到最大 600x600
   ↓
转为 JPEG 写入缩略图目录
   ↓
供前端 `/thumbnails/...` 使用
```

---

## 前端组件关系

```text
App.vue
└── Gallery.vue (主页面 / 主控制器)
    ├── TagInput.vue (顶部搜索栏)
    ├── MemeCard.vue[] (图片网格)
    ├── FloatingButtons.vue (右下角操作区)
    ├── RuleTree.vue (规则树面板)
    │   └── RuleGroupNode.vue[] (递归节点)
    └── ToastContainer.vue (通知)
```

### 与旧项目概念的对应

| 旧项目概念 | 新项目承载位置 |
|------|------|
| 全局主控制器 `MemeApp` | `Gallery.vue` + `useApi.ts` + `useGlobalStore.ts` |
| 搜索输入组件 | `TagInput.vue` |
| 图片卡片 + 标签编辑 | `MemeCard.vue` |
| 规则树面板 | `RuleTree.vue` |
| 全局状态 | `useGlobalStore.ts` |

---

## 前端状态管理

### Pinia Store: `useGlobalStore`

核心状态包括：

```typescript
{
  clientId: string,
  rulesVersion: number,
  rulesTree: RulesTree | null,
  isLoading: boolean,
  preferHQ: boolean,
  isExpansionEnabled: boolean,
  fabCollapsed: boolean,
  fabMiniPosition: number | null,
  expandedGroupIds: number[],
  tagCache: string[]
}
```

### 本地存储键

| Key | 存储位置 | 用途 |
|-----|----------|------|
| `bqbq_client_id` | LocalStorage | 客户端唯一 ID |
| `bqbq_rules_version` | LocalStorage | 当前规则版本 |
| `bqbq_rules_cache` | LocalStorage | 规则树缓存 |
| `bqbq_tag_cache` | LocalStorage | 标签建议缓存 |
| `bqbq_tag_timestamp` | LocalStorage | 标签缓存时间戳 |
| `bqbq_prefer_hq` | LocalStorage | 是否偏好原图 |
| `bqbq_expansion_enabled` | SessionStorage | 是否开启关键词膨胀 |
| `bqbq_fab_collapsed` | SessionStorage | FAB 是否折叠 |
| `bqbq_fab_mini_position` | SessionStorage | FAB 迷你位置 |
| `bqbq_tree_expanded` | SessionStorage | 规则树展开状态 |

---

## 关键数据流

### 1. 页面初始化

```text
打开页面
   ↓
初始化 Pinia store
   ↓
从本地缓存读取 clientId / rulesVersion / rulesTree / tagCache
   ↓
Gallery.vue onMounted
   ↓
请求规则树 / 标签建议 / 首屏图片
   ↓
渲染页面
```

### 2. 搜索图片

```text
用户输入标签胶囊
   ↓
Gallery.vue 规范化搜索条件
   ↓
若启用扩展：结合规则树做关键词膨胀
   ↓
调用 useApi.ts -> /api/search
   ↓
后端查询 SQLite / FTS5
   ↓
返回 { total, results }
   ↓
更新图片网格与分页状态
```

### 3. 编辑规则树

```text
RuleTree 触发增删改 / 拖拽
   ↓
useApi.ts 发起带 base_version 的请求
   ↓
后端进行 CAS 检查
   ↓
成功 → 返回 new_version
冲突 → 返回 409 + latest_data
   ↓
前端更新缓存 / 自动重试 / 提示用户
```

### 4. 编辑图片标签

```text
点击 MemeCard 标签区域
   ↓
打开内联 TagInput 编辑器
   ↓
点空白处 / Enter 完成编辑
   ↓
Gallery.vue 收到 update-tags 事件
   ↓
前端做乐观更新
   ↓
调用后端更新标签
   ↓
成功保留 / 失败回滚
```

### 5. 上传图片

```text
选择文件
   ↓
前端用 SparkMD5 计算 MD5
   ↓
请求后端检查是否重复
   ↓
若不存在则上传
   ↓
后端保存原图 + 生成缩略图 + 写数据库
   ↓
前端刷新列表
```

---

## 性能优化

1. **图片懒加载**：卡片根据索引决定 `eager / lazy`
2. **FTS5**：全文搜索索引减少文本匹配成本
3. **闭包表**：规则树祖先/后代查询更高效
4. **ETag / 版本缓存**：规则树可走缓存恢复逻辑
5. **标签缓存**：`tags_dict` + 前端本地缓存双层加速
6. **MD5 去重**：上传前预检查减少重复写入

---

## 安全与稳定性考虑

1. **文件类型约束**：后端仅允许图片扩展名
2. **MD5 校验**：Base64 上传会重新核对摘要
3. **CORS 配置**：仅允许本地开发常用来源
4. **SQL 参数化**：动态查询参数采用绑定方式
5. **CAS 并发控制**：避免多人同时修改规则树时互相覆盖
6. **冲突重试限制**：前端最多重试 3 次，避免死循环

---

## 已知差异与维护提醒

### 相比旧项目已经变化的地方

1. 前端从“单文件重逻辑”变成了组件化结构
2. 主页面逻辑集中在 `Gallery.vue`，但不再是原生 JS 控制器
3. 当前搜索接口统一收口到 `/api/search`
4. 规则树层级同时依赖闭包表与边表

### 仍保留的旧项目痕迹

1. 兼容旧字段名和旧返回结构
2. 兼容旧版规则树接口别名
3. 高级搜索 payload 保留旧式二维/三维数组格式
4. 文案、交互、排序语义仍尽量向旧项目对齐

### 维护时最容易踩坑的点

1. 只改前端类型，不改后端模型
2. 只改新接口，不看旧兼容接口
3. 只看 Vue 组件，不看旧项目行为对齐需求
4. 改文档时把流程图和迁移说明删掉

---

## 推荐阅读顺序（新手 / AI）

如果你第一次接触这个项目，建议按下面顺序读：

1. `CLAUDE.md` - 先建立项目背景和协作约束
2. 本文件 `ARCHITECTURE.md` - 再理解整体结构
3. `MIGRATION_STATUS.md` - 了解从旧项目迁来的内容和差异
4. `frontend/src/views/Gallery.vue` - 看当前前端主控流程
5. `backend/app/main.py` 与 `backend/app/routers/search.py` - 看后端入口和搜索链路

