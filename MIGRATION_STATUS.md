# BQBQ v2 迁移状态文档

> 最后更新: 2026-01-30
> 迁移进度: **99%** (仅剩可选的规则树数据缓存功能)

本文档记录从旧项目 `bqbq_backend-1/精确搜索SQLite端(旧)` 到新项目 `bqbq_v2` 的功能迁移状态。

---

## 一、后端功能迁移状态

### 1.1 已完成迁移 ✅

| 功能 | 旧项目实现 | 新项目实现 | 文件位置 |
|------|-----------|-----------|----------|
| **缩略图生成** | `_create_thumbnail_file()` 600x600 JPEG | `create_thumbnail()` | `backend/app/main.py` |
| **动图随机帧提取** | `_extract_random_frame()` | `extract_random_frame()` | `backend/app/main.py` |
| **启动扫描导入** | `scan_and_import_folder()` 并行处理 | `scan_and_import_folder()` | `backend/app/main.py` |
| **缩略图服务端点** | `/thumbnails/<path:f>` | `/thumbnails/{filename}` | `backend/app/main.py` |
| **tags_dict 表** | 标签使用次数统计 | `tags_dict` 表 | `backend/app/database.py` |
| **重建标签字典** | `rebuild_tags_dict()` | `rebuild_tags_dict()` | `backend/app/database.py` |
| **定时更新 tags_dict** | `start_tags_dict_updater()` 15分钟 | `start_tags_dict_updater()` | `backend/app/main.py` |
| **标签建议排序** | `/api/meta/tags` 按使用次数 | `/api/meta/tags` | `backend/app/routers/search.py` |
| **高级搜索 API** | 二维数组 keywords/excludes | `/api/search/advanced` | `backend/app/routers/search.py` |
| **交集排除** | `excludes_and` 三维数组 | `excludes_and` 参数 | `backend/app/routers/search.py` |
| **排除扩展名** | `exclude_extensions` | `exclude_extensions` 参数 | `backend/app/routers/search.py` |
| **分辨率排序** | `resolution_desc/asc` | `resolution_desc/asc` | `backend/app/routers/search.py` |
| **MD5 检查 API** | `/api/check_md5` | `/api/images/check-md5/{md5}` | `backend/app/routers/images.py` |
| **导出兼容旧格式** | `/api/export/all` | `/api/export` | `backend/app/routers/system.py` |
| **导入兼容旧格式** | `/api/import/all` | `/api/import` | `backend/app/routers/system.py` |
| **性能索引** | 多个 CREATE INDEX | 多个索引 | `backend/app/database.py` |
| **重复图片时间刷新** | `refresh_time` 参数 | 上传时自动刷新 | `backend/app/main.py` |
| **规则组启用/禁用** | `is_enabled` 字段 | `enabled` 字段 | `backend/app/routers/rules.py` |

### 1.2 结构差异说明

| 项目 | 旧项目 | 新项目 | 说明 |
|------|--------|--------|------|
| **框架** | Flask | FastAPI | 异步支持更好 |
| **图片主键** | `md5` | `id` (自增) | 新项目使用自增 ID |
| **层级关系表** | 简单 `parent_id/child_id` | 闭包表 `ancestor/descendant/depth` | 新项目查询更快 |
| **FTS 索引** | `images_fts(md5, tags_text)` | `images_fts(tags)` + 触发器 | 新项目自动同步 |
| **关键词膨胀** | 前端实现 | 后端实现 | 新项目更安全，减少前端复杂度 |

### 1.3 未迁移/不需要迁移

| 功能 | 原因 |
|------|------|
| **Werkzeug reloader 检测** | FastAPI 使用 uvicorn，机制不同 |
| **Flask CORS** | FastAPI 有自己的 CORS 中间件 |

---

## 二、前端功能迁移状态

### 2.1 已完成迁移 ✅

