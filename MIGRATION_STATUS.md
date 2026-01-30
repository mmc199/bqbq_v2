# BQBQ v2 迁移状态文档

> 最后更新: 2026-01-30
> 目标: 完全复刻旧项目的所有功能和视觉样式
> CSS 样式已同步到: `frontend/src/style.css`

## 项目路径

| 项目 | 路径 |
|------|------|
| **旧项目** | `C:\000soft\qqpy机器人-git\bqbq_backend-1\精确搜索SQLite端(旧)` |
| **新项目** | `C:\000soft\qqpy机器人-git\bqbq_v2` |

---

## 一、常量配置对照表

### 1.1 缓存与存储键名

| 常量名 | 值 | 说明 | 新项目位置 |
|--------|-----|------|-----------|
| `CACHE_DURATION` | `10 * 60 * 1000` | 缓存有效期 10分钟 | `useApi.ts` |
| `TAGS_CACHE_KEY` | `'bqbq_tag_cache'` | 标签缓存键名 | `useApi.ts` |
| `TAGS_TIME_KEY` | `'bqbq_tag_timestamp'` | 标签时间戳键名 | `useApi.ts` |
| `RULES_VERSION_KEY` | `'bqbq_rules_version'` | 规则版本号键名 | `useGlobalStore.ts` |
| `CLIENT_ID_KEY` | `'bqbq_client_id'` | 客户端ID键名 | `useGlobalStore.ts` |
| `FAB_COLLAPSED_KEY` | `'bqbq_fab_collapsed'` | FAB折叠状态键名 | `useGlobalStore.ts` |
| `FAB_MINI_POSITION_KEY` | `'bqbq_fab_mini_position'` | FAB迷你位置键名 | `FloatingButtons.vue` |
| `SUPPORTED_EXTENSIONS` | `['gif', 'png', 'jpg', 'webp']` | 支持的图片扩展名 | `types/index.ts` |

### 1.2 分页配置

| 配置项 | 旧项目值 | 新项目值 | 说明 |
|--------|---------|---------|------|
| `limit` | `40` | `40` | 每页数量 |
| `offset` | `0` | `0` | 初始偏移量 |

---

## 二、UI 元素尺寸与位置配置

> 以下信息提取自旧项目 `script.js` 和 `index.html`，**必须严格遵守**

### 2.1 FAB 悬浮按钮组布局

| 配置项 | 值 | Tailwind Class | 说明 |
|--------|-----|----------------|------|
| 容器位置 | `fixed right-16px top-112px` | `fixed right-4 top-[7rem]` | 距右 16px，距顶 112px |
| 布局方式 | `grid 2×5` | `grid grid-cols-2` | 2 列网格 |
| 按钮间距 | `gap: 12px` | `gap-3` | 按钮之间 12px 间距 |
| 按钮尺寸 | `56×56px` | `w-14 h-14` | 主按钮尺寸 |
| 按钮圆角 | `16px` | `rounded-2xl` | 圆角半径 |
| z-index | `50` | `z-50` | 层级 |

**按钮排列顺序（从上到下，从左到右）：**

| 行 | 左列 | 右列 |
|----|------|------|
| 1 | 导出（琥珀 `amber`） | 导入（靛蓝 `indigo`） |
| 2 | 标签数量（青色 `cyan`） | 临时标签（紫色 `purple`） |
| 3 | 排序（灰色 `slate`） | HQ模式（灰/蓝色） |
| 4 | 回收站（灰/红色） | 上传（翠绿 `emerald`） |
| 5 | 搜索（蓝色 `blue`+卫星） | 规则树（绿色 `green`） |

### 2.2 FAB 按钮详细配置

| 按钮ID | 图标 | 背景色 | 文字/图标色 | 边框色 | hover背景 |
|--------|------|--------|------------|--------|-----------|
| `fab-export` | `download` | `white` | `amber-600` | `amber-200` | `amber-50` |
| `fab-import` | `upload` | `white` | `indigo-600` | `indigo-200` | `indigo-50` |
| `fab-tag-count` | `hash` | `white` | `cyan-600` | `cyan-200` | `cyan-50` |
| `fab-temp-tags` | `stamp` | `white` | `purple-600` | `purple-100` | `purple-50` |
| `fab-sort` | `arrow-up-down` | `white` | `slate-600` | `slate-200` | `slate-50` |
| `fab-hq` | `HQ文字` | `white` | `slate-400`/`blue-600` | `slate-200` | `slate-50`/`blue-50` |
| `fab-trash` | `trash-2` | `white` | `slate-400`/`red-500` | `slate-200` | `red-50` |
| `fab-upload` | `image-plus` | `emerald-500` | `white` | 无 | `emerald-600` |
| `fab-search` | `search` | `blue-600` | `white` | 无 | `blue-700` |
| `fab-tree` | `tree-pine` | `white` | `green-600`/`yellow-600` | `green-200` | `green-50` |

