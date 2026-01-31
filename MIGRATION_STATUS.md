# BQBQ v2 迁移状态文档



> 最后更新: 2026-01-31

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



- [x] FAB 按钮组位置和布局 ✅ 2026-01-31

- [x] FAB 按钮颜色和图标 ✅ 2026-01-31

- [x] FAB 卫星按钮位置和样式 ✅ 2026-01-31

- [x] FAB 迷你按钮条样式 ✅ 2026-01-31

- [x] 搜索栏样式 ✅ 2026-01-31

- [x] 图片网格响应式列数 ✅ 2026-01-31

- [x] 图片卡片样式 ✅ 2026-01-31

- [x] 覆盖层标签样式 ✅ 2026-01-31

- [x] 回收站样式 ✅ 2026-01-31

- [x] 规则树侧边栏样式 ✅ 2026-01-31

- [x] 拖拽放置区样式 ✅ 2026-01-31

- [x] 标签胶囊样式和动画 ✅ 2026-01-31

- [x] noUiSlider 滑块样式 ✅ 2026-01-31

- [x] 面板位置和样式 ✅ 2026-01-31



### 12.2 功能检查



- [x] 标签输入（空格分割、同义词组、排除标签） ✅

- [x] 搜索功能（关键词膨胀） ✅ 2026-01-31

- [x] 图片上传（MD5 检查、预览） ✅ 2026-01-31

- [x] 图片复制/删除 ✅ 2026-01-31

- [x] 规则树 CRUD ✅ 2026-01-31

- [x] 规则树拖拽排序 ✅ 2026-01-31

- [x] 批量编辑模式 ✅ 2026-01-31

- [x] 临时标签粘贴 ✅ 2026-01-31

- [x] 标签数量筛选 ✅ 2026-01-31

- [x] 排序功能 ✅ 2026-01-31

- [x] HQ 模式 ✅ 2026-01-31

- [x] 回收站模式 ✅ 2026-01-31

- [x] 导入/导出 ✅ 2026-01-31

- [x] FAB 折叠/展开 ✅ 2026-01-31

- [x] FAB 迷你条拖拽 ✅ 2026-01-31



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



> 最后更新: 2026-01-31



### 14.1 已完成的样式迁移



| 组件/文件 | 状态 | 修改内容 |

|-----------|------|----------|

| `style.css` | ✅ 完成 | 标签动画 `cubic-bezier`、回收站 `8px dashed` 边框、加载失败灰度样式、覆盖层标签文字阴影 |

| `FloatingButtons.vue` | ✅ 完成 | FAB 按钮白色背景+边框样式、上传按钮翠绿填充、图标大小调整 |

| `MemeCard.vue` | ✅ 完成 | 卡片圆角 `rounded-xl`、背景色 `bg-white`、标签使用全局 `.overlay-tag` 样式 |

| `TagInput.vue` | ✅ 完成 | 容器 `rounded-xl`、最小高度 `50px`、聚焦 `ring-2`、标签 `font-bold`、删除按钮 `&times;` |

| `RuleTree.vue` | ✅ 完成 | 补齐 drop-gap/根目录放置区、批量拖拽视觉、冲突检测区块、自定义滚动条与中文文案 |

| `RuleGroupNode.vue` | ✅ 完成 | 已符合旧项目规范（`rounded-[10px]`、子节点 `border-l-2`） |

| `Gallery.vue` | ✅ 完成 | 搜索栏 `z-30`、搜索按钮 `rounded-xl`、加载指示器 `border-4` |



### 14.2 功能验证完成



- [x] FAB 按钮组完整功能 ✅ 2026-01-31

- [x] 规则树拖拽排序 ✅ 2026-01-31

- [x] 批量编辑模式 ✅ 2026-01-31

- [x] 临时标签粘贴 ✅ 2026-01-31

- [x] 标签数量筛选滑块 ✅ 2026-01-31

- [x] 导入/导出功能 ✅ 2026-01-31

- [x] 图片预览导航 ✅ 2026-01-31


---

## 追加更新（2026-01-30）
- [x] FAB 浮动按钮：完成 noUiSlider 标签数筛选、临时标签面板、扩展名筛选按钮及迷你条拖拽位置持久化，样式与旧版一致。
- [x] 临时标签模式：Gallery.vue + MemeCard.vue 支持 FAB 批量打标模式、单卡片点击即时应用、HQ/回收站逻辑同步。
- [x] 样式补充：style.css 新增 `temp-mode-card`/`temp-mode-pill`，与旧项目一致的视觉提示。
- [x] 表单与工具：UploadModal.vue 改为 ref 触发文件选择、useOptimisticUpdate.ts 精简泛型、TagInput.vue/RuleTree.vue 修复 TS 报错。
- [x] 拖拽排序区块、规则树拖拽、上传/导出流程已验证完成 ✅ 2026-01-31


## 追加更新（2026-01-31）
- [x] DOM ID 对齐：补齐旧版缺失的 FAB/面板/网格/加载等全部 ID。
- [x] 规则接口兼容：补齐 `/api/rules/group/*`、`/api/rules/keyword/*` 旧版路径，并补充 `version_id` 返回字段。
- [x] 规则树：修复中文乱码，补齐根目录放置区/节点间隙 drop-gap、批量拖拽视觉、冲突检测区块与修复按钮，结构与旧版一致。
- [x] 复核循环：已重新执行 5 轮差异分析并更新报告（`MIGRATION_STATUS-轮数1..5.md`），接口/DOM/CSS/指纹已重新计算。
- [x] 样式入口调整：`frontend/src/style.css` 顶部改为 `@import "tailwindcss";`（按当前指示覆盖旧版入口形式）。
- [x] 规则树滚动：自定义滚动条（左侧/上方）+ Pointer Capture 拖拽同步完成。
- [x] 后端兼容：新增 `/api/check_md5`、`/api/update_tags`，`/api/search` 兼容旧版高级搜索负载。
- [x] 编码策略：统一 UTF-8 读写流程，避免中文注释/文本再次乱码。
## 迁移完成总结

**迁移状态：✅ 全部完成**

所有功能已从旧项目成功迁移到新项目：
- 视觉样式：100% 复刻
- 功能逻辑：100% 实现
- API 对接：100% 完成

---

# 附录 A：旧项目完整代码逐行分析

> 以下是旧项目 `C:\000soft\qqpy机器人-git\bqbq_backend-1\精确搜索SQLite端(旧)` 的完整代码分析
> 用于 100% 复刻参考

---

## A1. 常量定义 (script.js:1-45)

### A1.1 缓存与存储键名

```javascript
const CACHE_DURATION = 10 * 60 * 1000;  // 标签缓存有效期：10分钟
const TAGS_CACHE_KEY = 'bqbq_tag_cache';      // localStorage 键：标签缓存
const TAGS_TIME_KEY = 'bqbq_tag_timestamp';   // localStorage 键：缓存时间戳
const RULES_VERSION_KEY = 'bqbq_rules_version'; // localStorage 键：规则树版本号
const CLIENT_ID_KEY = 'bqbq_client_id';       // localStorage 键：客户端唯一ID
const FAB_COLLAPSED_KEY = 'bqbq_fab_collapsed'; // sessionStorage 键：FAB折叠状态
const FAB_MINI_POSITION_KEY = 'bqbq_fab_mini_position'; // sessionStorage 键：FAB迷你位置
```

### A1.2 支持的图片扩展名

```javascript
const SUPPORTED_EXTENSIONS = ['gif', 'png', 'jpg', 'webp'];
```

### A1.3 防抖函数

```javascript
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
```

### A1.4 预定义 SVG 图标

```javascript
const SVG_ICONS = {
    download: `<svg ...>...</svg>`,  // 24x24 下载图标
    copy: `<svg ...>...</svg>`,      // 24x24 剪贴板堆叠图标
    trash: `<svg ...>...</svg>`,     // 24x24 垃圾桶图标（带盖子）
    refresh: `<svg ...>...</svg>`,   // 24x24 刷新箭头图标
    loader: `<svg class="animate-spin-fast">...</svg>`,  // 32x32 旋转沙漏
    check: `<svg ...>...</svg>`,     // 24x24 勾选图标
    alert: `<svg class="w-10 h-10">...</svg>`,  // 40x40 警告三角形
};
```

---

## A2. TagInput 类 (script.js:47-315)

### A2.1 构造函数参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `container` | HTMLElement | 必填 | 容器元素 |
| `initialTags` | Array | `[]` | 初始标签数组 |
| `suggestionsId` | String | `''` | datalist ID |
| `placeholder` | String | `'Add tag...'` | 占位符文本 |
| `onChange` | Function | `() => {}` | 标签变化回调 |
| `onSubmit` | Function | `() => {}` | 提交回调（空回车） |
| `onInputUpdate` | Function | `() => {}` | 输入更新回调 |
| `theme` | String | `'blue'` | 主题：blue/purple/mixed |
| `enableExcludes` | Boolean | `false` | 是否启用排除标签 |
| `autoFocus` | Boolean | `false` | 是否自动聚焦 |

### A2.2 输入框样式

```javascript
this.input.className = "flex-grow min-w-[60px] bg-transparent outline-none " +
                       "text-slate-700 placeholder-slate-400 font-medium h-8 text-sm";
```

### A2.3 事件绑定逻辑

**容器点击**：点击容器空白区域聚焦输入框
```javascript
this.container.onclick = (e) => {
    if (e.target === this.container) this.input.focus();
};
```

**输入事件**：检测空格（半角/全角）自动分割
```javascript
this.input.addEventListener('input', (e) => {
    const val = this.input.value;
    const spaceIndex = val.search(/[ 　]/);  // 半角或全角空格
    if (spaceIndex !== -1) {
        const textBefore = val.substring(0, spaceIndex).trim();
        const textAfter = val.substring(spaceIndex).trim();
        if (textBefore) this.addTag(textBefore);
        this.input.value = textAfter;
        this.input.focus();
    }
    this.onInputUpdate(this.input.value);
});
```

**键盘事件**：
- `Enter`：有内容则添加标签，无内容则触发提交
- `Backspace`：输入框为空时编辑最后一个标签

```javascript
this.input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        const val = this.input.value.trim();
        if (val) {
            e.preventDefault();
            this.addTag(val);
            this.input.value = '';
        } else {
            e.preventDefault();
            this.onSubmit(this.tags);
        }
    } else if (e.key === 'Backspace' && !this.input.value && this.tags.length > 0) {
        e.preventDefault();
        this.editTag(this.tags.length - 1);
    }
});
```

### A2.4 addTag 方法逻辑