| 功能 | 旧项目实现 | 新项目实现 | 文件位置 |
|------|-----------|-----------|----------|
| **缩略图/HQ 模式** | `loadOriginalImage()` | `currentSrcType` 切换 | `MemeCard.vue` |
| **首屏 eager 加载** | 前 4 张 `loading="eager"` | `loadingStrategy` 计算属性 | `MemeCard.vue` |
| **缩略图加载失败降级** | 自动切换原图 | `handleImageError()` | `MemeCard.vue` |
| **HQ 加载指示器** | 旋转图标 | `isLoadingHQ` + RotateCw | `MemeCard.vue` |
| **分辨率排序选项** | 6 种排序 | `sortOptions` 数组 | `FloatingButtons.vue` |
| **高级搜索类型** | 二维/三维数组 | `AdvancedSearchRequest` | `types/index.ts` |
| **高级搜索 API** | - | `advancedSearch()` | `useApi.ts` |
| **MD5 检查 API** | - | `checkMD5()` | `useApi.ts` |
| **标签建议 API** | - | `getTagSuggestions()` | `useApi.ts` |
| **排除扩展名类型** | - | `exclude_extensions` | `types/index.ts` |
| **批量编辑样式** | CSS 类 | `.batch-mode` 等 | `style.css` |
| **noUiSlider 样式** | 自定义滑块 | `#tag-slider` 样式 | `style.css` |
| **Toast 动画** | slideIn/Out | `@keyframes` | `style.css` |
| **关键词膨胀** | `expandSingleKeyword()` | 后端 `expand` 参数 | `search.py` |
| **膨胀统计徽章** | 前端计算 | 后端返回 `expanded_tags` | `Gallery.vue` |
| **膨胀开关** | `isExpansionEnabled` | `useGlobalStore.ts` | localStorage 持久化 |
| **FAB 折叠模式** | `toggleFabCollapsed()` | `isCollapsed` | `FloatingButtons.vue` |
| **FAB 状态持久化** | localStorage | `useGlobalStore.ts` | localStorage 持久化 |
| **临时标签面板** | `tempTagInput` | `showTempTagsPanel` | `FloatingButtons.vue` |
| **标签数量筛选面板** | `initTagCountSlider()` | `showTagCountPanel` | `FloatingButtons.vue` |
| **规则树拖拽** | HTML5 Drag & Drop | `@dragstart/@drop` | `RuleGroupNode.vue` |
| **批量编辑模式(图片)** | `isTempTagMode` | `isBatchMode` | `Gallery.vue` |
| **自定义滚动条** | `.custom-scrollbar` | `.custom-scrollbar` | `style.css` |
| **图片复制到剪贴板** | Clipboard API | `handleCopyImage()` | `Gallery.vue` |
| **状态持久化** | localStorage | `useGlobalStore.ts` | 膨胀/HQ/排序/FAB |
| **乐观更新** | `handleSave()` | `useOptimisticUpdate.ts` | 通用 composable |
| **冲突自动重试** | `retryCount` | `useOptimisticUpdate.ts` | 最多 3 次重试 |
| **TagInput 标签建议** | `datalist` | 下拉列表 | `TagInput.vue` |
| **TagInput 同义词组** | 逗号分隔 | 逗号分隔 | `TagInput.vue` |
| **TagInput 交集排除** | `-tag1,tag2` | `-tag1,tag2` | `TagInput.vue` |
| **规则组启用/禁用** | `toggleGroupEnabled()` | `toggleGroupEnabled()` | `RuleTree.vue` |
| **规则树批量编辑** | `batchEditMode` | `batchEditMode` | `RuleTree.vue` |
| **规则树搜索** | `filterRulesTree()` | `searchText` + `filteredGroups` | `RuleTree.vue` |
| **循环依赖检测** | `detectCycle()` | `detectCycles()` | `RuleTree.vue` |
| **FAB 位置拖拽** | `initFabMiniDrag()` | Pointer Events | `FloatingButtons.vue` |
| **标签缓存机制** | localStorage | `useGlobalStore.ts` | 10 分钟缓存 |
| **删除关键词** | `removeKeyword()` | `deleteKeyword()` | `RuleGroupNode.vue` |
| **批量移动层级** | `handleBatchHierarchyChange()` | `batchMoveHierarchy()` | `RuleTree.vue` |

