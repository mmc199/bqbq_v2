# CLAUDE.md

本文件为 Claude Code 在本仓库中工作时提供指导。

## ⚠️ 最重要：代码编辑原则

**必须严格遵守以下原则，防止文件损坏或内容丢失：**

1. **分段编辑** - 每次只修改一小部分代码，不要一次性重写整个文件
2. **验证完整性** - 修改后读取文件确认内容正确
3. **避免大量写入** - 超过 200-300 行的修改应该分多次进行
4. **先读后写** - 写入文件前必须先读取，了解现有内容
5. **控制上下文** - 使用 Task 工具委托子任务，避免一次性读取大量文件，防止上下文过长导致遗忘
6. **乱码检查** - 修改后确认中文显示正常，必要时以 UTF-8 读取/写入

## 语言偏好

本项目使用**中文**进行问答和代码注释。请始终使用中文回复。

## 项目概述

BQBQ v2（表情标签）是一个基于语义森林的图片标签管理系统，用于组织和搜索表情包/梗图。

**技术栈**：
- 前端：Vue 3 + TypeScript + Vite + Tailwind CSS + Pinia
- 后端：FastAPI + Pydantic + SQLite3 + FTS5

**相关文档**：
- [ARCHITECTURE.md](ARCHITECTURE.md) - 架构设计文档
- [MIGRATION_STATUS.md](MIGRATION_STATUS.md) - 迁移状态与视觉样式参考

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
├── MIGRATION_STATUS.md       # 迁移状态文档
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
        ├── style.css        # 全局样式
        ├── types/index.ts   # TypeScript 类型定义
        ├── stores/          # Pinia 状态管理
        │   └── useGlobalStore.ts
        ├── composables/     # 组合式函数
        │   ├── useApi.ts    # API 封装
        │   ├── useToast.ts  # Toast 通知
        │   └── useOptimisticUpdate.ts  # 乐观更新
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
- 后端 `expand` 参数控制膨胀开关

### 2. 乐观锁（CAS）
- 所有修改操作需要 `client_id` + `base_version`
- 版本冲突时返回 409 错误
- 前端 `useOptimisticUpdate.ts` 自动重试机制

### 3. 标签系统
- 空格分隔多个标签
- `-tag` 表示排除标签
- `tag1,tag2` 表示同义词组
- `-tag1,tag2` 表示交集排除

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

## API 端点速查

### 图片 API
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/images` | 上传图片 |
| GET | `/api/images` | 图片列表 |
| GET | `/api/images/{id}` | 获取单张图片 |
| GET | `/api/images/check-md5/{md5}` | 检查 MD5 是否存在 |
| PUT | `/api/images/{id}/tags` | 更新标签（CAS） |
| DELETE | `/api/images/{id}` | 删除图片 |

### 搜索 API
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/search` | 基础搜索 |
| POST | `/api/search/advanced` | 高级搜索（二维/三维数组） |
| GET | `/api/meta/tags` | 获取标签建议（按使用次数排序） |

### 规则树 API
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/rules` | 获取规则树（支持 ETag） |
| POST | `/api/rules/groups` | 创建规则组 |
| PUT | `/api/rules/groups/{id}` | 更新规则组 |
| DELETE | `/api/rules/groups/{id}` | 删除规则组 |
| POST | `/api/rules/groups/{id}/keywords` | 添加关键词 |
| DELETE | `/api/rules/keywords/{id}` | 删除关键词 |
| PUT | `/api/rules/keywords/{id}` | 更新关键词（启用/禁用） |

### 系统 API
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/export` | 导出数据 |
| POST | `/api/import` | 导入数据 |
| GET | `/api/version` | 获取规则版本 |
| GET | `/api/stats` | 获取系统统计 |

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

## AI 协作权限

本项目已授权 Claude 执行以下操作，无需额外确认：
- 读写项目内所有文件
- 执行 bash 命令（npm、python、git 等）
- 创建、修改、删除文件
- 运行开发服务器和测试

## 迁移参考

详细的迁移状态、视觉样式代码对照、API 端点对照表请参考 [MIGRATION_STATUS.md](MIGRATION_STATUS.md)。
