# CLAUDE.md

本文件为 Claude Code 在本仓库中工作时提供指导。

## 语言偏好

本项目使用**中文**进行问答和代码注释。请始终使用中文回复。

## 项目概述

BQBQ v2（表情标签）是一个基于语义森林的图片标签管理系统，用于组织和搜索表情包/梗图。

**技术栈**：
- 前端：Vue 3 + TypeScript + Vite + Tailwind CSS + Pinia
- 后端：FastAPI + Pydantic + SQLite3 + FTS5

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

## 项目结构

```
bqbq_v2/
├── CLAUDE.md                 # AI 协作指南（本文件）
├── ARCHITECTURE.md           # 架构设计文档
├── PROGRESS.md               # 开发进度追踪
│
├── backend/                  # FastAPI 后端
│   ├── run.py               # 启动脚本
│   ├── requirements.txt     # Python 依赖
│   └── app/
│       ├── main.py          # 应用入口 + 上传 API
│       ├── config.py        # 配置管理
│       ├── database.py      # 数据库连接 + 表结构
│       ├── models/          # Pydantic 模型
│       │   ├── image.py     # 图片模型
│       │   └── rule.py      # 规则树模型
│       └── routers/         # API 路由
│           ├── images.py    # 图片 CRUD + MD5 检查
│           ├── rules.py     # 规则树管理
│           ├── search.py    # 搜索功能
│           └── system.py    # 导入导出
│
└── frontend/                 # Vue 3 前端
    ├── vite.config.ts       # Vite 配置（含代理）
    ├── package.json         # 依赖配置
    └── src/
        ├── main.ts          # 入口
        ├── App.vue          # 根组件
        ├── types/index.ts   # TypeScript 类型定义
        ├── stores/          # Pinia 状态管理
        │   └── useGlobalStore.ts
        ├── composables/     # 组合式函数
        │   ├── useApi.ts    # API 封装
        │   └── useToast.ts  # Toast 通知
        ├── views/           # 页面视图
        │   └── Gallery.vue  # 主页面
        └── components/      # 可复用组件
            ├── TagInput.vue         # 标签输入
            ├── MemeCard.vue         # 图片卡片
            ├── RuleTree.vue         # 规则树面板
            ├── RuleGroupNode.vue    # 规则组节点
            ├── UploadModal.vue      # 上传模态框
            ├── ImageEditModal.vue   # 编辑模态框
            ├── FloatingButtons.vue  # FAB 按钮组
            └── ToastContainer.vue   # Toast 容器
```

## 核心概念

### 1. 语义森林（关键词膨胀）
- 搜索"车辆"自动匹配子节点"汽车"、"自行车"
- 通过 `search_hierarchy` 闭包表实现快速查询
- 可通过 FAB 按钮开关膨胀功能

### 2. 乐观锁（CAS）
- 所有修改操作需要 `client_id` + `base_version`
- 版本冲突时返回 409 错误
- 前端自动重试机制

### 3. 标签系统
- 空格分隔多个标签
- `-tag` 表示排除标签
- `tag1,tag2` 表示同义词组

## 文件修改指南

### 添加新 API
1. 在 `backend/app/routers/` 下对应文件添加路由
2. 在 `backend/app/models/` 添加 Pydantic 模型（如需要）
3. 在 `frontend/src/composables/useApi.ts` 添加调用函数
4. 在 `frontend/src/types/index.ts` 添加类型定义

### 添加新组件
1. 在 `frontend/src/components/` 创建 `.vue` 文件
2. 使用 `<script setup lang="ts">` 组合式 API
3. 在需要的地方导入使用

### 修改数据库结构
1. 修改 `backend/app/database.py` 中的 `init_database()`
2. 删除 `meme.db` 重新初始化（开发阶段）

## 代码规范

- **文件大小**：每个文件控制在 300 行以内
- **Python**：PEP 8，使用类型提示
- **TypeScript**：严格模式，完整类型定义
- **Vue**：组合式 API，单文件组件
- **命名**：组件 PascalCase，函数 camelCase

## 视觉样式规范

### 全局样式文件
所有自定义样式定义在 `frontend/src/style.css`，使用 Tailwind CSS 的 `@apply` 指令。

### 核心 CSS 类