### 2.2 未迁移功能 ❌ (待实现)

| 功能 | 旧项目实现 | 优先级 | 说明 | 修改文件 |
|------|-----------|--------|------|----------|
| **规则树数据缓存** | localStorage 缓存 | 低 | 304 响应时从 localStorage 加载（可选，ETag 已足够） | `RuleTree.vue` |

### 2.3 本次迁移完成 ✅ (2026-01-30)

| 功能 | 实现说明 | 修改文件 |
|------|----------|----------|
| **扩展名建议** | 输入 `.` 时显示 `.png`, `.gif` 等扩展名建议 | `TagInput.vue` |
| **规则树展开/折叠全部** | 工具栏添加展开/折叠全部按钮 | `RuleTree.vue` |
| **搜索后滚动到匹配项** | 规则树搜索后自动滚动到第一个匹配项 | `RuleTree.vue`, `RuleGroupNode.vue` |
| **关键词启用/禁用** | 单个关键词的启用/禁用（前后端完整实现） | `database.py`, `rule.py`, `rules.py`, `useApi.ts`, `types/index.ts`, `RuleTree.vue`, `RuleGroupNode.vue` |

### 2.4 设计差异说明

| 功能 | 旧项目 | 新项目 | 说明 |
|------|--------|--------|------|
| **关键词膨胀位置** | 前端 `expandSingleKeyword()` | 后端 `expand` 参数 | 新项目更安全，减少前端复杂度 |
| **规则树滚动条** | Pointer Events 自定义滚动条 | 原生滚动条 + CSS | 新项目更简洁，兼容性更好 |
| **标签建议** | `<datalist>` 原生 | 自定义下拉列表 | 新项目支持键盘导航，体验更好 |

---

## 三、视觉样式迁移状态

### 3.1 已完成迁移 ✅

| 样式 | 文件位置 |
|------|----------|
| `.custom-scrollbar` | `style.css` |
| `.tag-capsule` + `@keyframes popIn` | `style.css` |
| `.is-trash` 回收站样式 | `style.css` |
| `.overlay-tag` 标签样式 | `style.css` |
| `.image-info` 文字阴影 | `style.css` |
| `.top-toolbar` 工具栏 | `style.css` |
| `.load-failed` 加载失败 | `style.css` |
| `.drop-gap` 拖拽放置区 | `style.css` |
| `.root-drop-zone` 根目录放置区 | `style.css` |
| `.group-node.dragging` | `style.css` |
| `.batch-mode` 批量模式 | `style.css` |
| `#tag-slider` noUiSlider | `style.css` |
| Toast 动画 | `style.css` |
| `.fab-mini-strip` 迷你按钮条 | `style.css` |
| `.fab-mini-btn` 迷你按钮 | `style.css` |
| 搜索高亮 `<mark>` | `RuleGroupNode.vue` |
| 禁用组样式 | `RuleGroupNode.vue` |
| 冲突节点样式 | `RuleGroupNode.vue` |
| 批量选择复选框 | `RuleGroupNode.vue` |

### 3.2 未迁移样式 ❌ (可选)

| 样式 | 旧项目位置 | 说明 |
|------|-----------|------|
| `.custom-scrollbar-v` | `style.css` | Pointer Events 垂直滚动条（可选，原生滚动条已足够） |
| `.custom-scrollbar-h` | `style.css` | Pointer Events 水平滚动条（可选，原生滚动条已足够） |
| `.scrollbar-track` | `style.css` | 滚动条轨道样式 |
| `.scrollbar-thumb` | `style.css` | 滚动条滑块样式 |
| `.scrollbar-corner` | `style.css` | 滚动条角落样式 |
| `#rules-tree-scroll-wrapper` | `style.css` | 规则树滚动容器（新项目使用简单 overflow-auto） |