### 2.3 FAB 卫星按钮配置

| 配置项 | 值 | Tailwind Class | 说明 |
|--------|-----|----------------|------|
| 尺寸 | `28×28px` | `w-7 h-7` 或 `w-8 h-8` | 卫星按钮尺寸 |
| 圆角 | `50%` | `rounded-full` | 圆形 |
| 位置偏移 | `-8px` | `-top-2 -right-2` | 相对主按钮边缘偏移 |
| 显示方式 | 悬停显示 | `opacity-0 group-hover:opacity-100` | 主按钮 hover 时显示 |

**搜索按钮的卫星按钮：**

| 位置 | ID | 功能 | 背景色 | hover背景 |
|------|-----|------|--------|-----------|
| 左上 | `fab-toggle-btn` | 折叠FAB | `white` | `slate-100` |
| 右上 | `clear-search-btn` | 清空搜索 | `white` | `red-50` |
| 右下 | `reload-search-btn` | 刷新搜索 | `white` | `green-50` |

### 2.4 FAB 迷你按钮条（折叠模式）

| 配置项 | 值 | Tailwind Class | 说明 |
|--------|-----|----------------|------|
| 位置 | `fixed right-0 top-16rem` | `fixed right-0` | 右侧，可拖拽调整 |
| 按钮尺寸 | `32×32px` | `w-8 h-8` | 迷你按钮尺寸 |
| 按钮圆角 | `8px` | `rounded-lg` | 圆角半径 |
| 容器圆角 | `12px 0 0 12px` | `rounded-l-xl` | 左侧圆角 |
| 背景 | `rgba(255,255,255,0.95)` | `bg-white/95` | 半透明白色 |
| 可拖拽 | 是 | - | 支持上下拖拽调整位置 |
| 拖拽阈值 | `5px` | - | 移动超过5px才算拖拽 |
| 最小距顶 | `80px` | - | 拖拽位置限制 |

**迷你按钮列表：**

| 按钮 | 图标 | 功能 |
|------|------|------|
| 展开 | `chevrons-left` | 展开FAB组 |
| 清空 | `x` | 清空标签 |
| 刷新 | `refresh-cw` | 刷新搜索 |
| 搜索 | `search` | 执行搜索 |
| 膨胀 | `tree-pine` | 膨胀开关 |
| 上传 | `image-plus` | 上传图片 |

### 2.5 搜索栏配置

| 配置项 | 值 | Tailwind Class | 说明 |
|--------|-----|----------------|------|
| 容器位置 | `sticky top-0` | `sticky top-0` | 粘性定位 |
| 容器高度 | `min-h-16` | `min-h-16` | 最小高度 64px |
| 容器背景 | `white/90` | `bg-white/90` | 半透明白色 |
| 容器边框 | `border-b border-slate-200` | `border-b border-slate-200` | 底部边框 |
| 容器阴影 | `shadow-sm` | `shadow-sm` | 小阴影 |
| z-index | `30` | `z-30` | 层级 |
| 输入框背景 | `slate-100` → `white`（聚焦） | `bg-slate-100 focus-within:bg-white` | 背景色变化 |
| 输入框圆角 | `12px` | `rounded-xl` | 圆角半径 |
| 输入框高度 | `min: 50px, max: 120px` | `min-h-[50px] max-h-[120px]` | 最小/最大高度 |
| 聚焦边框 | `blue-300` | `focus-within:border-blue-300` | 聚焦时边框色 |
| 聚焦光晕 | `ring-2 ring-blue-100` | `focus-within:ring-2 focus-within:ring-blue-100` | 聚焦时光晕 |

### 2.6 图片网格配置

| 配置项 | 值 | Tailwind Class | 说明 |
|--------|-----|----------------|------|
| 布局方式 | `grid auto-fill` | `grid` | 网格布局 |
| 间距 | `16px` | `gap-4` | 卡片间距 |
| 卡片比例 | `aspect-ratio: 1` | `aspect-square` | 正方形 |
| 卡片圆角 | `12px` | `rounded-xl` | 圆角半径 |
| 卡片阴影 | `shadow-md` | `shadow-md` | 中等阴影 |
| 底部留白 | `160px` | `pb-40` | 为FAB留空间 |

**响应式列数：**