1. **排除标签检测**：以 `-` 开头且长度 > 1
2. **同义词组检测**：包含 `,` 或 `，`
3. **去重检查**：比较 text + exclude + synonym
4. **标签对象结构**：
```javascript
{
    text: "标签文本",
    exclude: false,      // 是否排除
    synonym: false,      // 是否同义词组
    synonymWords: null   // 同义词数组（如 ["猫", "喵", "cat"]）
}
```

### A2.5 标签样式映射

| 条件 | CSS 类名 |
|------|----------|
| `exclude && synonym` | `bg-orange-100 text-orange-700 border-orange-300 hover:bg-orange-200` |
| `exclude` | `bg-red-100 text-red-600 border-red-200 hover:bg-red-200` |
| `synonym` | `bg-green-100 text-green-600 border-green-200 hover:bg-green-200` |
| `theme === 'purple'` | `bg-purple-100 text-purple-700 border-purple-200 hover:bg-purple-200` |
| 默认 (blue) | `bg-blue-100 text-blue-600 border-blue-200 hover:bg-blue-200` |

### A2.6 render 方法

```javascript
render() {
    this.container.innerHTML = '';
    this.tags.forEach((tag, idx) => {
        const capsule = document.createElement('div');
        capsule.className = `tag-capsule flex items-center gap-1 px-3 py-1
            rounded-full text-sm font-bold cursor-pointer select-none
            transition-transform active:scale-95 ${this.getStyle(...)} max-w-full break-all`;

        // 文本部分（点击编辑）
        const spanText = document.createElement('span');
        spanText.textContent = (isExclude ? '-' : '') + text;
        spanText.onclick = (e) => { e.stopPropagation(); this.editTag(idx); };

        // 删除按钮
        const spanDel = document.createElement('span');
        spanDel.innerHTML = '&times;';
        spanDel.className = "ml-1 hover:text-black/50 text-lg leading-none px-1 " +
                           "rounded-full hover:bg-black/5 transition-colors";
        spanDel.onclick = (e) => { e.stopPropagation(); this.removeTag(idx); };

        capsule.appendChild(spanText);
        capsule.appendChild(spanDel);
        this.container.appendChild(capsule);
    });
    this.container.appendChild(this.input);
    this.input.placeholder = this.tags.length > 0 ? '' : this.placeholder;
}
```

### A2.7 同义词组 title 提示

```javascript
if (isSynonym) {
    if (isExclude) {
        capsule.title = `交集排除: 同时包含 [${tag.synonymWords.join(' 且 ')}] 的图片才会被排除`;
    } else {
        capsule.title = `同义词组: ${tag.synonymWords.join(' | ')}`;
    }
}
```

---

## A3. GlobalState 类 (script.js:317-535)

### A3.1 规则同步与并发控制状态

| 属性 | 类型 | 初始值 | 说明 |
|------|------|--------|------|
| `clientId` | String | 随机生成 | 客户端唯一标识（存 localStorage） |
| `rulesBaseVersion` | Number | 0 | 本地规则版本号 |
| `rulesTree` | Array/null | null | 解析后的规则树结构 |
| `conflictNodes` | Array | [] | 冲突节点列表 |
| `conflictRelations` | Array | [] | 冲突关系列表 |
| `pendingRulesRender` | Timeout/null | null | 防抖渲染定时器 |
| `rulesRenderDebounceMs` | Number | 300 | 防抖延迟毫秒 |

### A3.2 图片搜索与数据加载状态

| 属性 | 类型 | 初始值 | 说明 |
|------|------|--------|------|
| `offset` | Number | 0 | 分页偏移量 |
| `limit` | Number | 40 | 每页数量 |
| `loading` | Boolean | false | 加载中标志 |
| `hasMore` | Boolean | true | 是否有更多数据 |
| `totalItems` | Number | 0 | 总数量 |
| `queryTags` | Array | [] | 当前搜索标签 |
| `isTrashMode` | Boolean | false | 回收站模式 |
| `allKnownTags` | Array | [] | 所有已知标签（用于建议） |

### A3.3 设置与偏好

| 属性 | 类型 | 初始值 | 存储位置 |
|------|------|--------|----------|
| `sortBy` | String | 'date_desc' | 内存 |
| `preferHQ` | Boolean | localStorage | localStorage('bqbq_prefer_hq') |

### A3.4 临时标签面板状态

| 属性 | 类型 | 初始值 | 说明 |
|------|------|--------|------|
| `tempTags` | Array | [] | 临时标签列表 |
| `isTempTagMode` | Boolean | false | 批量打标模式开关 |

### A3.5 标签数量筛选状态

| 属性 | 类型 | 初始值 | 说明 |
|------|------|--------|------|
| `minTags` | Number | 0 | 最小标签数 |
| `maxTags` | Number | -1 | 最大标签数（-1=无限制） |
| `isTagCountPanelOpen` | Boolean | false | 面板开关状态 |

### A3.6 批量编辑状态

| 属性 | 类型 | 初始值 | 说明 |
|------|------|--------|------|
| `batchEditMode` | Boolean | false | 批量编辑模式 |
| `selectedGroupIds` | Set | new Set() | 已选中的组ID |

### A3.7 规则树展开状态

| 属性 | 类型 | 初始值 | 存储位置 |
|------|------|--------|----------|
| `expandedGroupIds` | Set | sessionStorage | sessionStorage('bqbq_tree_expanded') |
| `isTreeDefaultExpanded` | Boolean | true | 首次加载标记 |

### A3.8 同义词膨胀功能

| 属性 | 类型 | 初始值 | 存储位置 |
|------|------|--------|----------|
| `isExpansionEnabled` | Boolean | true | sessionStorage('bqbq_expansion_enabled') |

### A3.9 FAB 悬浮按钮状态

| 属性 | 类型 | 初始值 | 存储位置 |
|------|------|--------|----------|
| `isFabCollapsed` | Boolean | true | sessionStorage(FAB_COLLAPSED_KEY) |
| `fabMiniTopPosition` | Number/null | null | sessionStorage(FAB_MINI_POSITION_KEY) |

### A3.10 辅助方法

```javascript
// 生成或获取客户端ID
getOrGenerateClientId() {
    let id = localStorage.getItem(CLIENT_ID_KEY);
    if (!id) {
        id = Math.random().toString(36).substring(2, 15) +
             Math.random().toString(36).substring(2, 15);
        localStorage.setItem(CLIENT_ID_KEY, id);
    }
    return id;
}

// 加载/保存 FAB 迷你位置
loadFabMiniPosition() { /* 从 sessionStorage 读取 */ }
saveFabMiniPosition() { /* 保存到 sessionStorage */ }

// 加载/保存 FAB 折叠状态
loadFabCollapsedState() { /* 默认 true（折叠） */ }
saveFabCollapsedState() { /* 保存到 sessionStorage */ }

// 加载/保存膨胀功能状态
loadExpansionState() { /* 默认 true（开启） */ }
saveExpansionState() { /* 保存到 sessionStorage */ }

// 加载/保存展开状态
loadExpandedState() { /* 返回 Set */ }
saveExpandedState() { /* 保存 JSON 数组 */ }

// 初始化默认展开状态（首次加载展开所有）
initDefaultExpandState(rulesTree) {
    if (sessionStorage.getItem('bqbq_tree_expanded') !== null) return;
    // 递归收集所有节点ID并展开
}
```

---

## A4. MemeApp 类 (script.js:537-4924)

### A4.1 DOM 元素引用

```javascript
this.dom = {
    // 主要容器
    grid: document.getElementById('meme-grid'),
    headerSearchBar: document.getElementById('header-search-bar'),
    tempTagInputContainer: document.getElementById('temp-tag-input-container'),

    // FAB 按钮
    fabSearch: document.getElementById('fab-search'),
    fabUpload: document.getElementById('fab-upload'),
    fabHQ: document.getElementById('fab-hq'),
    fabSort: document.getElementById('fab-sort'),
    fabTrash: document.getElementById('fab-trash'),
    fabTemp: document.getElementById('fab-temp-tags'),
    fabTempSlash: document.getElementById('fab-temp-tags-slash'),
    toggleTempPanelBtn: document.getElementById('toggle-temp-panel-btn'),
    fabTagCount: document.getElementById('fab-tag-count'),
    btnClearSearch: document.getElementById('clear-search-btn'),

    // 指示器和面板
    hqDot: document.getElementById('hq-status-dot'),
    trashDot: document.getElementById('trash-active-dot'),
    sortMenu: document.getElementById('sort-menu'),
    tempPanel: document.getElementById('temp-tag-panel'),
    tagCountPanel: document.getElementById('tag-count-panel'),

    // 文件输入
    fileInput: document.getElementById('file-upload'),
    btnReload: document.getElementById('reload-search-btn'),

    // 加载指示器
    loader: document.getElementById('loading-indicator'),
    end: document.getElementById('end-indicator'),

    // 规则树相关
    fabTree: document.getElementById('fab-tree'),
    rulesPanel: document.getElementById('rules-tree-panel'),
    rulesTreeContainer: document.getElementById('rules-tree-container'),
    rulesPanelToggleBtn: document.getElementById('rules-panel-toggle-btn'),

    // FAB 折叠相关
    fabContainer: document.getElementById('fab-container'),
    fabMiniStrip: document.getElementById('fab-mini-strip'),
    fabToggleBtn: document.getElementById('fab-toggle-btn'),
    fabExpandBtn: document.getElementById('fab-expand-btn'),
    fabMiniClear: document.getElementById('fab-mini-clear'),
    fabMiniReload: document.getElementById('fab-mini-reload'),
    fabMiniSearch: document.getElementById('fab-mini-search'),
};
```

### A4.2 init 方法（初始化流程）

```javascript
async init() {
    this.initTagInputs();           // 1. 初始化标签输入组件
    this.updateHQVisuals();         // 2. 更新HQ视觉状态
    this.bindEvents();              // 3. 绑定所有事件
    this.updateFabCollapsedVisuals(); // 4. 初始化FAB折叠状态
    this.initFabMiniPosition();     // 5. 初始化FAB迷你位置
    this.initFabMiniDrag();         // 6. 初始化FAB迷你拖拽
    this.initRulesTreeHScrollSync(); // 7. 初始化规则树滚动条
    await this.loadRulesTree();     // 8. 加载规则树（先于图片）
    await this.loadMeta();          // 9. 加载标签元数据
    this.loadMore();                // 10. 加载第一页图片
}
```

### A4.3 buildTree 方法（构建规则树）

**输入数据结构**：
```javascript
{
    groups: [{ group_id, group_name, is_enabled }],
    keywords: [{ keyword, group_id, is_enabled }],
    hierarchy: [{ parent_id, child_id }]
}
```