---

## 四、API 端点对照表

### 4.1 图片 API

| 旧项目 | 新项目 | 状态 |
|--------|--------|------|
| `POST /api/upload` | `POST /api/upload` | ✅ |
| `POST /api/search` | `POST /api/search` | ✅ |
| `POST /api/update_tags` | `PUT /api/images/{id}/tags` | ✅ |
| `POST /api/check_md5` | `GET /api/images/check-md5/{md5}` | ✅ |
| - | `POST /api/search/advanced` | ✅ 新增 |

### 4.2 规则树 API

| 旧项目 | 新项目 | 状态 |
|--------|--------|------|
| `GET /api/rules` | `GET /api/rules` | ✅ |
| `POST /api/rules/group/add` | `POST /api/rules/groups` | ✅ |
| `POST /api/rules/group/update` | `PUT /api/rules/groups/{id}` | ✅ |
| `POST /api/rules/group/toggle` | `POST /api/rules/groups/{id}/toggle` | ✅ |
| `POST /api/rules/group/delete` | `DELETE /api/rules/groups/{id}` | ✅ |
| `POST /api/rules/group/batch` | `POST /api/rules/groups/batch` | ✅ |
| `POST /api/rules/keyword/add` | `POST /api/rules/groups/{id}/keywords` | ✅ |
| `POST /api/rules/keyword/remove` | `DELETE /api/rules/keywords/{id}` | ✅ |
| `POST /api/rules/hierarchy/add` | `POST /api/rules/hierarchy/add` | ✅ |
| `POST /api/rules/hierarchy/remove` | `POST /api/rules/hierarchy/remove` | ✅ |
| `POST /api/rules/hierarchy/batch_move` | `POST /api/rules/hierarchy/batch_move` | ✅ |

### 4.3 系统 API

| 旧项目 | 新项目 | 状态 |
|--------|--------|------|
| `GET /api/meta/tags` | `GET /api/meta/tags` | ✅ |
| `GET /api/export/all` | `GET /api/export` | ✅ |
| `POST /api/import/all` | `POST /api/import` | ✅ |
| - | `GET /api/version` | ✅ 新增 |
| - | `GET /api/stats` | ✅ 新增 |
| - | `GET /api/tags` | ✅ 新增 |

---

## 五、数据库表结构对照

### 5.1 images 表

```sql
-- 旧项目
CREATE TABLE images (
    md5 TEXT PRIMARY KEY,
    filename TEXT,
    created_at REAL,
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0,
    size INTEGER DEFAULT 0
);

-- 新项目
CREATE TABLE images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    md5 TEXT UNIQUE NOT NULL,
    tags TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_size INTEGER DEFAULT 0,
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0
);
```

### 5.2 规则相关表

```sql
-- 旧项目: search_groups
CREATE TABLE search_groups (
    group_id INTEGER PRIMARY KEY,
    group_name TEXT NOT NULL,
    is_enabled BOOLEAN DEFAULT 1
);

-- 新项目: search_groups
CREATE TABLE search_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER DEFAULT NULL,
    enabled INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

```sql
-- 旧项目: search_hierarchy (简单父子关系)
CREATE TABLE search_hierarchy (
    parent_id INTEGER,
    child_id INTEGER,
    PRIMARY KEY (parent_id, child_id)
);

-- 新项目: search_hierarchy (闭包表)
CREATE TABLE search_hierarchy (
    ancestor_id INTEGER NOT NULL,
    descendant_id INTEGER NOT NULL,
    depth INTEGER NOT NULL,
    PRIMARY KEY (ancestor_id, descendant_id)
);
```

### 5.3 新增表

```sql
-- 新项目独有: tags_dict
CREATE TABLE tags_dict (
    name TEXT PRIMARY KEY,
    use_count INTEGER DEFAULT 0
);