| 类名 | 用途 | 关键样式 |
|------|------|----------|
| `.fab-btn` | FAB 悬浮按钮 | `w-14 h-14 rounded-2xl shadow-lg hover:scale-105` |
| `.fab-satellite` | FAB 卫星按钮 | `w-7 h-7 rounded-full` 绝对定位 |
| `.fab-mini-btn` | 折叠后迷你按钮 | `w-8 h-8 rounded-lg` |
| `.fab-mini-strip` | 折叠按钮条 | 固定右侧，半圆背景 |
| `.fab-slash` | 禁用斜杠图标 | 红色斜线覆盖 |
| `.meme-card` | 图片卡片容器 | `aspect-square rounded-xl` |
| `.is-trash` | 回收站图片 | 红色虚线边框 + 灰度滤镜 + "已删除"水印 |
| `.overlay-tag` | 图片覆盖层标签 | 半透明白色背景 + 文字阴影 |
| `.image-info` | 图片信息文字 | 文字阴影增强可读性 |
| `.tag-capsule` | 标签胶囊 | `popIn` 弹出动画 |
| `.top-toolbar` | 顶部工具栏 | 渐变背景遮罩 |
| `.load-failed` | 加载失败提示 | 斜线背景图案 |
| `.custom-scrollbar` | 自定义滚动条 | 细滚动条 + 圆角 |

### 动画效果

```css
/* 标签弹出动画 */
@keyframes popIn {
  0% { transform: scale(0.8); opacity: 0; }
  50% { transform: scale(1.05); }
  100% { transform: scale(1); opacity: 1; }
}

/* Toast 滑入动画 */
@keyframes slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
```

### 布局规范

| 元素 | 位置/尺寸 |
|------|-----------|
| 搜索栏 | `sticky top-0 min-h-16 px-4 shadow-sm` |
| 搜索输入框 | `bg-slate-100 rounded-xl min-h-[50px] max-h-[120px]` |
| FAB 按钮组 | `fixed right-4 top-[7rem]` 2x2 网格 |
| 规则树面板 | `fixed left-0 w-80 h-full`（左侧滑出） |
| Toast 通知 | `fixed bottom-8 right-8` |
| 图片网格 | `grid-cols-2 → sm:3 → md:4 → lg:5 → xl:6 → 2xl:8` |

### 配色方案

| 用途 | 颜色 |
|------|------|
| 主操作（搜索） | `bg-blue-600` |
| 上传 | `bg-emerald-500` |
| 删除/回收站 | `bg-red-50 text-red-600` |
| 规则树 | `bg-purple-100 text-purple-700` |
| 导出 | `bg-amber-50 text-amber-600` |
| 导入 | `bg-indigo-50 text-indigo-600` |
| 膨胀开启 | `bg-green-100 text-green-700` |
| 膨胀关闭 | `bg-white text-slate-400` |

### 标签胶囊配色

| 类型 | 样式 |
|------|------|
| 普通标签（蓝色主题） | `bg-blue-100 text-blue-600 border-blue-200` |
| 普通标签（紫色主题） | `bg-purple-100 text-purple-700 border-purple-200` |
| 排除标签 | `bg-red-100 text-red-600 border-red-200` |
| 同义词组 | `bg-green-100 text-green-600 border-green-200` |
| 排除+同义词 | `bg-orange-100 text-orange-700 border-orange-300` |

## API 端点速查

### 图片 API
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/images` | 上传图片（JSON: filename, md5, tags, base64_data） |
| GET | `/api/images` | 图片列表 |
| GET | `/api/images/{id}` | 获取单张图片 |
| GET | `/api/images/check-md5/{md5}` | 检查 MD5 是否存在 |
| PUT | `/api/images/{id}/tags` | 更新标签（CAS） |
| DELETE | `/api/images/{id}` | 删除图片 |

### 搜索 API
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/search` | 搜索图片 |
| GET | `/api/tags` | 获取所有标签 |

**搜索参数**：
```json
{
  "include_tags": ["标签1", "标签2"],
  "exclude_tags": ["排除标签"],
  "page": 1,
  "page_size": 20,
  "min_tags": 1,        // 最小标签数量
  "max_tags": 10,       // 最大标签数量
  "sort_by": "time_desc", // 排序: time_desc/asc, tags_desc/asc, size_desc/asc
  "extensions": ["png", "gif"]  // 文件扩展名过滤
}
```

### 规则树 API
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/rules` | 获取规则树（支持 ETag） |
| POST | `/api/rules/groups` | 创建规则组 |
| PUT | `/api/rules/groups/{id}` | 更新规则组（重命名、移动、启用/禁用） |
| DELETE | `/api/rules/groups/{id}` | 删除规则组 |
| POST | `/api/rules/groups/{id}/toggle` | 切换规则组启用状态 |
| POST | `/api/rules/groups/{id}/keywords` | 添加关键词 |
| DELETE | `/api/rules/keywords/{id}` | 删除关键词 |
| POST | `/api/rules/groups/batch` | 批量操作规则组（delete/enable/disable/move） |

### 层级关系 API
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/rules/hierarchy/add` | 添加层级关系（移动到父节点下） |
| POST | `/api/rules/hierarchy/remove` | 删除层级关系（移动到根级别） |
| POST | `/api/rules/hierarchy/batch_move` | 批量移动层级 |