**输出数据结构**：
```javascript
{
    rootNodes: [{
        id: Number,
        name: String,
        isEnabled: Boolean,
        keywords: [{ text: String, isEnabled: Boolean }],
        children: [/* 递归子节点 */],
        parentIds: [Number],
        isConflict: Boolean,
        conflictReason: String|null
    }],
    conflictNodes: [/* 冲突节点 */],
    conflictRelations: [/* 冲突关系 */]
}
```

**冲突检测**：
1. 孤儿关系：父或子节点不存在
2. 自引用：parent_id === child_id
3. 循环依赖：child 是 parent 的祖先

### A4.4 expandSingleKeyword 方法（关键词膨胀）

```javascript
expandSingleKeyword(inputText) {
    if (!this.state.isExpansionEnabled) return [inputText];
    if (!this.state.rulesTree) return [inputText];

    const uniqueKeywords = new Set([inputText]);

    // 递归收集组及其子组的同义词
    const recursivelyCollectKeywords = (node) => {
        if (!node.isEnabled) return;
        node.keywords.filter(k => k.isEnabled).forEach(k => uniqueKeywords.add(k.text));
        node.children.forEach(recursivelyCollectKeywords);
    };

    // 遍历规则树匹配
    const traverseAndMatch = (nodes) => {
        nodes.forEach(node => {
            if (!node.isEnabled) return;
            // 1. 命中组名
            if (node.name === inputText) {
                recursivelyCollectKeywords(node);
                return;
            }
            // 2. 命中同义词
            if (node.keywords.find(k => k.text === inputText && k.isEnabled)) {
                recursivelyCollectKeywords(node);
                return;
            }
            // 3. 递归子节点
            traverseAndMatch(node.children);
        });
    };

    traverseAndMatch(this.state.rulesTree);
    return Array.from(uniqueKeywords);
}
```

### A4.5 handleSave 方法（乐观锁保存）

```javascript
async handleSave(action, payload, retryCount = 0) {
    const MAX_RETRIES = 3;
    if (retryCount >= MAX_RETRIES) {
        this.showToast('保存失败：冲突次数过多', 'error');
        await this.loadRulesTree(true);
        return { success: false, error: 'max_retries_exceeded' };
    }

    // 1. 乐观更新本地状态
    this.updateRulesTreeOptimistically(action.type, payload);
    this.renderRulesTree();

    try {
        const response = await fetch(action.url, {
            method: action.method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                ...payload,
                base_version: this.state.rulesBaseVersion,
                client_id: this.state.clientId
            })
        });

        if (response.status === 409) {
            // 冲突处理：更新基准数据，检查有效性，自动重放
            const conflictData = await response.json();
            this.state.rulesBaseVersion = conflictData.latest_data.version_id;
            // ... 重建本地树，检查操作有效性，递归重试
        }

        if (response.ok) {
            const result = await response.json();
            this.state.rulesBaseVersion = result.version_id;
            await this.loadRulesTree(true);
            return { success: true, version_id: result.version_id };
        }
    } catch (e) {
        this.showToast('保存失败：网络错误', 'error');
        return { success: false, error: e.message };
    }
}
```

### A4.6 filterAndUpdateDatalist 方法（标签建议过滤）

```javascript
filterAndUpdateDatalist(currentInput) {
    const dl = document.getElementById('tag-suggestions');
    const MAX_SUGGESTIONS = 4;

    // 检测排除标签前缀
    const isExclude = currentInput.startsWith('-');
    const prefix = isExclude ? '-' : '';
    const searchText = isExclude ? currentInput.slice(1) : currentInput;

    // 扩展名建议（以 . 开头）
    if (searchText.startsWith('.')) {
        const partialExt = searchText.slice(1).toLowerCase();
        const suggestions = SUPPORTED_EXTENSIONS
            .filter(ext => ext.startsWith(partialExt))
            .map(ext => `${prefix}.${ext}`);
        dl.innerHTML = suggestions.map(t => `<option value="${t}">`).join('');
        return;
    }

    // 普通标签过滤（不区分大小写，包含匹配）
    const filtered = this.state.allKnownTags
        .filter(tag => tag.toLowerCase().includes(searchText.toLowerCase()))
        .slice(0, MAX_SUGGESTIONS);

    dl.innerHTML = filtered.map(t => `<option value="${prefix}${t}">`).join('');
}
```

### A4.7 initTagInputs 方法

```javascript
initTagInputs() {
    // 1. 头部搜索栏
    this.headerTagInput = new TagInput({
        container: this.dom.headerSearchBar,
        suggestionsId: 'tag-suggestions',
        placeholder: '输入关键词 (空格生成胶囊)...',
        theme: 'mixed',
        enableExcludes: true,
        onChange: (tags) => {
            this.state.queryTags = tags;
            // 自动检测 trash_bin 标签
            const hasTrash = tags.some(t => t.text === 'trash_bin' && !t.exclude);
            if (this.state.isTrashMode !== hasTrash) {
                this.state.isTrashMode = hasTrash;
                this.updateTrashVisuals();
            }
        },
        onSubmit: () => this.doSearch(),
        onInputUpdate: (val) => this.filterAndUpdateDatalist(val)
    });

    // 2. 临时标签面板
    this.tempTagInput = new TagInput({
        container: this.dom.tempTagInputContainer,
        suggestionsId: 'tag-suggestions',
        placeholder: '输入临时标签...',
        theme: 'purple',
        enableExcludes: false,
        onChange: (tags) => { this.state.tempTags = tags; },
        onInputUpdate: (val) => this.filterAndUpdateDatalist(val)
    });
}
```

### A4.8 bindEvents 方法（事件绑定）

**FAB 按钮事件**：
```javascript
// 搜索按钮
this.dom.fabSearch.onclick = () => {
    this.headerTagInput.focus();
    window.scrollTo({ top: 0, behavior: 'smooth' });
};

// 清空搜索
this.dom.btnClearSearch.onclick = (e) => {
    e.stopPropagation();
    this.headerTagInput.clear();
    this.state.queryTags = [];
    this.state.isTrashMode = false;
    this.updateTrashVisuals();
    this.doSearch();
};

// HQ 模式切换
this.dom.fabHQ.onclick = () => {
    this.state.preferHQ = !this.state.preferHQ;
    localStorage.setItem('bqbq_prefer_hq', this.state.preferHQ);
    this.updateHQVisuals();
    this.resetSearch();
};

// 排序菜单
this.dom.fabSort.onclick = (e) => {
    e.stopPropagation();
    this.dom.sortMenu.classList.toggle('hidden');
    this.dom.sortMenu.classList.toggle('flex');
};

// 回收站切换
this.dom.fabTrash.onclick = () => {
    const hasTrash = this.state.queryTags.some(t => t.text === 'trash_bin');
    if (hasTrash) {
        const idx = this.state.queryTags.findIndex(t => t.text === 'trash_bin');
        if (idx !== -1) this.headerTagInput.removeTag(idx);
    } else {
        this.headerTagInput.addTag('trash_bin');
    }
    this.doSearch();
};

// 临时标签模式
this.dom.fabTemp.onclick = () => {
    this.state.isTempTagMode = !this.state.isTempTagMode;
    this.updateTempTagModeVisuals();
    const statusText = this.state.isTempTagMode ? '已进入批量打标模式' : '已退出批量打标模式';
    this.showToast(statusText, this.state.isTempTagMode ? 'success' : 'info');
};

// 膨胀功能切换
this.dom.fabTree.onclick = () => {
    this.toggleExpansionMode();
};
```

**无限滚动**：
```javascript
this.dom.grid.parentElement.addEventListener('scroll', () => {
    const el = this.dom.grid.parentElement;
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 200) {
        this.loadMore();
    }
});
```

**事件委托（图片网格）**：
```javascript
this.dom.grid.addEventListener('click', (e) => {
    const cardEl = e.target.closest('.meme-card');
    if (!cardEl) return;

    const md5 = cardEl.dataset.md5;
    const imgEl = cardEl.querySelector('.image-element');
    const tagsContainer = cardEl.querySelector('.tags-container-element');
    const infoEl = JSON.parse(cardEl.dataset.info || '{}');

    // A. 图片点击（加载原图或应用临时标签）
    if (e.target.classList.contains('image-element') || e.target.closest('.error-overlay')) {
        if (this.state.isTempTagMode) {
            this.applyTempTags(infoEl, cardEl, tagsContainer);
            return;
        }
        // 加载原图
        const originalSrc = imgEl.dataset.original;
        if (originalSrc && imgEl.src !== originalSrc) {
            this.loadOriginalImage(originalSrc, imgEl, cardEl);
        }
    }

    // B. 标签区域点击（编辑模式）
    if (e.target.closest('.tags-container-element')) {
        this.startOverlayEdit(tempImgData, cardEl, overlay, tagsContainer);
    }

    // C. 复制按钮
    if (e.target.closest('.copy-btn')) {
        const currentTags = Array.from(tagsContainer.querySelectorAll('.overlay-tag'))
            .map(el => el.textContent);
        this.copyText(currentTags.join(' '), btnCopy);
    }

    // D. 删除/恢复按钮
    if (e.target.closest('.delete-btn')) {
        this.toggleTrash(tempImgData, cardEl, deleteBtn, e);
    }
});
```

### A4.9 视觉更新方法

**updateHQVisuals**：
```javascript
updateHQVisuals() {
    if (this.state.preferHQ) {
        this.dom.hqDot.classList.remove('bg-slate-300');
        this.dom.hqDot.classList.add('bg-blue-600');
        this.dom.fabHQ.classList.add('text-blue-600', 'border-blue-200');
    } else {
        this.dom.hqDot.classList.add('bg-slate-300');
        this.dom.hqDot.classList.remove('bg-blue-600');
        this.dom.fabHQ.classList.remove('text-blue-600', 'border-blue-200');
    }
}
```

**updateTrashVisuals**：
```javascript
updateTrashVisuals() {
    if (this.state.isTrashMode) {
        this.dom.fabTrash.classList.add('text-red-500', 'bg-red-50', 'border-red-200');
        this.dom.trashDot.classList.remove('hidden');
        this.dom.grid.classList.add('trash-mode-active');
    } else {
        this.dom.fabTrash.classList.remove('text-red-500', 'bg-red-50', 'border-red-200');
        this.dom.trashDot.classList.add('hidden');
        this.dom.grid.classList.remove('trash-mode-active');
    }
}
```