| 断点 | 宽度 | 列数 | Tailwind Class |
|------|------|------|----------------|
| 默认 | < 640px | 2 | `grid-cols-2` |
| sm | ≥ 640px | 3 | `sm:grid-cols-3` |
| md | ≥ 768px | 4 | `md:grid-cols-4` |
| lg | ≥ 1024px | 5 | `lg:grid-cols-5` |
| xl | ≥ 1280px | 6 | `xl:grid-cols-6` |
| 2xl | ≥ 1536px | 8 | `2xl:grid-cols-8` |

### 2.7 规则树侧边栏配置

| 配置项 | 值 | Tailwind Class | 说明 |
|--------|-----|----------------|------|
| 位置 | `fixed top-16 left-0` | `fixed top-16 left-0` | 左侧固定 |
| 宽度 | `288px` | `w-72` | 侧边栏宽度 |
| 高度 | `calc(100vh - 8rem)` | `style="height: calc(100vh - 8rem)"` | 动态高度 |
| 默认状态 | 隐藏（向左平移） | `-translate-x-full` | 默认隐藏 |
| 过渡动画 | `300ms` | `transition-transform duration-300` | 平滑过渡 |
| z-index | `40` | `z-40` | 层级 |
| 背景 | `white` | `bg-white` | 白色背景 |
| 边框 | `border-r border-slate-200/50` | `border-r border-slate-200/50` | 右侧边框 |
| 阴影 | `shadow-xl` | `shadow-xl` | 大阴影 |

**侧边栏切换按钮：**

| 配置项 | 值 | Tailwind Class | 说明 |
|--------|-----|----------------|------|
| 位置 | `fixed top-16 left-0` | `fixed top-16 left-0` | 贴边 |
| 宽度 | `20px` → `24px`（hover） | `w-5 hover:w-6` | 可变宽度 |
| 高度 | `calc(100vh - 8rem)` | 同侧边栏 | 全高 |
| 圆角 | `右侧圆角` | `rounded-r-md` | 右侧圆角 |
| z-index | `50` | `z-50` | 层级 |

---

## 三、图片卡片样式配置

### 3.1 卡片基础样式

```html
<!-- 旧项目 HTML 结构 -->
<div class="meme-card relative bg-white rounded-xl shadow-md overflow-hidden aspect-square">
    <div class="relative w-full h-full">
        <img class="image-element w-full h-full object-cover cursor-pointer">
    </div>
    <div class="image-overlay absolute inset-0 flex flex-col justify-between p-2">
        <div class="top-toolbar flex justify-end gap-1">...</div>
        <div class="tags-container-element flex flex-wrap gap-1">...</div>
    </div>
</div>
```

### 3.2 覆盖层标签样式

```css
/* 旧项目 style.css - 必须完全复刻 */
.overlay-tag {
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans",
                 "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", sans-serif;
    background-color: rgba(255, 255, 255, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.1);
    text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8),
                -1px -1px 2px rgba(0, 0, 0, 0.8);
    overflow-wrap: break-all;
    max-width: 100%;
    display: block;
}
```

### 3.3 回收站样式

```css
/* 旧项目 style.css - 必须完全复刻 */
.is-trash {
    border: 8px dashed #fca5a5 !important;
    background-color: #fef2f2;
    box-sizing: border-box;
    position: relative;
}

.is-trash::after {
    content: "已删除";
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%) rotate(-15deg);
    font-size: 1.5rem;
    font-weight: 900;
    color: #ef4444;
    opacity: 0.3;
    pointer-events: none;
    z-index: 0;
}

.is-trash img {
    opacity: 0.5;
    filter: grayscale(100%);
}

/* 回收站模式下，已删除图片正常显示 */
.trash-mode-active .is-trash::after {
    display: none;
}
.trash-mode-active .is-trash img {
    opacity: 1;
    filter: none;
}
```

### 3.4 加载失败样式

```css
/* 旧项目 style.css */
.load-failed img {
    opacity: 0.3;
    filter: grayscale(100%);
}

.error-overlay {
    background-color: transparent !important;
}
```

### 3.5 图片覆盖层渐变

```css
/* 旧项目 style.css */
.image-overlay {
    background: linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.0) 0%, transparent 100%);
    pointer-events: none;
}
.image-overlay > * {
    pointer-events: auto;
}

.image-info {
    text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8),
                -1px -1px 2px rgba(0, 0, 0, 0.8);
}
```

---

## 四、标签胶囊样式配置

### 4.1 标签类型与颜色