### 系统 API
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/export` | 导出数据（JSON） |
| POST | `/api/import` | 导入数据（FormData: file） |
| GET | `/api/version` | 获取当前规则版本 |
| GET | `/api/stats` | 获取系统统计信息 |

## 开发代理配置

Vite 开发服务器已配置代理（`vite.config.ts`）：
- `/api/*` → `http://localhost:8000`
- `/images/*` → `http://localhost:8000`

## 开发环境

| 项目 | 版本/信息 |
|------|-----------|
| 操作系统 | Windows 10 (MINGW64) |
| Python | 3.13.11 |
| Node.js | 24.12.0 |
| npm | 11.6.2 |
| 项目路径 | `C:\000soft\qqpy机器人-git\bqbq_v2` |
| 后端端口 | 8000 |
| 前端端口 | 5173 |
| 数据库 | SQLite3 (meme.db) |
| Shell | Git Bash (MINGW64) |

## AI 协作权限

本项目已授权 Claude 执行以下操作，无需额外确认：
- 读写项目内所有文件
- 执行 bash 命令（npm、python、git 等）
- 创建、修改、删除文件
- 运行开发服务器和测试

## 前端组件详解

### Gallery.vue（主页面）
- **搜索栏**：`sticky top-0`，包含 TagInput 组件
- **图片网格**：响应式列数，使用 `gap-4`
- **无限滚动**：监听滚动事件，自动加载更多
- **到底提示**：`py-16 text-slate-300 font-bold`

### MemeCard.vue（图片卡片）
- **容器**：`aspect-square rounded-xl shadow-sm hover:shadow-lg`
- **回收站样式**：`.is-trash` 类，红色虚线边框 + 灰度 + 水印
- **顶部工具栏**：`hidden group-hover:flex`（悬停显示），包含下载/复制/删除按钮
- **底部信息栏**：渐变背景 `rgba(0,0,0,0.85)`，显示文件信息和标签
- **信息文字**：`text-[12px] font-mono opacity-80`
- **标签**：`.overlay-tag` 样式，点击触发搜索

### FloatingButtons.vue（FAB 按钮组）
- **布局**：`fixed right-4 top-[7rem]` 2x5 网格
- **按钮顺序**（一比一复刻旧项目）：
  1. 导出（琥珀色） | 导入（靛蓝色）
  2. HQ模式（青色） | 排序（橙色）
  3. 回收站（灰色/红色） | 上传（绿色）
  4. 搜索（蓝色+卫星） | 标签数量筛选（青色）
  5. 临时标签（紫色） | 规则树（绿色）
- **卫星按钮**：搜索按钮周围的折叠（左上）、清空（右上）、膨胀开关（右下）
- **折叠模式**：迷你按钮条，半圆背景

### TagInput.vue（标签输入）
- **容器**：`bg-slate-100 rounded-xl min-h-[50px] max-h-[120px]`
- **聚焦样式**：`bg-white border-blue-300 ring-2 ring-blue-100`
- **标签胶囊**：`px-3 py-1 rounded-full font-bold tag-capsule`（带 popIn 动画）
- **交互**：空格/回车添加，Backspace 编辑，点击删除

### RuleTree.vue（规则树面板）
- **侧边栏**：`fixed left-0 w-72 h-full bg-white shadow-xl`（左侧滑出）
- **切换条**：左侧边缘细长条，`w-5 hover:w-6`，点击打开面板
- **动画**：`translateX(-100%)` 滑入滑出
- **节点**：递归渲染 RuleGroupNode

### ToastContainer.vue（通知容器）
- **位置**：`fixed bottom-8 right-8`
- **样式**：`rounded-xl shadow-2xl min-w-[280px]`
- **动画**：`translateX(100%)` 滑入滑出

## 数据库表结构

### images 表
```sql
CREATE TABLE images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT UNIQUE NOT NULL,
    md5 TEXT UNIQUE NOT NULL,
    tags TEXT DEFAULT '',
    file_size INTEGER,
    width INTEGER,
    height INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1
);
```

### rule_groups 表
```sql
CREATE TABLE rule_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER REFERENCES rule_groups(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1
);
```

### search_hierarchy 表（闭包表）
```sql
CREATE TABLE search_hierarchy (
    ancestor_id INTEGER NOT NULL,
    descendant_id INTEGER NOT NULL,
    depth INTEGER NOT NULL,
    PRIMARY KEY (ancestor_id, descendant_id)
);
```

### images_fts 表（全文搜索）
```sql
CREATE VIRTUAL TABLE images_fts USING fts5(
    tags,
    content='images',
    content_rowid='id'
);
```