**updateExpansionButtonVisuals**：
```javascript
updateExpansionButtonVisuals() {
    const slashEl = document.getElementById('fab-tree-slash');
    if (this.state.isExpansionEnabled) {
        // 开启：绿色高亮
        this.dom.fabTree.classList.add('bg-green-100', 'border-green-400', 'text-green-700');
        this.dom.fabTree.classList.remove('bg-white', 'border-yellow-300', 'text-yellow-600');
        this.dom.fabTree.title = '同义词膨胀：已开启（点击关闭）';
        if (slashEl) slashEl.classList.add('hidden');
    } else {
        // 关闭：白色背景+黄色图标+红色斜杠
        this.dom.fabTree.classList.remove('bg-green-100', 'border-green-400', 'text-green-700');
        this.dom.fabTree.classList.add('bg-white', 'border-yellow-300', 'text-yellow-600');
        this.dom.fabTree.title = '同义词膨胀：已关闭（点击开启）';
        if (slashEl) slashEl.classList.remove('hidden');
    }
}
```

**updateTempTagModeVisuals**：
```javascript
updateTempTagModeVisuals() {
    const slashEl = this.dom.fabTempSlash;
    if (this.state.isTempTagMode) {
        // 开启：紫色高亮
        this.dom.fabTemp.classList.add('bg-purple-100', 'border-purple-400', 'text-purple-700');
        this.dom.fabTemp.classList.remove('bg-white', 'border-purple-100', 'text-purple-600');
        this.dom.fabTemp.title = '批量打标粘贴模式：已开启（点击关闭）';
        if (slashEl) slashEl.classList.add('hidden');
    } else {
        // 关闭：白色背景+紫色图标+红色斜杠
        this.dom.fabTemp.classList.remove('bg-purple-100', 'border-purple-400', 'text-purple-700');
        this.dom.fabTemp.classList.add('bg-white', 'border-purple-100', 'text-purple-600');
        this.dom.fabTemp.title = '批量打标粘贴模式：已关闭（点击开启）';
        if (slashEl) slashEl.classList.remove('hidden');
    }
}
```

**updateFabCollapsedVisuals**：
```javascript
updateFabCollapsedVisuals() {
    if (this.state.isFabCollapsed) {
        this.dom.fabContainer.classList.add('hidden');
        this.dom.fabMiniStrip.classList.remove('hidden');
    } else {
        this.dom.fabContainer.classList.remove('hidden');
        this.dom.fabMiniStrip.classList.add('hidden');
    }
}
```

### A4.10 FAB 迷你拖拽功能

```javascript
initFabMiniDrag() {
    const expandBtn = this.dom.fabExpandBtn;
    const miniStrip = this.dom.fabMiniStrip;

    let isDragging = false;
    let hasMoved = false;
    let startY = 0;
    let startTop = 0;
    const DRAG_THRESHOLD = 5;

    const handlePointerDown = (e) => {
        isDragging = true;
        hasMoved = false;
        startY = e.clientY || e.touches?.[0].clientY;
        startTop = miniStrip.getBoundingClientRect().top;
        e.preventDefault();
    };

    const handlePointerMove = (e) => {
        if (!isDragging) return;
        const clientY = e.clientY || e.touches?.[0].clientY;
        const deltaY = clientY - startY;
        if (Math.abs(deltaY) > DRAG_THRESHOLD) hasMoved = true;
        if (!hasMoved) return;

        let newTop = startTop + deltaY;
        const minTop = 80;
        const maxTop = window.innerHeight - miniStrip.offsetHeight - 16;
        newTop = Math.max(minTop, Math.min(maxTop, newTop));
        miniStrip.style.top = `${newTop}px`;
    };

    const handlePointerUp = (e) => {
        if (!isDragging) return;
        isDragging = false;
        if (hasMoved) {
            // 保存位置
            this.state.fabMiniTopPosition = Math.round(miniStrip.getBoundingClientRect().top);
            this.state.saveFabMiniPosition();
        } else {
            // 点击展开
            this.toggleFabCollapsed();
        }
    };

    // 绑定鼠标和触摸事件
    expandBtn.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('mousemove', handlePointerMove);
    document.addEventListener('mouseup', handlePointerUp);
    expandBtn.addEventListener('touchstart', handlePointerDown, { passive: false });
    document.addEventListener('touchmove', handlePointerMove, { passive: true });
    document.addEventListener('touchend', handlePointerUp);
}
```

### A4.11 规则树滚动条同步

```javascript
initRulesTreeHScrollSync() {
    const wrapper = document.getElementById('rules-tree-scroll-wrapper');
    const content = document.getElementById('rules-tree-content');
    const container = document.getElementById('rules-tree-container');

    // 创建自定义滚动条
    const vScrollbar = document.createElement('div');
    vScrollbar.className = 'custom-scrollbar-v';
    vScrollbar.innerHTML = '<div class="scrollbar-track"></div><div class="scrollbar-thumb"></div>';

    const hScrollbar = document.createElement('div');
    hScrollbar.className = 'custom-scrollbar-h';
    hScrollbar.innerHTML = '<div class="scrollbar-track"></div><div class="scrollbar-thumb"></div>';

    // 更新滑块位置和大小
    const updateScrollbars = () => {
        // 垂直滚动条
        const contentHeight = container.scrollHeight;
        const viewportHeight = content.clientHeight;
        if (contentHeight > viewportHeight) {
            vScrollbar.style.display = 'block';
            const thumbHeight = Math.max(30, (viewportHeight / contentHeight) * trackHeight);
            // ... 计算位置
        }
        // 水平滚动条类似
    };

    // Pointer Capture 拖拽逻辑
    const setupDrag = (thumb, scrollbar, isVertical) => {
        thumb.addEventListener('pointerdown', (e) => {
            thumb.setPointerCapture(e.pointerId);
            // ...
        });
        thumb.addEventListener('pointermove', (e) => {
            if (!thumb.hasPointerCapture(e.pointerId)) return;
            // ... 计算滚动位置
        });
    };
}
```

### A4.12 标签数量筛选滑块

```javascript
initTagCountSlider() {
    const sliderEl = document.getElementById('tag-slider');
    const inputMin = document.getElementById('input-min-tags');
    const inputMax = document.getElementById('input-max-tags');
    const display = document.getElementById('tag-count-display');
    const badge = document.getElementById('tag-count-badge');
    const SLIDER_MAX_VAL = 6;

    // 创建 noUiSlider
    noUiSlider.create(sliderEl, {
        start: [0, SLIDER_MAX_VAL],
        connect: true,
        step: 1,
        range: { 'min': 0, 'max': SLIDER_MAX_VAL }
    });

    const debouncedSearch = debounce(() => this.resetSearch(), 300);

    // 更新显示和徽章
    const updateDisplay = () => {
        const minText = this.state.minTags;
        const maxText = (this.state.maxTags === -1) ? '∞' : this.state.maxTags;
        display.textContent = `${minText} - ${maxText}`;

        if (this.state.minTags === 0 && this.state.maxTags === -1) {
            badge.classList.add('hidden');
            this.dom.fabTagCount.classList.remove('bg-cyan-100', 'border-cyan-300');
        } else {
            badge.textContent = `${minText}-${maxText}`;
            badge.classList.remove('hidden');
            this.dom.fabTagCount.classList.add('bg-cyan-100', 'border-cyan-300');
        }
    };

    // 滑块事件
    sliderEl.noUiSlider.on('update', (values, handle) => { /* 更新状态 */ });
    sliderEl.noUiSlider.on('change', () => debouncedSearch());

    // 输入框事件
    inputMin.onchange = () => { /* 更新 minTags */ };
    inputMax.onchange = () => { /* 更新 maxTags，支持 ∞ */ };
}
```

### A4.13 loadMeta 方法（加载标签元数据）

```javascript
async loadMeta() {
    let tags = [];
    const cachedData = localStorage.getItem(TAGS_CACHE_KEY);
    const cachedTime = localStorage.getItem(TAGS_TIME_KEY);
    const now = new Date().getTime();

    // 1. 检查缓存有效性
    if (cachedData && cachedTime && (now - parseInt(cachedTime) < CACHE_DURATION)) {
        tags = JSON.parse(cachedData);
        console.log("Tags loaded from localStorage cache.");
    } else {
        // 2. 从 API 拉取
        tags = await this.fetchTagsFromApi();
        if (tags.length > 0) {
            localStorage.setItem(TAGS_CACHE_KEY, JSON.stringify(tags));
            localStorage.setItem(TAGS_TIME_KEY, now.toString());
        }
    }

    // 3. 合并规则树关键词
    const rulesKeywords = new Set();
    if (this.state.rulesTree) {
        const collectKeywords = (nodes) => {
            nodes.forEach(group => {
                rulesKeywords.add(group.name);
                group.keywords.forEach(kw => rulesKeywords.add(kw.text));
                collectKeywords(group.children);
            });
        };
        collectKeywords(this.state.rulesTree);
    }

    // 4. 合并去重
    this.state.allKnownTags = Array.from(new Set([...tags, ...rulesKeywords]));
    this.filterAndUpdateDatalist('');
}

async fetchTagsFromApi() {
    try {
        return await fetch('/api/meta/tags').then(r => r.json());
    } catch(e) {
        console.error("Meta load failed", e);
        return [];
    }
}
```

### A4.14 loadMore 方法（搜索与分页）

```javascript
async loadMore(isJump = false) {
    if (this.state.loading || (!this.state.hasMore && !isJump)) return;
    this.state.loading = true;
    this.dom.loader.classList.remove('hidden');

    // 辅助函数：判断扩展名标签
    const isExtensionTag = (text) => {
        if (!text.startsWith('.')) return false;
        return SUPPORTED_EXTENSIONS.includes(text.slice(1).toLowerCase());
    };

    // 分离标签类型
    const extensionIncludes = this.state.queryTags
        .filter(t => !t.exclude && !t.synonym && isExtensionTag(t.text))
        .map(t => t.text.slice(1).toLowerCase());

    const extensionExcludes = this.state.queryTags
        .filter(t => t.exclude && !t.synonym && isExtensionTag(t.text))
        .map(t => t.text.slice(1).toLowerCase());

    const normalIncludes = this.state.queryTags
        .filter(t => !t.exclude && !t.synonym && !isExtensionTag(t.text))
        .map(t => t.text);

    const synonymIncludes = this.state.queryTags.filter(t => !t.exclude && t.synonym);
    const normalExcludes = this.state.queryTags
        .filter(t => t.exclude && !t.synonym && !isExtensionTag(t.text))
        .map(t => t.text);
    const synonymExcludes = this.state.queryTags.filter(t => t.exclude && t.synonym);

    // 膨胀普通包含标签（二维数组）
    const expandedNormalIncludes = this.expandKeywordsToGroups(normalIncludes);

    // 同义词组包含标签：每个词膨胀后合并为一个OR组
    const synonymIncludeGroups = synonymIncludes.map(t => {
        const expandedWords = t.synonymWords.flatMap(word => this.expandSingleKeyword(word));
        return [...new Set(expandedWords)];
    });

    // 合并包含标签
    const expandedIncludesGroups = [...expandedNormalIncludes, ...synonymIncludeGroups];

    // 膨胀排除标签
    const expandedNormalExcludes = this.expandKeywordsToGroups(normalExcludes);

    // 同义词组排除标签（交集排除）：三维数组
    const synonymExcludeAndGroups = synonymExcludes.map(t => {
        return t.synonymWords.map(word => {
            const expanded = this.expandSingleKeyword(word);
            return [...new Set(expanded)];
        });
    });

    const payload = {
        offset: this.state.offset,
        limit: this.state.limit,
        sort_by: this.state.sortBy,
        keywords: expandedIncludesGroups,      // 二维数组
        excludes: expandedNormalExcludes,      // 二维数组（OR排除）
        excludes_and: synonymExcludeAndGroups, // 三维数组（交集排除）
        extensions: extensionIncludes,
        exclude_extensions: extensionExcludes,
        min_tags: this.state.minTags,
        max_tags: this.state.maxTags
    };

    try {
        const res = await fetch('/api/search', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        }).then(r => r.json());

        this.state.totalItems = res.total;
        if (res.results.length < this.state.limit) {
            this.state.hasMore = false;
            this.dom.end.classList.remove('hidden');
        }
        this.renderPageBlock(res.results);
        this.state.offset += res.results.length;
    } finally {
        this.state.loading = false;
        this.dom.loader.classList.add('hidden');
    }
}
```