| 标签类型 | 条件 | CSS 类名 |
|----------|------|----------|
| 排除+同义词 | `exclude && synonym` | `bg-orange-100 text-orange-700 border-orange-300 hover:bg-orange-200` |
| 排除标签 | `exclude` | `bg-red-100 text-red-600 border-red-200 hover:bg-red-200` |
| 同义词组 | `synonym` | `bg-green-100 text-green-600 border-green-200 hover:bg-green-200` |
| 紫色主题 | `theme === 'purple'` | `bg-purple-100 text-purple-700 border-purple-200 hover:bg-purple-200` |
| 蓝色主题 | `theme === 'blue'` | `bg-blue-100 text-blue-600 border-blue-200 hover:bg-blue-200` |

### 4.2 标签胶囊动画

```css
/* 旧项目 style.css */
.tag-capsule {
    animation: popIn 0.2s cubic-bezier(0.18, 0.89, 0.32, 1.28);
}

@keyframes popIn {
    0% { transform: scale(0.9); opacity: 0; }
    100% { transform: scale(1); opacity: 1; }
}
```

### 4.3 标签胶囊基础样式

```html
<!-- Tailwind 类名 -->
<div class="tag-capsule flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold
            cursor-pointer select-none transition-transform active:scale-95 max-w-full break-all">
    <span>标签文本</span>
    <span class="ml-1 hover:text-black/50 text-lg leading-none px-1 rounded-full
                 hover:bg-black/5 transition-colors">&times;</span>
</div>
```

---

## 五、规则树样式配置

### 5.1 拖拽放置区样式

```css
/* 旧项目 style.css - 必须完全复刻 */

/* 节点间隙放置区：正常状态（收起） */
.drop-gap {
    height: 4px;
    margin: 2px 0;
    border-radius: 4px;
    background-color: transparent;
    transition: all 0.15s ease-out;
    position: relative;
}

/* 节点间隙放置区：拖拽悬停时展开 */
.drop-gap.drag-over {
    height: 24px;
    background-color: #dbeafe;
    border: 2px dashed #3b82f6;
    display: flex;
    align-items: center;
    justify-content: center;
}

.drop-gap.drag-over::after {
    content: "放置到此处";
    font-size: 10px;
    color: #3b82f6;
    font-weight: bold;
}

/* 根目录放置区 */
.root-drop-zone {
    min-height: 28px;
    margin-bottom: 8px;
    border-radius: 6px;
    border: 2px dashed #d1d5db;
    background-color: #f9fafb;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease-out;
    cursor: pointer;
    color: #9ca3af;
    font-size: 11px;
    font-weight: 500;
}

.root-drop-zone:hover {
    border-color: #9ca3af;
    background-color: #f3f4f6;
}

.root-drop-zone.drag-over {
    min-height: 40px;
    border-color: #10b981;
    background-color: #d1fae5;
    border-style: solid;
    color: #059669;
    font-weight: bold;
}

/* 拖拽中的组节点样式 */
.group-node.dragging {
    opacity: 0.4;
    border: 2px dashed #94a3b8 !important;
    background-color: #f1f5f9;
}

/* 作为嵌套目标时的组节点样式 */
.group-node.drop-target-child {
    background-color: #eff6ff;
    box-shadow: inset 0 0 0 2px #3b82f6;
    border-radius: 8px;
}
```

### 5.2 批量编辑样式

```css
/* 旧项目 style.css */

/* 批量模式下选中的组节点样式 */
.group-node.ring-2 {
    border-radius: 6px;
    margin: 2px 0;
}

/* 批量模式下 group-header 的样式 */
.group-header.batch-mode {
    transition: background-color 0.15s ease;
}

.group-header.batch-mode:hover {
    background-color: rgba(59, 130, 246, 0.1);
}

/* 复选框包装器样式 */
.batch-checkbox-wrapper {
    flex-shrink: 0;
    border-radius: 4px;
    transition: background-color 0.15s ease;
    cursor: grab;
}

.batch-checkbox-wrapper:active {
    cursor: grabbing;
}

.batch-checkbox-wrapper:hover {
    background-color: rgba(59, 130, 246, 0.15);
}

/* 拖拽时禁止文本选择 */
.is-dragging * {
    user-select: none !important;
}

/* 拖拽时选中的组保持高亮 */
.is-dragging .group-node.ring-2 {
    opacity: 0.6;
    background-color: #dbeafe;
}
```

### 5.3 自定义滚动条样式

