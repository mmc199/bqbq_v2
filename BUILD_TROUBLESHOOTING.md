# BUILD_TROUBLESHOOTING.md — 构建问题与缩略图批量加载

本文档记录两件事：

1. **`npm run build` 崩溃的根因**（换机器/重装 Node 时容易再踩）
2. **缩略图批量打包功能**的设计与验证

---

## 一、`npm run build` 崩溃：Node 版本问题

### 现象

```powershell
> npm run build
> vue-tsc -b && vite build

vite v7.3.1 building client environment for production...
transforming...
✓ 1728 modules transformed.
# ← 到这里突然结束，没有任何错误信息
[exit code: -1073740791]
```

- 退出码 `-1073740791` = `0xC0000409` = **STATUS_STACK_BUFFER_OVERRUN**
- 崩溃发生在 **`transforming` 之后、`rendering chunks` 之前**
  （即 Rollup 做模块链接 / tree-shaking 的阶段）
- **完全没有错误堆栈**，只有退出码

### 根因

**Node 24.12.0 在 Windows 上会导致 Rollup 原生模块栈溢出。**

决定性证据：

| 环境 / 测试 | 结果 |
| --- | --- |
| Node **24.12.0**（原） | ❌ 崩溃，**9/9 次稳定复现** |
| Node **26.7.0** | ✅ **构建成功** |
| 最小 vite 项目（同机器） | ✅ 成功 → 排除机器/环境问题 |
| 移除本次新增代码后 | ❌ 仍崩溃 → 排除新代码 |
| 去掉 JSZip 依赖 | ❌ 仍崩溃（1724 模块） |
| 关闭 minify / sourcemap | ❌ 仍崩溃 |
| 降级 rollup 到 4.51.0 | ❌ 仍崩溃 |
| 把最大的 RuleTree.vue 换空桩 | ❌ 仍崩溃（1725 模块） |

因为「移除新增代码仍崩溃」，所以**与本项目的代码无关**，
是 Node 运行时 + Rollup 原生二进制在 Windows 上的兼容问题。

