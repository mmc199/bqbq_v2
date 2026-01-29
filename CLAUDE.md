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

## API 端点速查

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/upload` | 上传图片（FormData） |
| GET | `/api/images` | 图片列表 |
| GET | `/api/images/check-md5/{md5}` | 检查 MD5 |
| PUT | `/api/images/{id}/tags` | 更新标签 |
| DELETE | `/api/images/{id}` | 删除图片 |
| POST | `/api/search` | 搜索图片 |
| GET | `/api/tags` | 获取所有标签 |
| GET | `/api/rules` | 获取规则树 |
| POST | `/api/rules/groups` | 创建规则组 |
| POST | `/api/rules/groups/{id}/keywords` | 添加关键词 |
| DELETE | `/api/rules/groups/{id}` | 删除规则组 |
| GET | `/api/export` | 导出数据 |
| POST | `/api/import` | 导入数据 |

## 开发代理配置

Vite 开发服务器已配置代理（`vite.config.ts`）：
- `/api/*` → `http://localhost:8000`
- `/images/*` → `http://localhost:8000`
