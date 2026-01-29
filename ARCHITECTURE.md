# ARCHITECTURE.md

BQBQ v2 架构设计文档

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (Vue 3)                          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │ Gallery │  │ Upload  │  │  Edit   │  │    RuleTree     │ │
│  │  View   │  │  Modal  │  │  Modal  │  │     Panel       │ │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────────┬────────┘ │
│       │            │            │                │          │
│  ┌────┴────────────┴────────────┴────────────────┴────┐     │
│  │              Composables (useApi, useToast)         │     │
│  └────────────────────────┬────────────────────────────┘     │
│                           │                                  │
│  ┌────────────────────────┴────────────────────────────┐     │
│  │              Pinia Store (GlobalState)              │     │
│  └─────────────────────────────────────────────────────┘     │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP (Vite Proxy)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      后端 (FastAPI)                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    API Routers                       │    │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────┐    │    │
│  │  │ images │ │ search │ │ rules  │ │   system   │    │    │
│  │  └───┬────┘ └───┬────┘ └───┬────┘ └─────┬──────┘    │    │
│  └──────┼──────────┼──────────┼────────────┼───────────┘    │
│         │          │          │            │                │
│  ┌──────┴──────────┴──────────┴────────────┴───────────┐    │
│  │                   Database Layer                     │    │
│  │  ┌─────────────────────────────────────────────┐    │    │
│  │  │              SQLite3 + FTS5                  │    │    │
│  │  └─────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 数据库设计

### ER 图

```
┌──────────────┐       ┌──────────────────┐       ┌─────────────────┐
│    images    │       │  search_groups   │       │ search_keywords │
├──────────────┤       ├──────────────────┤       ├─────────────────┤
│ id (PK)      │       │ id (PK)          │◄──────│ id (PK)         │
│ filename     │       │ name             │       │ keyword         │
│ md5 (UNIQUE) │       │ parent_id (FK)───┼───┐   │ group_id (FK)   │
│ tags         │       │ created_at       │   │   │ created_at      │
│ file_size    │       └──────────────────┘   │   └─────────────────┘
│ width        │                              │
│ height       │       ┌──────────────────┐   │
│ created_at   │       │ search_hierarchy │   │
└──────────────┘       ├──────────────────┤   │
                       │ ancestor_id (FK)─┼───┤
┌──────────────┐       │ descendant_id(FK)┼───┘
│  images_fts  │       │ depth            │
├──────────────┤       └──────────────────┘
│ rowid → images.id
│ tags (FTS5)  │       ┌──────────────────┐
└──────────────┘       │   system_meta    │
                       ├──────────────────┤
                       │ key (PK)         │
                       │ value            │
                       └──────────────────┘
```

### 表说明

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| `images` | 图片元数据 | md5 唯一标识，tags 空格分隔 |
| `images_fts` | FTS5 全文索引 | 自动同步 images.tags |
| `search_groups` | 规则组 | parent_id 实现树结构 |
| `search_keywords` | 关键词 | 属于某个 group |
| `search_hierarchy` | 闭包表 | 快速查询祖先/后代 |
| `system_meta` | 系统配置 | rules_version 版本号 |
| `search_version_log` | 版本日志 | CAS 操作记录 |

## 核心算法

### 1. 关键词膨胀（Keyword Expansion）

```
输入: 搜索词 "车辆"
处理:
  1. 查找包含 "车辆" 的 group
  2. 通过 search_hierarchy 获取所有子孙 group
  3. 收集所有子孙 group 的 keywords
输出: ["车辆", "汽车", "自行车", "卡车", "轿车", ...]
```

```sql
-- 获取所有子孙关键词
SELECT DISTINCT sk.keyword
FROM search_keywords sk
JOIN search_hierarchy sh ON sk.group_id = sh.descendant_id
WHERE sh.ancestor_id = ?
```

### 2. 乐观锁（CAS）流程

```
客户端                              服务端
   │                                  │
   │  1. 读取数据 + version           │
   │◄─────────────────────────────────│
   │                                  │
   │  2. 修改请求 + base_version      │
   │─────────────────────────────────►│
   │                                  │
   │         3. 检查版本              │
   │         if base_version != current_version:
   │             return 409 Conflict  │
   │         else:                    │
   │             执行修改             │
   │             version++            │
   │◄─────────────────────────────────│
   │  4. 返回 new_version             │
```

### 3. FTS5 搜索

```sql
-- 搜索包含任一标签的图片
SELECT i.* FROM images i
JOIN images_fts fts ON i.id = fts.rowid
WHERE images_fts MATCH '"标签1" OR "标签2"'
```

## 前端组件关系

```
App.vue
└── Gallery.vue (主页面)
    ├── TagInput.vue (搜索框)
    ├── MemeCard.vue[] (图片网格)
    ├── FloatingButtons.vue (FAB)
    ├── RuleTree.vue (侧边栏)
    │   └── RuleGroupNode.vue[] (递归)
    ├── UploadModal.vue (上传)
    ├── ImageEditModal.vue (编辑)
    │   └── TagInput.vue
    └── ToastContainer.vue (通知)
```

## 状态管理

### Pinia Store: useGlobalStore

```typescript
{
  clientId: string,        // 客户端唯一 ID
  rulesVersion: number,    // 当前规则版本
  rulesTree: RulesTree,    // 规则树缓存
  isLoading: boolean       // 全局加载状态
}
```

### 本地存储 (LocalStorage)

| Key | 用途 |
|-----|------|
| `bqbq_client_id` | 客户端 ID |
| `bqbq_rules_version` | 规则版本号 |

## 性能优化

1. **图片懒加载**: `loading="lazy"`
2. **ETag 缓存**: 规则树 304 响应
3. **FTS5 索引**: 全文搜索加速
4. **闭包表**: O(1) 祖先/后代查询
5. **MD5 去重**: 避免重复上传

## 安全考虑

1. **文件类型验证**: 仅允许图片格式
2. **MD5 校验**: 防止文件篡改
3. **CORS 配置**: 限制跨域来源
4. **SQL 参数化**: 防止注入
