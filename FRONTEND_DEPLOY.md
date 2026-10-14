# FRONTEND_DEPLOY.md — 前端托管方式（dev vs build）

本文档说明前端两种运行模式的区别、如何切换，以及为什么公网必须用 build。

---

## 一、结论先行

| 场景 | 用哪种模式 | 访问地址 |
| --- | --- | --- |
| **公网访问（日常使用）** | **build**（默认） | `https://bqbq.mmc199.com/g2/` |
| 改前端代码 | dev | `http://localhost:5173/g2/` |

```powershell
.\start.ps1              # build 模式（默认，推荐）
.\start.ps1 -DevMode     # dev 模式（改代码时）
```

---

## 二、为什么公网必须用 build

原来的架构是：**公网 nginx → 本机 Vite dev server(5173)**。

dev 模式下 Vite 按 ES module **逐个**返回 `.ts` / `.vue` 源码，还会注入 HMR 客户端。
实测对比：

| 指标 | dev 模式 | **build 版本** | 改善 |
| --- | --- | --- | --- |
| JS 请求数 | **28 个** | **1 个** | **28x** |
| JS 传输量 | **2,586 KiB**（未压缩） | **311 KiB**（已压缩） | **8.3x** |
| CSS | 1 个 8 KiB | 1 个 48 KiB（含 Tailwind） | — |
| HMR 客户端 | **175 KiB**（生产完全无用） | 无 | — |
| 合计脚本传输 | 约 **2.6 MB** | 约 **359 KiB** | **约 7x** |

### 再加一层 gzip（已启用）

发现 nginx 未对 JS/CSS 做压缩，于是在**后端**加了 `GZipMiddleware`
（见 `backend/app/main.py`），不依赖 nginx 配置即可生效：

| | 未压缩 | **gzip 后** |
| --- | --- | --- |
| JS | 311 KiB | **104 KiB**（省 66%） |
| CSS | 48 KiB | **10 KiB**（省 80%） |

### 最终效果（实测约 0.6 Mbps 公网链路）

| 阶段 | JS 传输 | 估算耗时 |
| --- | --- | --- |
| dev 模式（原） | 2,586 KiB | 约 35 秒 |
| build 版本 | 311 KiB | 约 4.2 秒 |
| **build + gzip（现在）** | **104 KiB** | **约 2.0 秒** |

真实浏览器实测 **load 事件：5.6 秒 → 2.8 秒**。

> 也就是说：「浏览器加载太多 js/ts/vue」的根因有两层 ——
> ① dev 模式不打包（28 个模块）② 未压缩。两层都已解决。

---

## 三、新架构

```
公网浏览器
   │  https://bqbq.mmc199.com/g2/
   ▼
nginx（公网机）
   │  转发到本机 8000
   ▼
FastAPI :8000
   ├─ /g2/            → build 产物（index.html + assets/）
   ├─ /g2/api/*       → API（前端固定用这个前缀）
   ├─ /api/*          → API（兼容保留）
   ├─ /images/*       → 原图
   └─ /thumbnails/*   → 缩略图
```

**关键变化：不再需要 Vite dev server，只需一个后端服务。**

### 为什么后端要同时认 `/g2/api` 和 `/api`

前端代码里 API 基址固定是 `/g2/api`（见 `frontend/src/composables/useApi.ts`）：

```ts
const API_BASE = '/g2/api'
```

以前由 Vite dev server 把 `/g2/api` 重写成 `/api` 再转发给后端。
现在由后端直接托管前端，没有那层重写了，所以后端自己也要挂一份 `/g2/api` 前缀
（见 `backend/app/main.py` 里第二次 `include_router`）。两套前缀都保留是为了兼容本地 dev。

---

## 四、实现细节

### 后端挂载

`backend/app/main.py`：

```python
FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"
app.mount("/g2", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
```

**路由顺序很重要**：`/g2/api/*` 必须先于 `/g2` 挂载注册，
否则 `StaticFiles` 会把 API 请求也当成静态文件去找（会 404）。
当前顺序：API 路由在位置 42-79，`/g2` 挂载在位置 81。

产物不存在时只打印提示、不影响后端启动，避免「没 build 就完全起不来」。

### start.ps1 的行为

build 模式下脚本会：

1. 检查 `frontend/dist/index.html` 是否存在
2. **检查 `src/` 下是否有文件比产物新** —— 有则自动重新构建
3. 构建失败时提示可改用 `-DevMode`
4. 只启动后端（不再需要 5173）

想强制重建：`.\start.ps1 -Build`

---

## 五、验证结果

### 本地（后端直连）

```
GET /g2/                      -> 200, 883 字节, 无 @vite/client ✅
GET /g2/assets/*.js           -> 200, 318,172 字节
POST /g2/api/search           -> 200, total=434810
GET  /api/stats               -> 200（兼容前缀仍可用）
GET  /images/... /thumbnails/... -> 200
```

### 公网（https://bqbq.mmc199.com/g2/）

真实浏览器实测：

```
总请求    : 48        （其中 40 个是缩略图业务数据）
JS        : 1 个, 311 KiB      ← 关键指标
CSS       : 2 个, 56 KiB
卡片/图片 : 40 / 40（全部成功解码）
页面错误  : 无
```

---

## 六、注意事项

### nginx 上游必须改成 8000

build 模式下 5173 不再监听。如果 nginx 仍指向 5173，公网会返回
**502 Bad Gateway**（实测遇到过）。

### 改前端代码的流程

| 模式 | 改完代码后 |
| --- | --- |
| dev | 自动热更新，刷新即可 |
| build | **重跑 `.\start.ps1`**（会自动检测源码更新并重建），或手动 `npm run build` |

### Node 版本要求

`npm run build` 需要 **Node ≥ 26**。
Node 24.12.0 在 Windows 上会崩溃（退出码 `0xC0000409`），详见 `BUILD_TROUBLESHOOTING.md`。

### 未来的优化方向

目前脚本 gzip 后约 104 KiB，在 0.6 Mbps 链路上约 2 秒，已经可接受。
若还想进一步：

1. **路由级代码分割**：目前所有组件打成一个 chunk，
   `RuleTree.vue`（62 KB）等非首屏组件可用 `defineAsyncComponent` 拆出去，
   首屏只需下载真正用到的部分
2. **CDN 托管静态资源**：把 `dist/assets/*` 放 CDN（同图片的做法），
   彻底绕开穿透链路
3. **nginx 端 gzip_static**：构建时预生成 `.gz` 文件，
   nginx 直接发预压缩文件，省掉后端实时压缩的 CPU
   （后端 GZipMiddleware 已够用，此项仅为进一步省 CPU）

### 已做的 gzip 配置

`backend/app/main.py`：

```python
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=500)
```

`minimum_size=500`：小于 500 字节的响应不压缩（压缩后反而更大）。

> 本机环境测不出 gzip 的价值（回环带宽足够），必须用公网链路才能体现。
