# R2_UPLOAD.md — 43 万表情包上传到 Cloudflare R2

> ## ✅ 新增：后端自动同步新图到 R2（2026-10-04）
>
> **问题**：后端上传图片只落本地磁盘，不推 R2 —— 而前端原图走 CDN，
> 所以机器人新收的图在前端会 **404**。
>
> **实现**：`backend/app/r2_sync.py`，在上传接口里**异步**推送，不阻塞响应。
>
> | 特性 | 说明 |
> | --- | --- |
> | 异步非阻塞 | 上传接口不等待 R2，不拖慢机器人收图（实测 2 秒内同步完成） |
> | 失败不影响入库 | R2 挂了本地文件仍在，前端会回退到本地接口 |
> | 先查后传 | 已存在的对象跳过 |
> | 并发限制 | 最多 4 个同步线程 |
> | 自动降级 | 没装 rclone 时只提示一次 |
>
> **补传工具**：`backend/backfill_r2.py`
> ```powershell
> python backfill_r2.py --dry-run               # 只列出缺哪些
> python backfill_r2.py --apply                 # 补传全部缺失
> python backfill_r2.py --since 435592 --apply  # 只处理 id 大于该值
> ```
>
> **前端回退**：CDN 加载失败时自动改用后端 `/images`，用户无感。
> 实测：CDN 404 时 2 次本地请求后正常显示；CDN 正常时 0 次本地请求。
>
> ### 关于「R2 会不会自动去重」
>
> **不会**（实测）：
> - 同名 key、不同内容 → **直接覆盖**，旧内容丢失
> - 不同 key、相同内容 → **两个都存**
>
> 但对本项目无影响：对象 key 就是 `<md5>.<ext>`，
> **MD5 即内容指纹**，内容相同必然同 key，覆盖的也是同一个文件。
> 真正的去重由后端的 MD5 查重负责。

> ## ✅ 上传已完成（2026-10-03）
>
> | 项目 | 结果 |
> | --- | --- |
> | 上传范围 | **仅原图** `meme_images`（按用户要求，缩略图未传） |
> | 对象数 | **434,810**（本地 434,810，完全一致） |
> | 体积 | **144,933,132,622 字节**（本地同值，**逐字节一致**） |
> | 耗时 | 5 小时 50 分，平均约 10 MiB/s |
> | 传输错误 | 2 次瞬时 502，rclone 自动重试后成功 |
> | 完整性 | `rclone check --one-way` 退出码 **0**；256 个分片逐一比对**全部一致** |
> | 公开访问 | `https://<R2_PUBLIC_BUCKET_ID>.r2.dev`（已验证 200 + 字节一致） |
>
> ⚠️ 上传过程中发现的一个坑：`rclone copy` 默认会把 Syncthing 的
> `meme_images/.stfolder/`（122 字节标记文件）也传上去，导致远端比本地多 1 个对象。
> 已删除，并在后续命令中加上 `--exclude ".stfolder/**" --exclude ".stignore"`。
>
> 🔴 **上传用的凭据是临时创建的、只能读写 `bqbq-memes` 这一个桶的限定令牌**
> （不是 Global API Key）。**你消息里贴出的 Global API Key 请立即吊销**：
> <https://dash.cloudflare.com/profile/api-tokens> → Global API Key → Change。
> 吊销它**不会**影响已上传的数据。
>
> ---
>
> ## ✅ 自定义域名已配置完成（2026-10-04）
>
> | 项目 | 值 |
> | --- | --- |
> | CDN 域名 | **`https://bqbq-img.mmc199.com`** |
> | DNS | `CNAME bqbq-img.mmc199.com → public.r2.dev`（已代理 🟠） |
> | 证书 | active，TLS 1.3（Google Trust Services，有效期至 2027-01-01，自动续期） |
> | 缓存规则 | Edge TTL + Browser TTL **1 年**（`immutable` 语义，图片按 MD5 命名内容永不变） |
> | 缓存实测 | 首次 `MISS`，再次 `HIT` ✅ |
> | `r2.dev` | **已关闭**（避免绕过缓存与防盗链） |
> | 前端配置 | `frontend/.env.local` 的 `VITE_CDN_BASE_URL` 已指向新域名 |
>
> **缩略图未上传**（按用户要求），仍走本地后端，见第 9 节。

本文档记录上传流程与约定，供后续增量同步参考。

---

## 0. 先纠正一个说法：rsync 用不了

**rsync 无法连接 Cloudflare R2。** 原因：

- rsync 是自有协议，必须在**两端都跑 rsync 进程**（rsync daemon 或 SSH）。
- Cloudflare R2 只提供 **S3 兼容 API**，不会跑 rsync daemon。