参考：[nodejs/node#63620](https://github.com/nodejs/node/issues/63620)
（Windows 下 libuv `/GS stack-buffer-overrun` 静默崩溃）、
[rollup/rollup#6199](https://github.com/rollup/rollup/issues/6199)

### 解决办法

**升级 Node**（已在本机执行）：

```powershell
winget install --id OpenJS.NodeJS --accept-package-agreements --accept-source-agreements
```

升级后：

```
Node  : v24.12.0 → v26.7.0
npm   : 11.6.2   → 11.19.0
构建  : ❌ → ✅ 6.7 秒完成
```

> ⚠️ 注意包名：是 `OpenJS.NodeJS`（主版本线），
> 不是 `OpenJS.NodeJS.22` / `.24` 这类固定大版本的包。

### 排查建议（下次遇到类似问题）

按这个顺序，**别一上来就二分依赖**：

1. **看退出码**：`0xC0000409` 这类原生崩溃码 → 大概率是运行时/原生模块问题，不是你的代码
2. **跑最小复现**：新建一个只有 vite 的空项目，看能否构建
   - 能 → 问题在本项目依赖组合
   - 不能 → 问题是环境/Node 版本
3. **换 Node 版本试**：下载[便携版 Node](https://nodejs.org/dist/) 解压后直接跑，成本极低
   ```powershell
   $env:PATH = "C:\path\to\node-v26.7.0-win-x64;$env:PATH"
   npx vite build
   ```
4. 最后才去二分依赖

> 本次绕了十几轮弯路的教训：**在确认「移除自己改动后仍崩溃」时就该怀疑运行时**，
> 而不是继续在依赖堆里逐个排除。二分依赖每次要等 3-5 分钟，
> 而换 Node 版本一次就能定性。

---

## 二、缩略图批量打包

### 为什么需要

生产链路是「**中国服务器 → 内网穿透 → 美国服务器**」：

| 指标 | 实测/估算 |
| --- | --- |
| 单次往返 RTT | 约 200 ms |
| 穿透带宽 | 约 5 Mbps |
| 一页图片数 | 最多 100 张 |
| 一页缩略图总量 | 50 张约 1.78 MiB |

**逐个请求的代价**：

```
50 张 ÷ 浏览器 6 并发 = 9 轮 × 200ms = 1800ms 的纯等待开销
```

而传输量 1.78 MiB 无论分几个请求都要花掉（约 2.9 秒 @ 5Mbps）。

**合并成 1 个请求后，这 1800ms 的等待降到 200ms。**

### 方案对比

| 方案 | 请求数 | 等待 | 传输 | 合计 |
| --- | --- | --- | --- | --- |
| A 现状（逐个请求） | 50 | 1800 ms | 2990 ms | **4790 ms** |
| **B 打包 zip** | **1** | **200 ms** | 2930 ms | **3290 ms** |
| C 缩略图放 R2 走 CDN | 50 | 900 ms | 299 ms | 1199 ms |

> C 更快，但本次先实现 B（不依赖上传 13 GB、不改部署）。
> 两者不冲突，以后可以叠加。

### 实现

**后端**：`POST /thumbnails/batch`（`backend/app/main.py`）

```jsonc
// 请求
{ "md5": ["...", "..."] }        // 最多 200 个
// 响应：application/zip，内部文件名 = md5
```

用 `ZIP_STORED`（**不压缩**）：缩略图本身是 JPEG，已高度压缩，
再套 deflate 只能省 1-2%，却要付服务端 CPU 和前端解压时间的代价。
实测 50 张仅多约 0.5% 体积（ZIP 头部开销）。

**前端**：`src/composables/useThumbBatch.ts`

- 一次请求取回整页 → JSZip 解压 → 缓存 `blob:` URL
- 缓存上限 600 个，超出按时间淘汰并 `revokeObjectURL`（防内存泄漏）
- 同一批只发一次（`inflight` 去重）

### ⚠️ 关键设计点：不能在等待期间就回退

**这是第一版实现的 bug**，表现是「zip 还在下载，图片已经逐张加载」：

```ts
// ❌ 错误写法：查不到 blob 就立刻回退
const src = computed(() => batchedThumbUrl.value || thumbnailSrc.value)
```

原因：卡片挂载时批量请求还没回来 → `batchedThumbUrl` 为 null
→ **立刻**渲染单图 URL → 浏览器马上并发发出 N 个请求
→ 等 batch 返回时早已晚了，**batch 的作用被完全抵消**。

**正确做法**：引入全局「批量是否仍在进行」状态，等待期间**不渲染 `src`**：

```ts
const resolvedThumbSrc = computed(() => {
  if (batchedThumbUrl.value) return batchedThumbUrl.value
  if (!batchSettled.value) return null        // 批量中：占位，不发请求
  return thumbnailSrc.value                   // 批量已结束仍未命中：回退
})
```

配合 `isBatchPending()` / `onBatchSettled()` 订阅（而非轮询）。

### 验证（用真实浏览器统计网络请求）

用 Playwright + 缓存的 Chromium 实测：

**正常情况：**

```
批量请求 (batch)  : 1
单图缩略图请求     : 0        ← 关键
页面 <img> 总数 40  blob 40  http 0
```

**批量失败时（强制返回 500）：**

```
批量请求 (batch)  : 1
单图缩略图请求     : 40
页面 <img> 总数 40  blob 0  http 40  已成功解码 40
✅ 降级生效，不会白屏
```

### 维护提醒

1. **批量请求期间绝不能让卡片渲染单图 URL**，否则等于没做
2. `blob:` URL 必须 `revokeObjectURL`，否则内存持续增长
3. 后端 `md5` 参数上限 200，前端会分块（正常一页不会超）
4. 打包格式是 `ZIP_STORED`；若改成 deflate，注意前端解压耗时

---

## 三、一屏装得下时无法翻页（已修复）

### 现象

手机浏览器选择「电脑版」，一屏能显示 40+ 张图，
**但不会继续请求，也无法下拉翻页** —— 卡死在首批结果上。

### 根因

原来的翻页逻辑只挂在 `scroll` 事件上：

```js
function handleMainScroll() {
  const el = mainRef.value
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 200) loadMore()
}
```

这隐含了一个**前提假设：内容一定超出容器高度**。

当一屏就能装下全部结果时，`scrollHeight == clientHeight`，
**既没有滚动条、也永远不会触发 scroll 事件**，于是 `loadMore()` 永不调用。

实测复现（8 列布局，每页 40 张）：

| 视口高度 | clientHeight | scrollHeight | 能滚动 | search 请求 |
| --- | --- | --- | --- | --- |
| 1600 | 1536 | 1536 | ❌ 否 | **1** |
| 2000 | 1936 | 1936 | ❌ 否 | **1** |
| 2400 | 2336 | 2336 | ❌ 否 | **1** |
| 4000 | 3936 | 3936 | ❌ 否 | **1** |

> 注意：这**不只影响手机**。任何「大屏 + 结果较少」的组合都会卡死，
> 例如 2xl 断点（8 列）下 40 张只占 5 行，1600px 高就装得下。

### 修复

新增**自动补足**逻辑：每次渲染后检查，若内容还没撑出滚动条且还有更多数据，
就继续拉下一页，直到撑出滚动条（或数据取完）。

```js
watch(() => images.value.length, async () => {
  await nextTick()               // 等 DOM 更新完再量高度
  await autoFillIfNeeded()
}, { flush: 'post' })
```

配套措施：

- `MAX_AUTOFILL_ROUNDS = 10` 上限，避免极端情况下无限请求
- 监听 `resize`（旋转屏幕、拖窗口、手机切换电脑版）后重新检查
- 用 `nextTick` 等布局完成，否则量到的是旧高度

### 验证

| 场景 | 修复前 | 修复后 |
| --- | --- | --- |
| 1600×1600（手机桌面版） | 40 张，**卡死** | **80 张，可滚动** ✅ |
| 1600×2400（超高视口） | 40 张，**卡死** | **120 张，可滚动** ✅ |
| 1440×900（笔记本） | 40 张，可滚动 | 40 张，可滚动 ✅（无需补足） |
| 滚动翻页 | — | 40 → 200 张，5 次请求 ✅ |
| 数据一致性 | — | 80 卡片 = 80 唯一 URL，**无重复** ✅ |

### 维护提醒

1. **任何「滚动触底加载」都必须在挂载/渲染后补一次「是否可滚动」的检查**，
   否则内容不足一屏时会永久卡住
2. 判断是否可滚动要留容差（`scrollHeight <= clientHeight + 4`），
   避免亚像素误差误判
3. 量高度前必须 `await nextTick()`，否则读到旧布局