```css
/* 旧项目 style.css - 规则树专用滚动条 */

/* 滚动条容器 */
.custom-scrollbar-v,
.custom-scrollbar-h {
    position: absolute;
    z-index: 10;
    touch-action: none;
}

/* 垂直滚动条 - 左侧 */
.custom-scrollbar-v {
    left: 0;
    top: 0;
    bottom: 0;
    width: 20px;
}

/* 水平滚动条 - 上方 */
.custom-scrollbar-h {
    top: -20px;
    left: 20px;
    right: 0;
    height: 20px;
}

/* 滚动条轨道 */
.scrollbar-track {
    position: absolute;
    background: #e2e8f0;
    border-radius: 2px;
}

/* 滚动条滑块 */
.scrollbar-thumb {
    position: absolute;
    background-color: #64748b;
    border-radius: 10px;
    box-shadow: 0 0 4px rgba(0,0,0,0.25);
    cursor: grab;
    touch-action: none;
    z-index: 1;
}

.scrollbar-thumb:hover {
    background-color: #475569;
    box-shadow: 0 0 6px rgba(0,0,0,0.35);
}

.scrollbar-thumb:active,
.scrollbar-thumb.dragging {
    background-color: #334155;
    cursor: grabbing;
}
```

---

## 六、noUiSlider 滑块样式

```css
/* 旧项目 style.css - 标签数量筛选滑块 */

/* 滑块轨道 */
#tag-slider {
    height: 8px;
    background: #e2e8f0;
    border-radius: 4px;
    border: none;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);
}

/* 滑块连接条（两个手柄之间的部分） */
#tag-slider .noUi-connect {
    background: linear-gradient(to right, #06b6d4, #0891b2);
    border-radius: 4px;
}

/* 滑块手柄 */
#tag-slider .noUi-handle {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: white;
    border: 2px solid #06b6d4;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    cursor: grab;
    top: -5px;
    right: -9px;
}

#tag-slider .noUi-handle:hover {
    border-color: #0891b2;
    box-shadow: 0 2px 8px rgba(6, 182, 212, 0.4);
}

#tag-slider .noUi-handle:active {
    cursor: grabbing;
    border-color: #0e7490;
    transform: scale(1.1);
}

/* 移除默认的手柄装饰线 */
#tag-slider .noUi-handle::before,
#tag-slider .noUi-handle::after {
    display: none;
}

/* 滑块聚焦样式 */
#tag-slider .noUi-handle:focus {
    outline: none;
    box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.3);
}

/* 标签数量面板过渡动画 */
#tag-count-panel {
    animation: slideIn 0.2s ease-out;
}

@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateY(-10px) scale(0.95);
    }
    to {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}
```

---

## 七、面板位置配置

### 7.1 临时标签面板

| 配置项 | 值 | Tailwind Class |
|--------|-----|----------------|
| 位置 | `fixed top-24 right-44` | `fixed top-24 right-44` |
| 宽度 | `256px` | `w-64` |
| z-index | `40` | `z-40` |
| 圆角 | `12px` | `rounded-xl` |
| 阴影 | `shadow-2xl` | `shadow-2xl` |
| 变换原点 | `top-right` | `origin-top-right` |

### 7.2 标签数量筛选面板

| 配置项 | 值 | Tailwind Class |
|--------|-----|----------------|
| 位置 | `fixed top-24 right-44` | `fixed top-24 right-44` |
| 宽度 | `208px` | `w-52` |
| z-index | `40` | `z-40` |
| 圆角 | `12px` | `rounded-xl` |
| 阴影 | `shadow-2xl` | `shadow-2xl` |
| 变换原点 | `top-right` | `origin-top-right` |

### 7.3 排序菜单

| 配置项 | 值 | Tailwind Class |
|--------|-----|----------------|
| 位置 | `fixed top-24 right-44` | `fixed top-24 right-44` |
| 宽度 | `160px` | `w-40` |
| z-index | `40` | `z-40` |
| 圆角 | `12px` | `rounded-xl` |
| 阴影 | `shadow-xl` | `shadow-xl` |
| 变换原点 | `top-right` | `origin-top-right` |

**排序选项：**

| data-sort | 图标 | 文本 |
|-----------|------|------|
| `date_desc` | 📅 | 最新添加 |
| `date_asc` | 📅 | 最早添加 |
| `size_desc` | 💾 | 文件很大 |
| `size_asc` | 💾 | 文件很小 |
| `resolution_desc` | 📐 | 高分辨率 |
| `resolution_asc` | 📐 | 低分辨率 |

---

## 八、功能函数对照表

### 8.1 TagInput 类

