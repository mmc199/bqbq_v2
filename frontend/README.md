# Frontend README

`frontend/` 是 `BQBQ v2` 的前端子项目。

它并不是一个从零开始设计的页面，而是把旧项目中已经可用的图片搜索 / 规则树 / 标签编辑体验，迁移到 Vue 3 + TypeScript 架构中的结果。

---

## 技术栈

- Vue 3
- TypeScript
- Vite
- Pinia
- Tailwind CSS
- lucide-vue-next
- SparkMD5

---

## 当前入口

- `src/main.ts`：创建应用并挂载 Pinia
- `src/App.vue`：直接渲染 `src/views/Gallery.vue`

> 注意：虽然依赖中存在 `vue-router`，但当前前端**没有真正启用路由系统**，目前是单页直渲染。

---

## 组件关系图

```text
App.vue
└── Gallery.vue
    ├── TagInput.vue
    ├── MemeCard.vue[]
    ├── FloatingButtons.vue
    ├── RuleTree.vue
    │   └── RuleGroupNode.vue[]
    └── ToastContainer.vue
```

---

## 主要功能

- 标签搜索图片
- 排除标签 / 同义词输入
- 图片网格浏览
- 图片卡片内联编辑标签
- 缩略图 / 原图切换
- 规则树浏览与编辑
- 批量移动、批量启用 / 禁用 / 删除规则组
- 上传图片
- JSON 导入 / 导出
- 回收站模式
- 临时打标模式

---

## 核心文件

### 页面与组件

- `src/views/Gallery.vue`：业务主页面，当前前端主控制器
- `src/components/TagInput.vue`：标签输入组件
- `src/components/MemeCard.vue`：图片卡片
- `src/components/RuleTree.vue`：规则树主组件
- `src/components/RuleGroupNode.vue`：规则树递归节点
- `src/components/FloatingButtons.vue`：功能按钮组
- `src/components/ToastContainer.vue`：通知组件

### 数据与状态

- `src/composables/useApi.ts`：后端接口封装与兼容适配
- `src/composables/useOptimisticUpdate.ts`：CAS 冲突重试与乐观更新
- `src/composables/useToast.ts`：toast 封装
- `src/stores/useGlobalStore.ts`：全局状态与本地缓存
- `src/types/index.ts`：类型定义

---

## 当前前端承担的职责

相对旧项目，新前端做了更多结构化拆分，但 `Gallery.vue` 仍然承担很多核心业务调度职责：

- 搜索条件整理
- 图片加载与分页
- 规则树同步
- 上传、导入、导出
- 回收站模式与 HQ 模式切换
- 临时打标模式
- 主滚动容器的增量加载控制

所以在改功能时，不要只看单个组件，还要看 `Gallery.vue` 有没有联动逻辑。

---

## 与后端的关键契约

### 主要接口前缀

- API：`/api`
- 原图：`/images/{filename}`
- 缩略图：`/thumbnails/{filename}`

### 常用接口

- `POST /api/search`
- `GET /api/meta/tags`
- `GET /api/tags`
- `/api/rules/*`
- `/api/export/all`
- `/api/import/all`
- `/api/update_tags`

### 一个非常重要的兼容点

前端虽然已经组件化，但仍兼容旧项目的一些数据风格：

- 规则树读取时仍可能接收到旧式扁平结构
- 搜索接口既支持简单 payload，也支持旧式高级 payload
- 409 冲突响应会走兼容处理逻辑

---

## 本地开发

```bash
cd frontend
npm install
npm run dev
```

默认通过 Vite 开发服务器运行，并依赖后端提供：

- API
- 原图
- 缩略图

---

## 前端缓存与持久化

前端会在 `localStorage` / `sessionStorage` 中缓存：

- 客户端 ID
- 规则树版本号
- 规则树缓存
- 标签缓存
- HQ 模式
- 规则树展开状态
- FAB 折叠状态与位置

这部分主要由 `src/stores/useGlobalStore.ts` 管理。

---

## 修改建议

### 改搜索逻辑时

同时检查：

- `src/views/Gallery.vue`
- `src/composables/useApi.ts`
- `src/types/index.ts`

### 改规则树时

同时检查：

- `src/components/RuleTree.vue`
- `src/components/RuleGroupNode.vue`
- `src/composables/useApi.ts`
- `src/stores/useGlobalStore.ts`

### 改图片卡片时

同时检查：

- `src/components/MemeCard.vue`
- `src/components/TagInput.vue`
- `src/views/Gallery.vue`

### 改后端接口返回结构时

必须同步更新：

- `src/composables/useApi.ts`
- `src/types/index.ts`

---

## 给新手的理解方式

如果你刚开始用 AI 写这个项目，可以先把前端理解成：

- `Gallery.vue`：总调度
- `MemeCard.vue`：单张图的交互
- `RuleTree.vue`：规则树交互
- `useApi.ts`：所有后端接口入口
- `useGlobalStore.ts`：本地缓存和全局状态中心

这样你在问 AI 时，定位会更快。