### A4.15 renderPageBlock 方法（渲染图片卡片）

```javascript
renderPageBlock(items) {
    items.forEach(item => {
        const card = this.createMemeCard(item);
        this.dom.grid.appendChild(card);
    });
}
```

### A4.16 createMemeCard 方法（创建图片卡片）

```javascript
createMemeCard(imgData) {
    const card = document.createElement('div');
    card.className = 'meme-card relative rounded-xl overflow-hidden bg-white shadow-md ' +
                     'hover:shadow-lg transition-shadow cursor-pointer group';
    card.dataset.md5 = imgData.md5;
    card.dataset.info = JSON.stringify(imgData);

    // 回收站样式
    if (imgData.is_trash) {
        card.classList.add('is-trash');
    }

    // 图片容器
    const imgContainer = document.createElement('div');
    imgContainer.className = 'relative aspect-square';

    // 图片元素
    const img = document.createElement('img');
    img.className = 'image-element w-full h-full object-cover';
    img.src = this.state.preferHQ
        ? `/images/${imgData.md5}.${imgData.ext}`
        : `/thumbnails/${imgData.md5}.webp`;
    img.dataset.original = `/images/${imgData.md5}.${imgData.ext}`;
    img.loading = 'lazy';

    // 加载指示器
    const loader = document.createElement('div');
    loader.className = 'loader-element hidden absolute inset-0 flex items-center ' +
                       'justify-center bg-black/30 z-10';
    loader.innerHTML = SVG_ICONS.loader;

    // 覆盖层
    const overlay = document.createElement('div');
    overlay.className = 'image-overlay absolute inset-0 flex flex-col justify-end p-2';

    // 标签容器
    const tagsContainer = document.createElement('div');
    tagsContainer.className = 'tags-container-element flex flex-wrap gap-1';

    // 渲染标签
    imgData.tags.forEach(tag => {
        const tagEl = document.createElement('span');
        tagEl.className = 'overlay-tag px-2 py-0.5 rounded-full text-xs text-white';
        tagEl.textContent = tag;
        tagsContainer.appendChild(tagEl);
    });

    // 操作按钮
    const btnContainer = document.createElement('div');
    btnContainer.className = 'absolute top-2 right-2 flex gap-1 opacity-0 ' +
                             'group-hover:opacity-100 transition-opacity';

    // 复制按钮
    const copyBtn = document.createElement('button');
    copyBtn.className = 'copy-btn p-1.5 rounded-lg bg-white/80 hover:bg-white ' +
                        'text-slate-600 hover:text-blue-600 transition-colors';
    copyBtn.innerHTML = SVG_ICONS.copy;

    // 删除按钮
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'delete-btn p-1.5 rounded-lg bg-white/80 hover:bg-white ' +
                          'text-slate-600 hover:text-red-600 transition-colors';
    deleteBtn.innerHTML = imgData.is_trash ? SVG_ICONS.refresh : SVG_ICONS.trash;

    btnContainer.appendChild(copyBtn);
    btnContainer.appendChild(deleteBtn);

    overlay.appendChild(tagsContainer);
    imgContainer.appendChild(img);
    imgContainer.appendChild(loader);
    imgContainer.appendChild(overlay);
    imgContainer.appendChild(btnContainer);
    card.appendChild(imgContainer);

    return card;
}
```

### A4.17 loadOriginalImage 方法（加载原图）

```javascript
loadOriginalImage(originalSrc, imgEl, cardEl) {
    // 移除错误覆盖层
    const existingError = cardEl.querySelector('.error-overlay');
    if (existingError) existingError.remove();

    // 显示加载器
    const loader = cardEl.querySelector('.loader-element');
    if (loader) loader.classList.remove('hidden');

    const tempImg = new Image();

    tempImg.onload = () => {
        imgEl.src = originalSrc;
        if (loader) loader.classList.add('hidden');
        imgEl.classList.remove('opacity-50', 'grayscale');
        cardEl.classList.remove('load-failed');
    };

    tempImg.onerror = () => {
        if (loader) loader.classList.add('hidden');
        imgEl.classList.add('opacity-50', 'grayscale');
        cardEl.classList.add('load-failed');

        // 插入错误覆盖层
        const errorOverlay = document.createElement('div');
        errorOverlay.className = 'error-overlay absolute inset-0 text-red-500 ' +
                                 'flex flex-col items-center justify-center z-20 cursor-pointer';
        errorOverlay.innerHTML = SVG_ICONS.alert;
        cardEl.appendChild(errorOverlay);
    };

    tempImg.src = originalSrc;
}
```

### A4.18 handleUpload 方法（文件上传）

```javascript
async handleUpload(files) {
    if (files.length === 0) return;

    const btn = this.dom.fabUpload;
    const originalContent = btn.innerHTML;
    btn.innerHTML = `<i data-lucide="loader-2" class="animate-spin w-7 h-7"></i>`;
    lucide.createIcons();

    try {
        for (let file of files) {
            // 1. 计算 MD5
            const md5 = await this.calculateMD5(file);

            // 2. 检查是否已存在
            const checkResult = await this.checkMD5Exists(md5, true);
            if (checkResult.exists) {
                if (checkResult.time_refreshed) {
                    this.showToast(`图片已存在：${file.name}（已更新时间戳）`, 'info');
                } else {
                    this.showToast(`图片已存在：${file.name}`, 'info');
                }
                continue;
            }

            // 3. 上传新文件
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.success) {
                this.showToast(`上传成功：${file.name}`, 'success');
            } else {
                this.showToast(`上传失败：${result.error}`, 'error');
            }
        }
        this.resetSearch();
    } finally {
        btn.innerHTML = originalContent;
        lucide.createIcons();
    }
}
```

### A4.19 calculateMD5 方法

```javascript
async calculateMD5(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        const spark = new SparkMD5.ArrayBuffer();

        reader.onload = (e) => {
            spark.append(e.target.result);
            resolve(spark.end());
        };

        reader.onerror = () => reject(new Error('文件读取失败'));
        reader.readAsArrayBuffer(file);
    });
}
```

### A4.20 checkMD5Exists 方法

```javascript
async checkMD5Exists(md5, refreshTime = false) {
    const response = await fetch('/api/check_md5', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ md5, refresh_time: refreshTime })
    });
    return await response.json();
}
```

### A4.21 导入导出方法

```javascript
async exportAllData() {
    try {
        const response = await fetch('/api/export/all');
        const data = await response.json();

        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `bqbq_export_${new Date().toISOString().slice(0,10)}.json`;
        a.click();
        URL.revokeObjectURL(url);

        this.showToast('导出成功！', 'success');
    } catch (error) {
        this.showToast(`导出失败：${error.message}`, 'error');
    }
}

async importAllData(file) {
    try {
        const fileContent = await file.text();
        const data = JSON.parse(fileContent);

        const response = await fetch('/api/import/all', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        if (result.success) {
            this.showToast(
                `导入成功！新增 ${result.imported_images} 张，跳过 ${result.skipped_images} 张`,
                'success'
            );
            await this.loadRulesTree(true);
            this.resetSearch();
        } else {
            this.showToast(`导入失败：${result.error}`, 'error');
        }
    } catch (error) {
        this.showToast(`导入失败：${error.message}`, 'error');
    }
}
```

---

## A5. 后端 API (app.py) 完整分析

### A5.1 Flask 应用配置

```python
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import hashlib
from PIL import Image
from datetime import datetime

app = Flask(__name__)
CORS(app)

# 配置
UPLOAD_FOLDER = 'images'
THUMBNAIL_FOLDER = 'thumbnails'
DATABASE = 'meme.db'
THUMBNAIL_SIZE = (200, 200)
```

### A5.2 数据库表结构

```sql
-- 图片表
CREATE TABLE IF NOT EXISTS images (
    md5 TEXT PRIMARY KEY,
    ext TEXT NOT NULL,
    tags TEXT DEFAULT '',
    is_trash INTEGER DEFAULT 0,
    upload_time TEXT,
    file_size INTEGER,
    width INTEGER,
    height INTEGER
);

-- 规则组表
CREATE TABLE IF NOT EXISTS rule_groups (
    group_id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_name TEXT NOT NULL,
    is_enabled INTEGER DEFAULT 1,
    sort_order INTEGER DEFAULT 0
);

-- 关键词表
CREATE TABLE IF NOT EXISTS rule_keywords (
    keyword_id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    keyword TEXT NOT NULL,
    is_enabled INTEGER DEFAULT 1,
    FOREIGN KEY (group_id) REFERENCES rule_groups(group_id)
);

-- 层级关系表
CREATE TABLE IF NOT EXISTS rule_hierarchy (
    parent_id INTEGER NOT NULL,
    child_id INTEGER NOT NULL,
    PRIMARY KEY (parent_id, child_id),
    FOREIGN KEY (parent_id) REFERENCES rule_groups(group_id),
    FOREIGN KEY (child_id) REFERENCES rule_groups(group_id)
);

-- 版本表
CREATE TABLE IF NOT EXISTS rule_versions (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT,
    modified_at TEXT
);
```

### A5.3 API 端点详细说明

#### 图片上传 `/api/upload` (POST)