| 旧项目方法 | 新项目位置 | 功能描述 |
|-----------|-----------|----------|
| `constructor(options)` | `TagInput.vue setup` | 初始化标签输入组件 |
| `bindEvents()` | `TagInput.vue onMounted` | 绑定输入框事件 |
| `addTag(text)` | `addTag(text)` | 添加标签（支持排除和同义词） |
| `removeTag(index)` | `removeTag(index)` | 删除指定索引的标签 |
| `editTag(index)` | `editTag(index)` | 编辑指定索引的标签 |
| `getStyle(isExclude, isSynonym)` | `getTagClass(tag)` | 获取标签样式类名 |
| `render()` | Vue 响应式渲染 | 渲染所有标签胶囊 |
| `setTags(newTags)` | `v-model` | 设置新的标签数组 |
| `focus()` | `focus()` | 聚焦输入框 |
| `clear()` | `clear()` | 清空所有标签 |

### 8.2 GlobalState 类

| 旧项目属性/方法 | 新项目位置 | 功能描述 |
|----------------|-----------|----------|
| `clientId` | `useGlobalStore.clientId` | 客户端唯一ID |
| `rulesBaseVersion` | `useGlobalStore.rulesVersion` | 规则树版本号 |
| `rulesTree` | `RuleTree.vue groups` | 规则树数据 |
| `expandedGroupIds` | `RuleTree.vue expandedIds` | 已展开的组ID集合 |
| `isExpansionEnabled` | `Gallery.vue isExpansionEnabled` | 同义词膨胀开关 |
| `isFabCollapsed` | `useGlobalStore.fabCollapsed` | FAB折叠状态 |
| `fabMiniTopPosition` | `FloatingButtons.vue miniStripTop` | FAB迷你位置 |
| `loadFabCollapsedState()` | `useGlobalStore` | 加载FAB折叠状态 |
| `saveFabCollapsedState()` | `useGlobalStore` | 保存FAB折叠状态 |
| `loadExpansionState()` | `useGlobalStore` | 加载膨胀状态 |
| `saveExpansionState()` | `useGlobalStore` | 保存膨胀状态 |
| `loadExpandedState()` | `RuleTree.vue` | 加载展开状态 |
| `saveExpandedState()` | `RuleTree.vue` | 保存展开状态 |

### 8.3 MemeApp 类

| 旧项目方法 | 新项目位置 | 功能描述 |
|-----------|-----------|----------|
| `doSearch()` | `Gallery.vue handleSearch()` | 执行搜索 |
| `resetSearch()` | `Gallery.vue resetSearch()` | 重置搜索 |
| `loadMore()` | `Gallery.vue loadMore()` | 加载更多 |
| `renderMemeCard(item)` | `MemeCard.vue` | 渲染图片卡片 |
| `copyImage(md5, ext)` | `MemeCard.vue handleCopy()` | 复制图片 |
| `deleteImage(md5)` | `MemeCard.vue handleDelete()` | 删除图片 |
| `uploadFiles(files)` | `UploadModal.vue startUpload()` | 上传文件 |
| `exportAllData()` | `Gallery.vue handleExport()` | 导出数据 |
| `importData(json)` | `Gallery.vue handleImport()` | 导入数据 |
| `toggleFabCollapsed()` | `FloatingButtons.vue toggleCollapsed()` | 切换FAB折叠 |
| `toggleExpansionMode()` | `Gallery.vue toggleExpansion()` | 切换膨胀模式 |
| `toggleRulesPanel()` | `Gallery.vue toggleRulesPanel()` | 切换规则树面板 |
| `toggleTempTagMode()` | `FloatingButtons.vue` | 切换临时标签模式 |

---

## 九、API 端点对照表

### 9.1 图片相关 API

| 方法 | 旧项目端点 | 新项目端点 | 请求体 |
|------|-----------|-----------|--------|
| POST | `/api/search` | `/api/search` | `{offset, limit, sort_by, keywords, excludes, ...}` |
| POST | `/api/upload` | `/api/images` | FormData |
| POST | `/api/update_tags` | `PUT /api/images/{id}/tags` | `{tags, client_id, base_version}` |
| POST | `/api/check_md5` | `GET /api/images/check-md5/{md5}` | - |
| GET | `/api/meta/tags` | `/api/meta/tags` | - |

### 9.2 规则树相关 API

| 方法 | 旧项目端点 | 新项目端点 | 说明 |
|------|-----------|-----------|------|
| GET | `/api/rules` | `/api/rules` | 获取规则树（支持ETag） |
| POST | `/api/rules/groups` | `/api/rules/groups` | 创建规则组 |
| PUT | `/api/rules/groups/{id}` | `/api/rules/groups/{id}` | 更新规则组 |
| DELETE | `/api/rules/groups/{id}` | `/api/rules/groups/{id}` | 删除规则组 |
| POST | `/api/rules/keywords` | `/api/rules/groups/{id}/keywords` | 添加关键词 |
| DELETE | `/api/rules/keywords/{id}` | `/api/rules/keywords/{id}` | 删除关键词 |
| PUT | `/api/rules/keywords/{id}` | `/api/rules/keywords/{id}` | 更新关键词状态 |