-- 新项目独有: search_version_log
CREATE TABLE search_version_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER NOT NULL,
    client_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 六、待实现功能详细说明

### 6.1 扩展名建议（中优先级）

**旧项目实现** (`script.js:970-978`):
```javascript
// 特殊处理：当输入以 . 开头时（或 -. 开头），显示扩展名建议
if (searchText.startsWith('.')) {
    const partialExt = searchText.slice(1).toLowerCase();
    const extensionSuggestions = SUPPORTED_EXTENSIONS
        .filter(ext => ext.startsWith(partialExt))
        .map(ext => `${prefix}.${ext}`);
    dl.innerHTML = extensionSuggestions.map(t => `<option value="${t}">`).join('');
    return;
}
```

**修改文件**: `frontend/src/components/TagInput.vue`

**实现方案**:
1. 在 `filteredSuggestions` 计算属性中添加扩展名检测
2. 定义 `SUPPORTED_EXTENSIONS` 常量
3. 当输入以 `.` 开头时，返回扩展名建议

### 6.2 规则树展开/折叠全部（低优先级）

**旧项目实现** (`script.js`):
```javascript
expandAllGroups() {
    // 收集所有组ID并添加到 expandedGroupIds
}
collapseAllGroups() {
    // 清空 expandedGroupIds
}
```

**修改文件**: `frontend/src/components/RuleTree.vue`

**实现方案**:
1. 添加 `expandAll()` 和 `collapseAll()` 函数
2. 在工具栏添加展开/折叠全部按钮

### 6.3 搜索后滚动到匹配项（低优先级）

**旧项目实现** (`script.js:4750-4757`):
```javascript
// 滚动到第一个匹配项
const container = document.getElementById('rules-tree-container');
if (container) {
    const firstMatch = container.querySelector('.group-node.bg-blue-50');
    if (firstMatch) {
        firstMatch.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}
```

**修改文件**: `frontend/src/components/RuleTree.vue`

**实现方案**:
1. 在 `filterTree()` 后使用 `nextTick` 滚动到第一个匹配项
2. 使用 `ref` 获取匹配元素并调用 `scrollIntoView()`

### 6.4 关键词启用/禁用（低优先级）

**旧项目实现**:
- `search_keywords` 表有 `is_enabled` 字段
- 膨胀时只收集 `k.isEnabled` 为 true 的关键词

**修改文件**:
- `backend/app/database.py` - 添加 `enabled` 字段
- `backend/app/models/rule.py` - 添加 `enabled` 字段到 `KeywordResponse`
- `backend/app/routers/rules.py` - 添加切换关键词启用状态 API
- `frontend/src/components/RuleGroupNode.vue` - 添加启用/禁用按钮

---

## 七、已完成功能清单

- ✅ 缩略图生成和服务
- ✅ 动图随机帧提取
- ✅ 启动扫描导入
- ✅ 标签使用次数统计
- ✅ 高级搜索 API
- ✅ 交集排除
- ✅ 排除扩展名
- ✅ 分辨率排序
- ✅ MD5 检查
- ✅ 导入导出
- ✅ 关键词膨胀（后端实现）
- ✅ 膨胀统计徽章
- ✅ FAB 折叠模式
- ✅ FAB 位置拖拽
- ✅ 临时标签面板
- ✅ 标签数量筛选
- ✅ 规则树拖拽
- ✅ 规则组启用/禁用
- ✅ 规则树批量编辑
- ✅ 规则树搜索
- ✅ 循环依赖检测
- ✅ 标签缓存机制
- ✅ 删除关键词
- ✅ 批量移动层级
- ✅ 乐观更新和冲突重试
- ✅ 图片复制到剪贴板
- ✅ 状态持久化

---

*文档更新时间: 2026-01-30*
*迁移状态: 95% 完成（剩余 5 个低优先级可选功能）*