所以对 R2 要用 **rclone** —— 命令和 rsync 非常像（`copy` / `sync` / `--dry-run`
/ `--exclude`），但它会说 S3 协议。本指南全部使用 rclone。

> 如果你原本想让 rsync 做的是「本地两台机器互相同步」，那 rsync 仍然可以；
> 但只要是往 Cloudflare 传，就必须用 rclone / aws-cli / SDK。

---

## 1. 你的数据规模（实测）

| 项目 | 数值 |
| --- | --- |
| 原图 | 434,810 个文件 / **134.98 GiB** |
| 缩略图 | 434,811 个文件 / **13.21 GiB** |
| **合计** | **869,621 个文件 / 148.19 GiB** |
| 平均文件大小 | 原图 325 KiB（中位数 67 KiB） |
| 最大文件 | 23.5 MiB |

### 文件大小分布

| 区间 | 文件数 | 合计 |
| --- | --- | --- |
| < 100 KiB | 274,170 | 10.44 GiB |
| 100 KiB – 1 MiB | 123,146 | 34.56 GiB |
| 1 – 5 MiB | 34,127 | 62.86 GiB |
| > 5 MiB | 3,367 | 27.13 GiB |

> 所有文件都 **远小于 100 MiB**，所以每个对象只需 **1 次 Class A 操作**
> （单个 PutObject，不会触发 multipart）。这对省钱很关键。

---

## 2. 费用估算

