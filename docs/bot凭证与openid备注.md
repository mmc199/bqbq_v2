# bot 凭证与 openid 备注

> **本文件记录 bot 的长期凭证。仓库是私有的，但仍建议不要外传。**
> 凭证泄露等同于把写权限交给对方（能上传、能改标签）。

## 一、bot 凭证

两个 bot 各有一个长期有效的 `client_id`，已手动写入
`backend/meme.db` 的 `auth_granted_clients` 表（`kind='bot'`），
与网页登录产生的凭证走同一套鉴权。

| bot | client_id | 长度 |
|---|---|---|
| AstrBot | `bot_astrbot_5v63v6prskk9s` | 25 |
| nonebot2 | `bot_nonebot_62iuu3gi3utwx` | 25 |

**格式**：`bot_<名字>_` + 13 位随机字符（与网页 `client_xxxxxxxxxxxxx`
的后缀长度一致），熵约 65 bit。

**为什么带随机后缀**：以前用的是 `bot_astrbot` 这种固定名字，
任何人猜到就能冒充 bot 获得写权限。加随机后缀后无法猜测。

### 改凭证的完整步骤

1. 生成新值：`bot_astrbot_` + 13 位随机（小写字母 + 数字）
2. 更新数据库：
   ```sql
   DELETE FROM auth_granted_clients WHERE kind='bot' AND client_id LIKE 'bot_astrbot_%';
   INSERT INTO auth_granted_clients (client_id, openid, kind)
   VALUES ('bot_astrbot_<新13位>', '__bot_astrbot__', 'bot');
   ```
3. 更新插件代码里的默认值（见下）
4. 重启对应 bot

### 代码位置

| bot | 文件 | 位置 |
|---|---|---|
| AstrBot | `main.py` | `self.bot_client_id = str(cfg.get("bot_client_id") or "bot_astrbot_5v63v6prskk9s")` |
| AstrBot | `imagelib.py` | `ImageLibClient(backend, client_id)`，内部用 `_with_cid()` / `_body()` 自动附加 |
| nonebot2 | `__init__.py` | `BOT_CLIENT_ID = getattr(driver.config, "bqbq_client_id", "bot_nonebot_62iuu3gi3utwx")` |

两者都支持用配置项覆盖，不必改代码：
- AstrBot：配置项 `bot_client_id`
- nonebot2：`driver.config.bqbq_client_id`

## 二、openid 备注

bot 只能拿到 openid（32 位大写十六进制），时间久了分不清是谁。

### 用管理脚本（推荐）

```bash
cd backend

# 查看所有 openid（含备注、QQ 号、设备数、最近登录）
python manage_openid.py list

# 加备注
python manage_openid.py set A22C9E2359E63789C8E775ECD4A373B3 \
    --remark "我自己" --qq 123456

# 标记为站长本人（list 里显示 ★）
python manage_openid.py set A22C9E... --remark "我自己" --owner

# 按备注搜索
python manage_openid.py find "我自己"

# 撤销某人的所有授权（踢下线）
python manage_openid.py revoke A22C9E...
```

### 直接查数据库

```sql
-- 汇总视图：openid + 备注 + 挂了几个 client_id
SELECT * FROM v_openid_summary;

-- 手动设置备注
UPDATE openid_profiles
SET remark='朋友小王', qq='10001', updated_at=CURRENT_TIMESTAMP
WHERE openid='XXX';
```

### 表结构

**`openid_profiles`**

| 字段 | 说明 |
|---|---|
| `openid` | 主键，QQ 身份 |
| `remark` | 备注名，如「我自己」「朋友小王」 |
| `qq` | 对应 QQ 号（可选） |
| `is_owner` | 1 = 站长本人 |
| `created_at` / `updated_at` | 时间戳 |

**`v_openid_summary`**（视图，只读）
把授权表按 openid 聚合，附带备注与 client_id 列表，方便一眼看清
「谁登录过、登录过几个设备」。

**`auth_granted_clients`**

| 字段 | 说明 |
|---|---|
| `client_id` | 主键，凭证本身 |
| `openid` | 该凭证属于哪个 QQ（bot 凭证填 `__bot_xxx__`） |
| `kind` | `web` = 网页登录产生；`bot` = bot 长期凭证 |
| `granted_at` | 授权时间 |

## 三、上传接口已合并

原有两个上传接口逻辑完全重复（各 130 行）：

| 接口 | 状态 |
|---|---|
| `POST /api/images/upload` | **唯一实现**，两个 bot 与网页都用它 |
| `POST /api/upload` | 保留为兼容别名，内部直接委托，已标记 `deprecated` |

两者都需要 `?client_id=`，行为与返回字段完全一致。