```python
@app.route('/api/upload', methods=['POST'])
def upload_image():
    file = request.files.get('file')
    if not file:
        return jsonify({'success': False, 'error': '没有文件'})

    # 读取文件内容计算 MD5
    content = file.read()
    md5 = hashlib.md5(content).hexdigest()
    file.seek(0)

    # 检查是否已存在
    conn = get_db()
    existing = conn.execute('SELECT md5 FROM images WHERE md5 = ?', (md5,)).fetchone()
    if existing:
        return jsonify({'success': False, 'error': '图片已存在', 'md5': md5})

    # 保存原图
    ext = file.filename.rsplit('.', 1)[-1].lower()
    filepath = os.path.join(UPLOAD_FOLDER, f'{md5}.{ext}')
    file.save(filepath)

    # 生成缩略图
    img = Image.open(filepath)
    img.thumbnail(THUMBNAIL_SIZE)
    thumb_path = os.path.join(THUMBNAIL_FOLDER, f'{md5}.webp')
    img.save(thumb_path, 'WEBP', quality=80)

    # 获取图片信息
    width, height = img.size
    file_size = os.path.getsize(filepath)

    # 插入数据库
    conn.execute('''
        INSERT INTO images (md5, ext, tags, upload_time, file_size, width, height)
        VALUES (?, ?, '', ?, ?, ?, ?)
    ''', (md5, ext, datetime.now().isoformat(), file_size, width, height))
    conn.commit()

    return jsonify({'success': True, 'md5': md5, 'msg': '上传成功'})
```

#### MD5 检查 `/api/check_md5` (POST)

```python
@app.route('/api/check_md5', methods=['POST'])
def check_md5():
    data = request.json
    md5 = data.get('md5')
    refresh_time = data.get('refresh_time', False)

    conn = get_db()
    row = conn.execute('SELECT md5 FROM images WHERE md5 = ?', (md5,)).fetchone()

    if row:
        time_refreshed = False
        if refresh_time:
            conn.execute('UPDATE images SET upload_time = ? WHERE md5 = ?',
                        (datetime.now().isoformat(), md5))
            conn.commit()
            time_refreshed = True
        return jsonify({'exists': True, 'time_refreshed': time_refreshed})

    return jsonify({'exists': False})
```

#### 搜索 `/api/search` (POST)

```python
@app.route('/api/search', methods=['POST'])
def search_images():
    data = request.json
    offset = data.get('offset', 0)
    limit = data.get('limit', 40)
    sort_by = data.get('sort_by', 'date_desc')
    keywords = data.get('keywords', [])        # 二维数组
    excludes = data.get('excludes', [])        # 二维数组
    excludes_and = data.get('excludes_and', []) # 三维数组
    extensions = data.get('extensions', [])
    exclude_extensions = data.get('exclude_extensions', [])
    min_tags = data.get('min_tags', 0)
    max_tags = data.get('max_tags', -1)

    # 构建 SQL 查询
    sql = 'SELECT * FROM images WHERE 1=1'
    params = []

    # 包含关键词（AND 关系，每组内 OR）
    for group in keywords:
        if group:
            placeholders = ' OR '.join(['tags LIKE ?' for _ in group])
            sql += f' AND ({placeholders})'
            params.extend([f'%{kw}%' for kw in group])

    # 排除关键词（OR 排除）
    for group in excludes:
        if group:
            placeholders = ' OR '.join(['tags LIKE ?' for _ in group])
            sql += f' AND NOT ({placeholders})'
            params.extend([f'%{kw}%' for kw in group])

    # 交集排除（AND 排除）
    for capsule in excludes_and:
        if capsule:
            conditions = []
            for group in capsule:
                if group:
                    placeholders = ' OR '.join(['tags LIKE ?' for _ in group])
                    conditions.append(f'({placeholders})')
                    params.extend([f'%{kw}%' for kw in group])
            if conditions:
                sql += f' AND NOT ({" AND ".join(conditions)})'

    # 扩展名筛选
    if extensions:
        placeholders = ','.join(['?' for _ in extensions])
        sql += f' AND ext IN ({placeholders})'
        params.extend(extensions)

    if exclude_extensions:
        placeholders = ','.join(['?' for _ in exclude_extensions])
        sql += f' AND ext NOT IN ({placeholders})'
        params.extend(exclude_extensions)

    # 标签数量筛选
    if min_tags > 0:
        sql += ' AND (LENGTH(tags) - LENGTH(REPLACE(tags, " ", "")) + 1) >= ?'
        params.append(min_tags)

    if max_tags >= 0:
        sql += ' AND (LENGTH(tags) - LENGTH(REPLACE(tags, " ", "")) + 1) <= ?'
        params.append(max_tags)

    # 排序
    sort_map = {
        'date_desc': 'upload_time DESC',
        'date_asc': 'upload_time ASC',
        'size_desc': 'file_size DESC',
        'size_asc': 'file_size ASC',
        'resolution_desc': 'width * height DESC',
        'resolution_asc': 'width * height ASC'
    }
    sql += f' ORDER BY {sort_map.get(sort_by, "upload_time DESC")}'
    sql += ' LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    conn = get_db()
    rows = conn.execute(sql, params).fetchall()

    # 获取总数
    count_sql = sql.replace('SELECT *', 'SELECT COUNT(*)').split('ORDER BY')[0]
    total = conn.execute(count_sql, params[:-2]).fetchone()[0]

    results = [{
        'md5': row['md5'],
        'ext': row['ext'],
        'tags': row['tags'].split() if row['tags'] else [],
        'is_trash': bool(row['is_trash']),
        'upload_time': row['upload_time'],
        'file_size': row['file_size'],
        'width': row['width'],
        'height': row['height']
    } for row in rows]

    return jsonify({'results': results, 'total': total})
```

#### 更新标签 `/api/update_tags` (POST)

```python
@app.route('/api/update_tags', methods=['POST'])
def update_tags():
    data = request.json
    md5 = data.get('md5')
    tags = data.get('tags', [])
    is_trash = data.get('is_trash', False)

    conn = get_db()
    conn.execute('''
        UPDATE images SET tags = ?, is_trash = ? WHERE md5 = ?
    ''', (' '.join(tags), int(is_trash), md5))
    conn.commit()

    return jsonify({'success': True})
```

#### 获取规则树 `/api/rules` (GET)

```python
@app.route('/api/rules', methods=['GET'])
def get_rules():
    # 支持 ETag 缓存
    etag = request.headers.get('If-None-Match')

    conn = get_db()
    version = conn.execute('SELECT MAX(version_id) FROM rule_versions').fetchone()[0] or 0

    if etag == str(version):
        return '', 304

    groups = conn.execute('SELECT * FROM rule_groups ORDER BY sort_order').fetchall()
    keywords = conn.execute('SELECT * FROM rule_keywords').fetchall()
    hierarchy = conn.execute('SELECT * FROM rule_hierarchy').fetchall()

    response = jsonify({
        'version_id': version,
        'groups': [dict(g) for g in groups],
        'keywords': [dict(k) for k in keywords],
        'hierarchy': [dict(h) for h in hierarchy]
    })
    response.headers['ETag'] = str(version)
    return response
```

#### 规则树写入操作（带乐观锁）

```python
@app.route('/api/rules/groups', methods=['POST'])
def create_group():
    data = request.json
    base_version = data.get('base_version', 0)
    client_id = data.get('client_id', '')
    group_name = data.get('group_name', '')
    parent_id = data.get('parent_id')

    conn = get_db()

    # 检查版本冲突
    current_version = conn.execute('SELECT MAX(version_id) FROM rule_versions').fetchone()[0] or 0
    if base_version < current_version:
        # 返回 409 冲突，附带最新数据
        return get_conflict_response(conn, current_version), 409

    # 创建新组
    cursor = conn.execute('INSERT INTO rule_groups (group_name) VALUES (?)', (group_name,))
    new_id = cursor.lastrowid

    # 如果有父节点，添加层级关系
    if parent_id:
        conn.execute('INSERT INTO rule_hierarchy (parent_id, child_id) VALUES (?, ?)',
                    (parent_id, new_id))

    # 更新版本
    conn.execute('INSERT INTO rule_versions (client_id, modified_at) VALUES (?, ?)',
                (client_id, datetime.now().isoformat()))
    new_version = conn.execute('SELECT MAX(version_id) FROM rule_versions').fetchone()[0]
    conn.commit()

    return jsonify({'success': True, 'version_id': new_version, 'new_id': new_id})
```

#### 导出 `/api/export/all` (GET)

```python
@app.route('/api/export/all', methods=['GET'])
def export_all():
    conn = get_db()

    images = conn.execute('SELECT * FROM images').fetchall()
    groups = conn.execute('SELECT * FROM rule_groups').fetchall()
    keywords = conn.execute('SELECT * FROM rule_keywords').fetchall()
    hierarchy = conn.execute('SELECT * FROM rule_hierarchy').fetchall()

    return jsonify({
        'images': [dict(i) for i in images],
        'rules': {
            'groups': [dict(g) for g in groups],
            'keywords': [dict(k) for k in keywords],
            'hierarchy': [dict(h) for h in hierarchy]
        }
    })
```

#### 导入 `/api/import/all` (POST)

```python
@app.route('/api/import/all', methods=['POST'])
def import_all():
    data = request.json
    conn = get_db()

    imported_images = 0
    skipped_images = 0

    # 导入图片
    for img in data.get('images', []):
        existing = conn.execute('SELECT md5 FROM images WHERE md5 = ?', (img['md5'],)).fetchone()
        if existing:
            skipped_images += 1
            continue

        conn.execute('''
            INSERT INTO images (md5, ext, tags, is_trash, upload_time, file_size, width, height)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (img['md5'], img['ext'], img.get('tags', ''), img.get('is_trash', 0),
              img.get('upload_time'), img.get('file_size'), img.get('width'), img.get('height')))
        imported_images += 1

    # 导入规则（如果有）
    rules = data.get('rules', {})
    # ... 导入 groups, keywords, hierarchy

    conn.commit()
    return jsonify({
        'success': True,
        'imported_images': imported_images,
        'skipped_images': skipped_images
    })
```

---

## A6. HTML 结构详细分析 (index.html)

### A6.1 搜索栏区域

```html
<header class="sticky top-0 z-30 bg-white/90 backdrop-blur-sm border-b border-slate-200 shadow-sm">
    <div class="max-w-7xl mx-auto px-4 py-3">
        <!-- 搜索栏容器 -->
        <div id="header-search-bar"
             class="flex flex-wrap items-center gap-2 px-4 py-2 bg-slate-100
                    rounded-xl border-2 border-transparent
                    focus-within:border-blue-400 focus-within:ring-2
                    focus-within:ring-blue-100 transition-all min-h-[50px]">
            <!-- TagInput 动态渲染标签胶囊和输入框 -->
        </div>

        <!-- 搜索按钮组 -->
        <div class="flex gap-2 mt-2">
            <button id="clear-search-btn"
                    class="px-4 py-2 bg-slate-200 hover:bg-slate-300
                           rounded-xl text-slate-600 transition-colors">
                <i data-lucide="x" class="w-4 h-4"></i>
            </button>
            <button id="reload-search-btn"
                    class="px-4 py-2 bg-blue-500 hover:bg-blue-600
                           rounded-xl text-white transition-colors">
                <i data-lucide="search" class="w-4 h-4 mr-1"></i>
                搜索
            </button>
        </div>
    </div>
</header>
```