### 9.3 系统相关 API

| 方法 | 旧项目端点 | 新项目端点 | 说明 |
|------|-----------|-----------|------|
| GET | `/api/export/all` | `/api/export` | 导出所有数据 |
| POST | `/api/import/all` | `/api/import` | 导入数据 |
| GET | - | `/api/version` | 获取规则版本 |
| GET | - | `/api/stats` | 获取系统统计 |

---

## 十、SVG 图标配置

### 10.1 预定义图标（旧项目 script.js）

```javascript
const SVG_ICONS = {
    download: `<svg>...</svg>`,  // 下载图标
    copy: `<svg>...</svg>`,      // 剪贴板堆叠图标
    trash: `<svg>...</svg>`,     // 垃圾桶图标
    refresh: `<svg>...</svg>`,   // 刷新图标
    loader: `<svg>...</svg>`,    // 旋转沙漏（加载中）
    check: `<svg>...</svg>`,     // 勾选图标
    alert: `<svg>...</svg>`,     // 警告三角形
};
```

### 10.2 新项目使用 Lucide Vue

```typescript
import {
    Download, Upload, Copy, Trash2, RefreshCw,
    Loader2, Check, AlertTriangle, Search, X,
    ChevronRight, ChevronDown, ChevronLeft,
    ChevronsRight, ChevronsLeft,
    Folder, FolderOpen, Tag, Hash,
    ArrowUpDown, ImagePlus, TreePine, Stamp,
    FileText, GripVertical, Plus, Minus,
    CheckCircle, XCircle, Info, AlertCircle
} from 'lucide-vue-next';
```

---

## 十一、事件处理对照表

### 11.1 FAB 按钮事件

| 按钮 | 旧项目事件 | 新项目事件 |
|------|-----------|-----------|
| fab-search | `headerTagInput.focus()` + `scrollTo(0)` | `emit('search')` |
| clear-search-btn | `headerTagInput.clear()` + `doSearch()` | `emit('clear')` |
| fab-hq | 切换 `preferHQ` + `resetSearch()` | `emit('toggleHQ')` |
| fab-sort | 切换 `sortMenu` 显示 | `showSortMenu = !showSortMenu` |
| fab-trash | 添加/移除 `trash_bin` 标签 | `emit('toggleTrash')` |
| fab-temp-tags | 切换 `isTempTagMode` | 切换 `showTempTagsPanel` |
| fab-tag-count | 切换 `tagCountPanel` 显示 | `showTagCountPanel = !showTagCountPanel` |
| fab-tree | `toggleExpansionMode()` | `emit('toggleExpansion')` |
| fab-upload | `fileInput.click()` | `emit('upload')` |
| fab-export | `exportAllData()` | `emit('export')` |
| fab-import | `jsonInput.click()` | `emit('import')` |
| fab-toggle-btn | `toggleFabCollapsed()` | `toggleCollapsed()` |

### 11.2 规则树事件

| 元素 | 旧项目事件 | 新项目事件 |
|------|-----------|-----------|
| rules-panel-toggle-btn | `toggleRulesPanel()` | `emit('toggle')` |
| rules-tree-search | `filterRulesTree(value)` | `searchText` 响应式过滤 |
| batch-mode-btn | `toggleBatchMode()` | `batchEditMode = !batchEditMode` |
| expand-all-btn | `expandAllGroups()` | `expandAll()` |
| collapse-all-btn | `collapseAllGroups()` | `collapseAll()` |
| add-root-group-btn | `showAddGroupDialog()` | `showRootInput = true` |
| refresh-rules-btn | `refreshRulesTree()` | `loadRules(true)` |

---

## 十二、迁移检查清单

### 12.1 视觉样式检查

- [x] FAB 按钮组位置和布局 ✅ 2026-01-30
- [x] FAB 按钮颜色和图标 ✅ 2026-01-30
- [x] FAB 卫星按钮位置和样式 ✅ 2026-01-30
- [x] FAB 迷你按钮条样式 ✅ 2026-01-30
- [x] 搜索栏样式 ✅ 2026-01-30
- [x] 图片网格响应式列数 ✅ 2026-01-30
- [x] 图片卡片样式 ✅ 2026-01-30
- [x] 覆盖层标签样式 ✅ 2026-01-30
- [x] 回收站样式 ✅ 2026-01-30
- [x] 规则树侧边栏样式 ✅ 2026-01-30
- [ ] 拖拽放置区样式 (待验证)
- [x] 标签胶囊样式和动画 ✅ 2026-01-30
- [ ] noUiSlider 滑块样式 (待验证)
- [ ] 面板位置和样式 (待验证)