参考 [R2 官方定价](https://developers.cloudflare.com/r2/pricing/)：

| 项目 | 单价 | 免费额度 |
| --- | --- | --- |
| 存储（标准） | $0.015 / GB-月 | 10 GB-月 |
| Class A 操作 | $4.50 / 百万次 | 100 万次 / 月 |
| Class B 操作 | $0.36 / 百万次 | 1000 万次 / 月 |
| 出网流量 | **免费** | — |

### 存储

```
148.19 GiB ≈ 159.1 GB
(159.1 − 10) × $0.015 ≈ $2.24 / 月
```

### 首次上传的 Class A 操作

```
869,621 个对象 × 1 次 PutObject = 869,621 次
减去 100 万免费额度 → 0
首次上传操作费 ≈ $0.00
```

### 结论

**大约 $2.2 / 月**，且首次上传的操作费基本被免费额度覆盖。

> 注意：Cloudflare 的计费单位是**向上取整**。如果你某月操作数超过 100 万，
> 会直接按 200 万计费。日常浏览只产生 Class B（读），1000 万次/月免费额度很大。

---

## 3. 安装 rclone

Windows 推荐用 winget：

```powershell
winget install --id Rclone.Rclone -e
```

如果 winget 不可用，去 <https://rclone.org/downloads/> 下载 Windows zip，
解压后把 `rclone.exe` 放到 `C:\Windows\System32` 或任意 PATH 目录。

验证（**必须 ≥ 1.59**，更低版本对 R2 会返回 401）：

```powershell
rclone version
```

---

## 4. 在 Cloudflare 创建 R2 与密钥

> **实测记录（本次已完成的配置）**
>
> | 项目 | 值 |
> | --- | --- |
> | 桶名 | `bqbq-memes` |
> | Account ID | `<ACCOUNT_ID>` |
> | endpoint | `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` |
> | 公开域名 | **`https://bqbq-img.mmc199.com`**（自定义域名，已启用缓存） |
> | rclone remote 名 | `r2` |
>
> **命名说明**：`img.mmc199.com` 已被另一个图床（Telegraph-Image，
> 部署在 Cloudflare Pages 项目 `mmc199`）占用，所以本桶使用
> `bqbq-img.mmc199.com`，与 `bqbq.mmc199.com` 主站成系列、互不干扰。
>
> **权限最小化**：实际用于上传的不是 Global API Key，而是一个
> 新建的、**只对该桶有 Object Read & Write 权限**的限定令牌
> （permission group：`Workers R2 Storage Bucket Item Read/Write`，
> resource：`com.cloudflare.edge.r2.bucket.<ACCOUNT_ID>_default_bqbq-memes`）。
>
> **S3 凭据的推导方式**（官方规则，容易踩坑）：
> - `Access Key ID` = API Token 的 **`id`**
> - `Secret Access Key` = **该 Token `value` 的 SHA-256 哈希**（不是 value 本身）
>
> 参考：<https://developers.cloudflare.com/r2/api/tokens/>

### 4.1 创建桶

1. 登录 Cloudflare Dashboard → **R2 object storage** → **Create bucket**
2. 名称填 `bqbq-memes`
3. 位置：选 **Automatic**（或离你近的亚太区）
4. 创建

### 4.2 创建 API 令牌（Access Key）

1. R2 页面 → 右侧 **API** → **Manage API tokens**
2. **Create API token** → 权限选 **Object Read & Write**
3. 建议限定到 `bqbq-memes` 这一个桶（最小权限）
4. 记下三样东西（**Secret 只显示一次**）：
   - Access Key ID
   - Secret Access Key
   - 你的 **Account ID**（R2 概览页右侧可复制）

### 4.3 开启公开读取

因为你要「公开读」，二选一：

**方式 A：自定义域名（生产推荐）**

1. 桶 → **Settings** → **Custom Domains** → **Add**
2. 填例如 `img.你的域名.com`，按提示加 DNS 记录
3. 好处：可走 Cloudflare 缓存、能配 WAF / 防盗链

**方式 B：r2.dev 开发域名（快速验证）**

1. 桶 → **Settings** → **Public Development URL** → **Enable**
2. 输入 `allow` 确认
3. 得到形如 `https://pub-xxxxxxxx.r2.dev` 的地址

> ⚠️ r2.dev **有速率限制，仅供开发**。正式用请走自定义域名。
> 另外：**不要把 r2.dev 用 CNAME 挂到自己的域名上**，官方明确不支持。

---

## 5. 配置 rclone

```powershell
rclone config
```

按提示操作：`n`（新建）→ 名字 `r2` → 存储类型选
`Amazon S3 Compliant Storage Providers` → 提供商选 `Cloudflare R2`
→ 填入 Key ID / Secret → region 填 `auto` → endpoint 填
`https://<你的AccountID>.r2.cloudflarestorage.com`

也可以直接编辑配置文件（`rclone config file` 可看路径）：

```ini
[r2]
type = s3
provider = Cloudflare
access_key_id = 你的KEY_ID
secret_access_key = 你的SECRET
endpoint = https://你的ACCOUNTID.r2.cloudflarestorage.com
acl = private
region = auto

# 大文件并发与重试，适合 15 万个小文件 + 少量大文件
transfers = 32
checkers = 32
s3_chunk_size = 32M
s3_upload_cutoff = 64M
s3_no_check_bucket = true
```

验证连接：

```powershell
rclone lsd r2:
```

---

## 6. 上传

> **补充（实测）：** 一定要加排除规则，否则 Syncthing 的元数据目录会被传上去：
>
> ```powershell
> --exclude ".stfolder/**" --exclude ".stignore"
> ```

### 6.1 先演习（务必！）

```powershell
rclone copy "D:\bqbq_backend\meme_images" r2:bqbq-memes/meme_images `
  --dry-run --transfers 32 --checkers 32 -P `
  --exclude ".stfolder/**" --exclude ".stignore"
```

`--dry-run` 不传任何数据，只列出「将要做什么」。确认路径无误再真跑。

### 6.2 正式上传

推荐**分两批**：先传缩略图（13 GB，快，能立刻验证），再传原图（135 GB）。

```powershell
# 第一批：缩略图（约 13 GB）
rclone copy "D:\bqbq_backend\meme_images_thumbnail" r2:bqbq-memes/meme_images_thumbnail `
  --transfers 64 --checkers 64 --retries 5 --low-level-retries 20 `
  --progress --stats 30s --log-file "D:\bqbq_backend\r2_thumb_upload.log" --log-level INFO
```

```powershell
# 第二批：原图（约 135 GB，耗时长，建议挂后台）
rclone copy "D:\bqbq_backend\meme_images" r2:bqbq-memes/meme_images `
  --transfers 32 --checkers 32 --retries 5 --low-level-retries 20 `
  --progress --stats 30s --log-file "D:\bqbq_backend\r2_image_upload.log" --log-level INFO `
  --exclude ".stfolder/**" --exclude ".stignore"
```

### 6.3 关于 `copy` 和 `sync` 的选择（重要）

| 命令 | 行为 | 建议 |
| --- | --- | --- |
| `rclone copy` | 只上传缺失/变更的，**不删远端多余文件** | ✅ **用这个** |
| `rclone sync` | 让远端与本地**完全一致，会删除远端多余文件** | ⚠️ 谨慎 |

**首次上传用 `copy`。** `sync` 一旦路径写错（比如把空目录同步到桶根），
会**删掉你桶里的数据**。等你确认 bucket 结构正确、且确实想镜像删除时再考虑 sync。

### 6.4 断点续传

rclone 天生支持：中断后**重新执行同一条命令**即可，已上传的会自动跳过
（依据大小/修改时间/校验和判断）。这就是它比 rsync 更方便的地方。

### 6.5 加速：并行按分片目录切分

43 万小文件，瓶颈在**每文件的往返延迟**。可以按 16 个一级分片并行开 16 个进程：

```powershell
# 只传 00~0f 开头的分片
rclone copy "D:\bqbq_backend\meme_images" r2:bqbq-memes/meme_images `
  --include "0?/**" --transfers 32 -P
```

不过一般来说，先把 `--transfers` 调到 **32–64** 就够了；
除非你确认带宽吃不满，否则不必手工分片。

---

## 7. 预计耗时

上传耗时几乎完全取决于**你的上行带宽**，而不是文件数（
869,621 次请求在 32 并发下约几小时量级）。

| 上行带宽 | 148 GB 理论耗时 |
| --- | --- |
| 10 Mbps | ~33 小时 |
| 30 Mbps | ~11 小时 |
| 100 Mbps | ~3.5 小时 |
| 500 Mbps | ~45 分钟 |

**建议**：先跑缩略图那批（13 GB），根据实际速度再推算原图要多久。
日志里的 `--stats` 会给出实时速率。

---

## 8. 上传完成后：校验

### 8.1 数量核对

```powershell
# 远端对象数（会列出所有对象，数量大时较慢）
rclone size r2:bqbq-memes/meme_images
rclone size r2:bqbq-memes/meme_images_thumbnail
```

期望：

- `meme_images` → **434,810** 个对象 / **134.98 GiB**
- `meme_images_thumbnail` → **434,811** 个对象 / **13.21 GiB**

### 8.2 抽查具体文件

```powershell
rclone lsjson r2:bqbq-memes/meme_images/7f/5d --files-only
```

对比本地：

```powershell
Get-ChildItem "D:\bqbq_backend\meme_images\7f\5d"
```

### 8.3 用 rclone check 做完整性校验

```powershell
rclone check "D:\bqbq_backend\meme_images" r2:bqbq-memes/meme_images `
  --size-only --one-way -P
```

> 用 `--size-only`（只比大小）比默认的哈希校验快得多；
> 43 万文件全量哈希校验会非常慢。R2 的 S3 接口对 multipart 对象的
> 哈希值和本地不一致，容易误报，所以这里用大小足够。

### 8.4 浏览器验证公开访问

```powershell
# 换成你的域名
curl "https://img.你的域名.com/meme_images/7f/5d/7f5d377f8dae018434c9b5638d4a5cec.gif" -I
```

应返回 `200`。我在本地验证过这个路径确实存在。

---

## 9. 接入 bqbq_v2 后端

目前后端是**本地读盘**：

```text
/images/{filename}      -> StaticFiles 挂载 backend/meme_images
/thumbnails/{filename}  -> 本地找/生成
```

### ✅ 已经帮你接好了：方案 A（前端走 CDN，服务器零图片流量）

我新增了 `frontend/src/composables/useImageUrl.ts`，并把
`MemeCard.vue` 改为通过它取地址。**默认行为完全不变**，
只有你设置了环境变量才会走 CDN —— 所以本地开发和线上 CDN 可以共存。

**启用方式**：在 `frontend/` 下新建 `.env.local`（可从 `.env.example` 复制）：

```ini
VITE_CDN_BASE_URL=https://bqbq-img.mmc199.com
```

然后重新 `npm run dev`（或重新 build）。

它会自动产出正确的地址：

| 模式 | 原图 | 缩略图 |
| --- | --- | --- |
| 未配置（本地） | `/images/7f/5d/xxx.gif` | `/thumbnails/7f/5d/xxx.gif` |
| 配置 CDN 后 | `https://bqbq-img.mmc199.com/meme_images/7f/5d/xxx.gif` | `/thumbnails/7f/5d/xxx.gif`（本地） |

> **原图与缩略图分开配置**：本项目只上传了原图，缩略图仍在本地。
> 所以 `.env.local` 里只设 `VITE_CDN_BASE_URL`，**不要**设
> `VITE_CDN_THUMB_BASE_URL`（设了会 404）。
> 等以后也上传了缩略图，再补上后者即可。

### 缓存规则（已配置）

| 项 | 值 |
| --- | --- |
| Ruleset phase | `http_request_cache_settings` |
| 匹配 | `http.host eq "bqbq-img.mmc199.com"` |
| Edge TTL | 31536000 秒（1 年） |
| Browser TTL | 31536000 秒（1 年） |
| 依据 | 图片按 MD5 命名，**内容永不改变**，可安全长缓存 |

效果：浏览器二次访问**零请求**；Cloudflare 边缘命中后**不回源**，
大幅减少 R2 的 B 类读取操作。


### 方案 B：后端反代 / 跳转到 R2（可选）

如果希望**前端零改动**、由后端统一决定走本地还是 CDN，
可以改 `/images` 路由做 302 跳转：

```python
from fastapi.responses import RedirectResponse

@app.get("/images/{filename:path}")
async def serve_image(filename: str):
    if settings.cdn_base_url:
        return RedirectResponse(
            f"{settings.cdn_base_url}/meme_images/{filename}", status_code=302
        )
    ...
```

> ⚠️ 注意：`/images` 目前是 `app.mount(StaticFiles(...))`，
> **挂载的路由优先级高于普通装饰器路由**，直接用上面的写法不会生效，
> 必须先去掉那个 `app.mount("/images", ...)`。
>
> 因此**推荐直接用已接好的方案 A**，改动小、可回退、本地线上兼容。


---

## 10. 常见问题

### 401 Unauthorized

- rclone 版本 < 1.59
- endpoint 写错（应是 `https://<accountid>.r2.cloudflarestorage.com`）
- 令牌没有该桶权限 → 加 `s3_no_check_bucket = true`

### 429 / 上传很慢

降低 `--transfers`（R2 对小文件高频写入有速率限制），
或分批按分片目录上传。

### `--dry-run` 显示要传 43 万个，但明明已经传过

rclone 默认按「大小 + 修改时间」判断。加 `--size-only` 或
`--checksum` 调整判据：

```powershell
rclone copy ... --size-only
```

### 想只传增量（后续新增图片）

直接再跑一次第 6.2 节的命令即可，已存在的会自动跳过。

### 断了怎么办

重跑同一条命令，rclone 自动续传，**不要**加 `--ignore-existing`
（那会导致已传文件被跳过而没校验）。

---

## 11. 回滚 / 清理

```powershell
# 删除整个前缀（谨慎！先 dry-run）
rclone purge r2:bqbq-memes/meme_images --dry-run

# 删除桶（需先清空）
rclone purge r2:bqbq-memes
```

> R2 的 `DeleteObject` 是**免费**的，删除不产生 Class A 费用。

---

## 12. 一句话总结流程

```text
1. winget install Rclone.Rclone
2. Cloudflare 建桶 bqbq-memes + 建 API 令牌 + 开公开访问
3. rclone config 建名为 r2 的 remote
4. .\scripts\upload_to_r2.ps1 -Action check     ← 检查环境 + 连通性
5. .\scripts\upload_to_r2.ps1 -Action dryrun    ← 演习
6. .\scripts\upload_to_r2.ps1 -Action thumbs    ← 先传缩略图 (13GB)
7. .\scripts\upload_to_r2.ps1 -Action images    ← 再传原图 (135GB)
8. .\scripts\upload_to_r2.ps1 -Action verify    ← 校验数量
9. frontend/.env.local 填 VITE_CDN_BASE_URL     ← 前端切到 CDN
```

---

## 13. 附：辅助脚本 `scripts/upload_to_r2.ps1`

我已经写好一个 PowerShell 脚本把上面的流程包起来：

```powershell
cd C:\000soft\qqpy机器人-git\bqbq_v2
.\scripts\upload_to_r2.ps1 -Action check     # 检查 rclone 版本 + 本地数据量 + 远端连通
.\scripts\upload_to_r2.ps1 -Action dryrun    # 演习，不传数据
.\scripts\upload_to_r2.ps1 -Action thumbs    # 传缩略图
.\scripts\upload_to_r2.ps1 -Action images    # 传原图
.\scripts\upload_to_r2.ps1 -Action verify    # 校验远端数量与体积
```

参数可覆盖：`-Remote`、`-ImageRoot`、`-ThumbRoot`。

脚本做的事：

- 检查 rclone 是否存在、版本是否 ≥ 1.59（低版本对 R2 会 401）
- 统计本地文件数与体积（已实测与 434,810 / 134.98 GiB 一致）
- 统一使用 `--transfers 32 --checkers 32 --retries 5`，并把日志写到
  `D:\bqbq_backend\r2_*_upload.log`
- 上传用 **`rclone copy`（不是 sync）**，确保**不会误删远端文件**

> ⚠️ 这个脚本因为包含中文，已保存为 **UTF-8 with BOM**。
> 如果你用编辑器重新保存，请注意保留 BOM，否则 Windows PowerShell 5.1
> 可能会把中文读成乱码并报「字符串缺少终止符」。