### A6.2 图片网格

```html
<main class="max-w-7xl mx-auto px-4 py-6">
    <!-- 响应式网格：2-8列 -->
    <div id="meme-grid"
         class="grid gap-4
                grid-cols-2
                sm:grid-cols-3
                md:grid-cols-4
                lg:grid-cols-5
                xl:grid-cols-6
                2xl:grid-cols-8
                pb-40">
        <!-- MemeCard 动态渲染 -->
    </div>

    <!-- 加载指示器 -->
    <div id="loading-indicator" class="hidden flex justify-center py-8">
        <div class="w-8 h-8 border-4 border-blue-500 border-t-transparent
                    rounded-full animate-spin"></div>
    </div>

    <!-- 结束指示器 -->
    <div id="end-indicator" class="hidden text-center py-8 text-slate-400">
        <i data-lucide="check-circle" class="w-6 h-6 mx-auto mb-2"></i>
        已加载全部
    </div>
</main>
```

### A6.3 FAB 悬浮按钮组

```html
<!-- 主 FAB 容器 -->
<div id="fab-container"
     class="fixed right-4 top-[7rem] z-50 grid grid-cols-2 gap-3">

    <!-- 搜索按钮 -->
    <button id="fab-search"
            class="w-14 h-14 rounded-2xl bg-white border-2 border-slate-200
                   shadow-lg hover:shadow-xl transition-all
                   flex items-center justify-center text-slate-600 hover:text-blue-600">
        <i data-lucide="search" class="w-7 h-7"></i>
    </button>

    <!-- 上传按钮（翠绿填充） -->
    <button id="fab-upload"
            class="w-14 h-14 rounded-2xl bg-emerald-500 hover:bg-emerald-600
                   shadow-lg hover:shadow-xl transition-all
                   flex items-center justify-center text-white">
        <i data-lucide="image-plus" class="w-7 h-7"></i>
    </button>

    <!-- HQ 模式按钮 -->
    <button id="fab-hq"
            class="w-14 h-14 rounded-2xl bg-white border-2 border-slate-200
                   shadow-lg hover:shadow-xl transition-all relative
                   flex items-center justify-center text-slate-600">
        <span class="font-bold text-lg">HQ</span>
        <span id="hq-status-dot"
              class="absolute top-1 right-1 w-3 h-3 rounded-full bg-slate-300"></span>
    </button>

    <!-- 排序按钮 -->
    <button id="fab-sort"
            class="w-14 h-14 rounded-2xl bg-white border-2 border-slate-200
                   shadow-lg hover:shadow-xl transition-all
                   flex items-center justify-center text-slate-600 hover:text-blue-600">
        <i data-lucide="arrow-up-down" class="w-7 h-7"></i>
    </button>

    <!-- 回收站按钮 -->
    <button id="fab-trash"
            class="w-14 h-14 rounded-2xl bg-white border-2 border-slate-200
                   shadow-lg hover:shadow-xl transition-all relative
                   flex items-center justify-center text-slate-600">
        <i data-lucide="trash-2" class="w-7 h-7"></i>
        <span id="trash-active-dot"
              class="hidden absolute top-1 right-1 w-3 h-3 rounded-full bg-red-500"></span>
    </button>

    <!-- 临时标签按钮 -->
    <button id="fab-temp-tags"
            class="w-14 h-14 rounded-2xl bg-white border-2 border-purple-100
                   shadow-lg hover:shadow-xl transition-all relative
                   flex items-center justify-center text-purple-600">
        <i data-lucide="stamp" class="w-7 h-7"></i>
        <!-- 红色斜杠（关闭状态） -->
        <span id="fab-temp-tags-slash"
              class="absolute inset-0 flex items-center justify-center pointer-events-none">
            <span class="w-10 h-0.5 bg-red-500 rotate-45 rounded-full"></span>
        </span>
    </button>

    <!-- 标签数量筛选按钮 -->
    <button id="fab-tag-count"
            class="w-14 h-14 rounded-2xl bg-white border-2 border-slate-200
                   shadow-lg hover:shadow-xl transition-all relative
                   flex items-center justify-center text-cyan-600">
        <i data-lucide="hash" class="w-7 h-7"></i>
        <span id="tag-count-badge"
              class="hidden absolute -top-1 -right-1 px-1.5 py-0.5
                     bg-cyan-500 text-white text-xs rounded-full font-bold"></span>
    </button>

    <!-- 膨胀功能按钮 -->
    <button id="fab-tree"
            class="w-14 h-14 rounded-2xl bg-green-100 border-2 border-green-400
                   shadow-lg hover:shadow-xl transition-all relative
                   flex items-center justify-center text-green-700">
        <i data-lucide="tree-pine" class="w-7 h-7"></i>
        <span id="fab-tree-slash"
              class="hidden absolute inset-0 flex items-center justify-center pointer-events-none">
            <span class="w-10 h-0.5 bg-red-500 rotate-45 rounded-full"></span>
        </span>
        <span id="expansion-badge"
              class="hidden absolute -top-1 -right-1 px-1.5 py-0.5
                     bg-green-500 text-white text-xs rounded-full font-bold"></span>
    </button>

    <!-- 折叠按钮 -->
    <button id="fab-toggle-btn"
            class="col-span-2 h-8 rounded-xl bg-slate-100 hover:bg-slate-200
                   flex items-center justify-center text-slate-400 transition-colors">
        <i data-lucide="chevrons-right" class="w-5 h-5"></i>
    </button>
</div>
```

### A6.4 FAB 迷你按钮条

```html
<div id="fab-mini-strip"
     class="hidden fixed right-0 top-[24rem] z-50
            flex flex-col gap-1 p-1 bg-white/90 backdrop-blur-sm
            rounded-l-xl shadow-lg border border-r-0 border-slate-200">

    <button id="fab-expand-btn"
            class="w-8 h-8 rounded-lg hover:bg-slate-100
                   flex items-center justify-center text-slate-400 cursor-grab">
        <i data-lucide="grip-vertical" class="w-4 h-4"></i>
    </button>

    <button id="fab-mini-clear"
            class="w-8 h-8 rounded-lg hover:bg-slate-100
                   flex items-center justify-center text-slate-500">
        <i data-lucide="x" class="w-4 h-4"></i>
    </button>

    <button id="fab-mini-reload"
            class="w-8 h-8 rounded-lg hover:bg-slate-100
                   flex items-center justify-center text-slate-500">
        <i data-lucide="refresh-cw" class="w-4 h-4"></i>
    </button>

    <button id="fab-mini-search"
            class="w-8 h-8 rounded-lg hover:bg-slate-100
                   flex items-center justify-center text-slate-500">
        <i data-lucide="search" class="w-4 h-4"></i>
    </button>
</div>
```

### A6.5 规则树侧边栏

```html
<aside id="rules-tree-panel"
       class="fixed top-16 left-0 w-72 z-40 -translate-x-full
              transition-transform duration-300 ease-in-out
              bg-white border-r border-slate-200 shadow-xl
              flex flex-col"
       style="height: calc(100vh - 4rem);">

    <!-- 头部工具栏 -->
    <div class="flex-shrink-0 p-3 border-b border-slate-200 bg-slate-50">
        <!-- 搜索框 -->
        <div class="relative mb-2">
            <input id="rules-tree-search" type="text"
                   placeholder="搜索规则..."
                   class="w-full px-3 py-2 pr-8 text-sm border border-slate-300
                          rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400">
            <button id="rules-tree-search-clear"
                    class="hidden absolute right-2 top-1/2 -translate-y-1/2
                           text-slate-400 hover:text-slate-600">
                <i data-lucide="x" class="w-4 h-4"></i>
            </button>
        </div>

        <!-- 工具按钮 -->
        <div class="flex gap-1 flex-wrap">
            <button id="batch-mode-btn" class="px-2 py-1 text-xs rounded bg-slate-200">批量</button>
            <button id="expand-all-btn" class="px-2 py-1 text-xs rounded bg-slate-200">展开</button>
            <button id="collapse-all-btn" class="px-2 py-1 text-xs rounded bg-slate-200">折叠</button>
            <button id="add-root-group-btn" class="px-2 py-1 text-xs rounded bg-blue-500 text-white">+ 新组</button>
            <button id="refresh-rules-btn" class="px-2 py-1 text-xs rounded bg-slate-200">
                <i data-lucide="refresh-cw" class="w-3 h-3"></i>
            </button>
        </div>

        <!-- 版本信息 -->
        <div class="mt-2 text-xs text-slate-400">
            版本: <span id="rules-version-info">v0</span>
        </div>
    </div>

    <!-- 滚动容器 -->
    <div id="rules-tree-scroll-wrapper" class="flex-1 relative overflow-hidden">
        <div id="rules-tree-content" class="absolute inset-0 overflow-auto p-3">
            <div id="rules-tree-container">
                <!-- 规则树节点动态渲染 -->
            </div>
        </div>
    </div>
</aside>

<!-- 侧边栏切换按钮 -->
<button id="rules-panel-toggle-btn"
        class="fixed top-16 left-0 z-50 w-6 h-12
               bg-white border border-l-0 border-slate-200
               rounded-r-lg shadow-md
               flex items-center justify-center text-slate-400
               hover:text-slate-600 hover:bg-slate-50 transition-all"
        style="transition: left 0.3s ease-in-out;">
    <i data-lucide="chevron-right" class="w-4 h-4"></i>
</button>
```

### A6.6 弹出面板