### 12.2 功能检查

- [x] 标签输入（空格分割、同义词组、排除标签） ✅
- [ ] 搜索功能（关键词膨胀） (待验证)
- [ ] 图片上传（MD5 检查、预览） (待验证)
- [ ] 图片复制/删除 (待验证)
- [ ] 规则树 CRUD (待验证)
- [ ] 规则树拖拽排序 (待验证)
- [ ] 批量编辑模式 (待验证)
- [ ] 临时标签粘贴 (待验证)
- [ ] 标签数量筛选 (待验证)
- [ ] 排序功能 (待验证)
- [ ] HQ 模式 (待验证)
- [ ] 回收站模式 (待验证)
- [ ] 导入/导出 (待验证)
- [ ] FAB 折叠/展开 (待验证)
- [ ] FAB 迷你条拖拽 (待验证)

---

## 十三、组件文件对照表

| 旧项目文件 | 新项目文件 | 说明 |
|-----------|-----------|------|
| `index.html` | `App.vue` + `Gallery.vue` | 主页面结构 |
| `script.js` (TagInput) | `TagInput.vue` | 标签输入组件 |
| `script.js` (GlobalState) | `useGlobalStore.ts` | 全局状态管理 |
| `script.js` (MemeApp) | `Gallery.vue` + 各组件 | 主应用逻辑 |
| `style.css` | `style.css` | 全局样式 |
| - | `FloatingButtons.vue` | FAB 按钮组 |
| - | `MemeCard.vue` | 图片卡片 |
| - | `RuleTree.vue` | 规则树面板 |
| - | `RuleGroupNode.vue` | 规则组节点 |
| - | `UploadModal.vue` | 上传模态框 |
| - | `ImageEditModal.vue` | 编辑模态框 |
| - | `ImagePreview.vue` | 图片预览 |
| - | `ToastContainer.vue` | Toast 通知 |
| - | `useApi.ts` | API 封装 |
| - | `useToast.ts` | Toast 通知 |
| - | `useOptimisticUpdate.ts` | 乐观更新 |

---

## 十四、迁移进度记录

> 最后更新: 2026-01-30

### 14.1 已完成的样式迁移

| 组件/文件 | 状态 | 修改内容 |
|-----------|------|----------|
| `style.css` | ✅ 完成 | 标签动画 `cubic-bezier`、回收站 `8px dashed` 边框、加载失败灰度样式、覆盖层标签文字阴影 |
| `FloatingButtons.vue` | ✅ 完成 | FAB 按钮白色背景+边框样式、上传按钮翠绿填充、图标大小调整 |
| `MemeCard.vue` | ✅ 完成 | 卡片圆角 `rounded-xl`、背景色 `bg-white`、标签使用全局 `.overlay-tag` 样式 |
| `TagInput.vue` | ✅ 完成 | 容器 `rounded-xl`、最小高度 `50px`、聚焦 `ring-2`、标签 `font-bold`、删除按钮 `&times;` |
| `RuleTree.vue` | ✅ 完成 | 已符合旧项目规范，无需修改 |
| `RuleGroupNode.vue` | ✅ 完成 | 已符合旧项目规范（`rounded-[10px]`、子节点 `border-l-2`） |
| `Gallery.vue` | ✅ 完成 | 搜索栏 `z-30`、搜索按钮 `rounded-xl`、加载指示器 `border-4` |

### 14.2 待验证功能

- [ ] FAB 按钮组完整功能测试
- [ ] 规则树拖拽排序
- [ ] 批量编辑模式
- [ ] 临时标签粘贴
- [ ] 标签数量筛选滑块
- [ ] 导入/导出功能
- [ ] 图片预览导航

---

## 追加更新（2026-01-30）
- [x] FAB 浮动按钮：完成 noUiSlider 标签数筛选、临时标签面板、扩展名筛选按钮及迷你条拖拽位置持久化，样式与旧版一致。
- [x] 临时标签模式：Gallery.vue + MemeCard.vue 支持 FAB 批量打标模式、单卡片点击即时应用、HQ/回收站逻辑同步。
- [x] 样式补充：style.css 新增 `temp-mode-card`/`temp-mode-pill`，与旧项目一致的视觉提示。
- [x] 表单与工具：UploadModal.vue 改为 ref 触发文件选择、useOptimisticUpdate.ts 精简泛型、TagInput.vue/RuleTree.vue 修复 TS 报错。
- [ ] 待验证：拖拽排序区块、规则树拖拽、上传/导出流程将在下一轮联调时补测。