```html
<!-- 临时标签面板 -->
<div id="temp-tag-panel"
     class="hidden fixed top-24 right-44 z-40 w-64
            bg-white rounded-xl shadow-2xl border border-slate-200
            flex flex-col origin-top-right">
    <div class="flex items-center justify-between p-3 border-b border-slate-100">
        <span class="font-bold text-slate-700">临时标签</span>
        <div class="flex gap-1">
            <button id="clear-temp-tags" class="p-1 hover:bg-slate-100 rounded">
                <i data-lucide="trash-2" class="w-4 h-4 text-slate-400"></i>
            </button>
            <button id="close-temp-panel" class="p-1 hover:bg-slate-100 rounded">
                <i data-lucide="x" class="w-4 h-4 text-slate-400"></i>
            </button>
        </div>
    </div>
    <div class="p-3">
        <div id="temp-tag-input-container"
             class="flex flex-wrap items-center gap-2 px-3 py-2
                    bg-purple-50 rounded-xl border-2 border-transparent
                    focus-within:border-purple-400 min-h-[40px]">
        </div>
    </div>
</div>

<!-- 标签数量筛选面板 -->
<div id="tag-count-panel"
     class="hidden fixed top-24 right-44 z-40 w-52
            bg-white rounded-xl shadow-2xl border border-slate-200
            flex flex-col p-4 origin-top-right">
    <div class="flex items-center justify-between mb-3">
        <span class="font-bold text-slate-700">标签数量</span>
        <button id="close-tag-count-panel" class="p-1 hover:bg-slate-100 rounded">
            <i data-lucide="x" class="w-4 h-4 text-slate-400"></i>
        </button>
    </div>
    <div id="tag-slider" class="mb-4"></div>
    <div class="flex gap-2 items-center">
        <input id="input-min-tags" type="number" min="0"
               class="w-16 px-2 py-1 text-center border rounded" value="0">
        <span class="text-slate-400">-</span>
        <input id="input-max-tags" type="text"
               class="w-16 px-2 py-1 text-center border rounded" value="∞">
    </div>
    <div id="tag-count-display" class="mt-2 text-center text-sm text-slate-500">0 - ∞</div>
</div>

<!-- 排序菜单 -->
<div id="sort-menu"
     class="hidden fixed top-24 right-44 z-40 w-40
            bg-white rounded-xl shadow-xl border border-slate-200
            flex flex-col py-2 origin-top-right">
    <button class="sort-option px-4 py-2 text-left hover:bg-slate-100 text-blue-600 font-bold"
            data-sort="date_desc">📅 最新添加</button>
    <button class="sort-option px-4 py-2 text-left hover:bg-slate-100 text-slate-600"
            data-sort="date_asc">📅 最早添加</button>
    <button class="sort-option px-4 py-2 text-left hover:bg-slate-100 text-slate-600"
            data-sort="size_desc">💾 文件很大</button>
    <button class="sort-option px-4 py-2 text-left hover:bg-slate-100 text-slate-600"
            data-sort="size_asc">💾 文件很小</button>
    <button class="sort-option px-4 py-2 text-left hover:bg-slate-100 text-slate-600"
            data-sort="resolution_desc">📐 高分辨率</button>
    <button class="sort-option px-4 py-2 text-left hover:bg-slate-100 text-slate-600"
            data-sort="resolution_asc">📐 低分辨率</button>
</div>
```

---

## A7. CSS 样式完整分析 (style.css)

### A7.1 标签胶囊动画

```css
/* 标签胶囊弹出动画 */
.tag-capsule {
    animation: popIn 0.2s cubic-bezier(0.18, 0.89, 0.32, 1.28);
}

@keyframes popIn {
    0% { transform: scale(0.9); opacity: 0; }
    100% { transform: scale(1); opacity: 1; }
}
```

### A7.2 覆盖层标签样式

```css
/* 图片卡片上的标签样式 */
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

### A7.3 回收站样式

```css
/* 回收站图片样式 */
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

### A7.4 加载失败样式

```css
.load-failed img {
    opacity: 0.3;
    filter: grayscale(100%);
}

.error-overlay {
    background-color: transparent !important;
}
```

### A7.5 图片覆盖层渐变

```css
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

### A7.6 拖拽放置区样式

```css
/* 节点间隙放置区：正常状态 */
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

### A7.7 批量编辑样式

```css
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

### A7.8 自定义滚动条样式

```css
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

### A7.9 noUiSlider 滑块样式

```css
/* 滑块轨道 */
#tag-slider {
    height: 8px;
    background: #e2e8f0;
    border-radius: 4px;
    border: none;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);
}

/* 滑块连接条 */
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

/* 移除默认手柄装饰线 */
#tag-slider .noUi-handle::before,
#tag-slider .noUi-handle::after {
    display: none;
}

/* 滑块聚焦样式 */
#tag-slider .noUi-handle:focus {
    outline: none;
    box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.3);
}
```

### A7.10 面板动画

```css
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

### A7.11 快速旋转动画

```css
/* 沙漏加载动画 */
.animate-spin-fast {
    animation: spin 0.6s linear infinite;
}

@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}
```

### A7.12 临时标签模式样式

```css
/* 临时标签模式下的卡片样式 */
.temp-mode-card {
    cursor: pointer;
    transition: all 0.15s ease;
}

.temp-mode-card:hover {
    box-shadow: 0 0 0 3px #a855f7;
}

/* 临时标签模式下的标签提示 */
.temp-mode-pill {
    position: absolute;
    top: 8px;
    left: 8px;
    padding: 2px 8px;
    background-color: #a855f7;
    color: white;
    font-size: 10px;
    font-weight: bold;
    border-radius: 9999px;
    z-index: 10;
}
```

---

## A8. 关键尺寸与位置汇总

### A8.1 FAB 按钮尺寸

| 元素 | 尺寸 | Tailwind |
|------|------|----------|
| 主按钮 | 56x56px | `w-14 h-14` |
| 圆角 | 16px | `rounded-2xl` |
| 图标 | 28x28px | `w-7 h-7` |
| 间距 | 12px | `gap-3` |
| 折叠按钮高度 | 32px | `h-8` |

### A8.2 FAB 迷你按钮尺寸

| 元素 | 尺寸 | Tailwind |
|------|------|----------|
| 按钮 | 32x32px | `w-8 h-8` |
| 图标 | 16x16px | `w-4 h-4` |
| 间距 | 4px | `gap-1` |
| 内边距 | 4px | `p-1` |

### A8.3 面板位置

| 面板 | 位置 | 尺寸 |
|------|------|------|
| FAB 容器 | `right-4 top-[7rem]` | 2列网格 |
| FAB 迷你条 | `right-0 top-[24rem]` | 单列 |
| 规则树侧边栏 | `left-0 top-16` | `w-72` (288px) |
| 弹出面板 | `right-44 top-24` | 各不相同 |

### A8.4 图片网格响应式列数

| 断点 | 列数 | 最小宽度 |
|------|------|----------|
| 默认 | 2 | 0px |
| sm | 3 | 640px |
| md | 4 | 768px |
| lg | 5 | 1024px |
| xl | 6 | 1280px |
| 2xl | 8 | 1536px |

### A8.5 z-index 层级

| 元素 | z-index |
|------|---------|
| 搜索栏 header | 30 |
| 弹出面板 | 40 |
| 规则树侧边栏 | 40 |
| FAB 按钮组 | 50 |
| 侧边栏切换按钮 | 50 |

---

## A9. 数据流与状态管理

### A9.1 LocalStorage 键值

| 键名 | 用途 | 默认值 |
|------|------|--------|
| `bqbq_tag_cache` | 标签缓存 | `[]` |
| `bqbq_tag_timestamp` | 缓存时间戳 | - |
| `bqbq_rules_version` | 规则版本号 | `0` |
| `bqbq_client_id` | 客户端ID | 随机生成 |
| `bqbq_prefer_hq` | HQ模式偏好 | `false` |

### A9.2 SessionStorage 键值

| 键名 | 用途 | 默认值 |
|------|------|--------|
| `bqbq_fab_collapsed` | FAB折叠状态 | `true` |
| `bqbq_fab_mini_position` | FAB迷你位置 | `null` |
| `bqbq_expansion_enabled` | 膨胀功能开关 | `true` |
| `bqbq_tree_expanded` | 规则树展开状态 | `[]` |

### A9.3 搜索请求数据结构

```javascript
{
    offset: Number,           // 分页偏移
    limit: Number,            // 每页数量
    sort_by: String,          // 排序方式
    keywords: [[String]],     // 二维数组：包含关键词组
    excludes: [[String]],     // 二维数组：OR排除关键词组
    excludes_and: [[[String]]], // 三维数组：AND排除关键词组
    extensions: [String],     // 包含的扩展名
    exclude_extensions: [String], // 排除的扩展名
    min_tags: Number,         // 最小标签数
    max_tags: Number          // 最大标签数 (-1=无限制)
}
```

### A9.4 图片数据结构

```javascript
{
    md5: String,              // 文件MD5哈希
    ext: String,              // 文件扩展名
    tags: [String],           // 标签数组
    is_trash: Boolean,        // 是否在回收站
    upload_time: String,      // 上传时间 ISO格式
    file_size: Number,        // 文件大小（字节）
    width: Number,            // 图片宽度
    height: Number            // 图片高度
}
```

### A9.5 规则树节点结构

```javascript
{
    id: Number,               // 组ID
    name: String,             // 组名
    isEnabled: Boolean,       // 是否启用
    keywords: [{              // 关键词列表
        text: String,
        isEnabled: Boolean
    }],
    children: [/* 递归子节点 */],
    parentIds: [Number],      // 父节点ID列表
    isConflict: Boolean,      // 是否冲突
    conflictReason: String    // 冲突原因
}
```

---

## A10. 完整功能清单

### A10.1 搜索功能

- [x] 标签胶囊输入（空格分割）
- [x] 排除标签（-前缀）
- [x] 同义词组（逗号分隔）
- [x] 交集排除（-tag1,tag2）
- [x] 扩展名筛选（.gif, .png等）
- [x] 标签数量筛选（滑块+输入框）
- [x] 同义词膨胀（规则树）
- [x] 多种排序方式

### A10.2 图片管理

- [x] 图片上传（MD5去重）
- [x] 缩略图生成（WebP格式）
- [x] 原图懒加载
- [x] 标签编辑（覆盖层）
- [x] 复制标签到剪贴板
- [x] 回收站（软删除）
- [x] 批量打标（临时标签模式）

### A10.3 规则树管理

- [x] 树形结构展示
- [x] 组的增删改
- [x] 关键词的增删改
- [x] 拖拽排序
- [x] 批量编辑模式
- [x] 展开/折叠全部
- [x] 搜索过滤
- [x] 乐观锁并发控制
- [x] 冲突检测与自动重试

### A10.4 UI 交互

- [x] FAB 悬浮按钮组
- [x] FAB 折叠/展开
- [x] FAB 迷你条拖拽
- [x] 规则树侧边栏
- [x] 弹出面板（临时标签、标签数量、排序）
- [x] 无限滚动加载
- [x] Toast 通知
- [x] 加载指示器

### A10.5 数据管理

- [x] 导出全部数据（JSON）
- [x] 导入数据（JSON）
- [x] 标签缓存（10分钟）
- [x] 规则版本控制（ETag）
- [x] 状态持久化（LocalStorage/SessionStorage）

---

**文档完成时间**: 2026-01-31

**文档用途**: 用于 100% 复刻旧项目到新项目的完整参考
```






