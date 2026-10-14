# ASTRBOT_PLUGIN.md —— AstrBot 插件开发易错点

本文档记录在 `C:\000soft\AstrBotLauncher-0.2.0`（AstrBot）上开发
`astrbot_plugin_bqbq_collect` 时**实际踩过的坑**，每条都附有源码依据和实测结论。

适用对象：任何要在 AstrBot 上写「消息收集类插件」的人（包括未来的我）。

---

## 零、最关键的前提：官方机器人**收不到**群里的所有消息

**先给结论**：QQ 官方机器人在**实际可用范围内**只能收到：

- ✅ 私聊消息
- ✅ **@了机器人**的群消息
- ❌ 群里其他人之间发的消息 —— **收不到**

### ⚠️ 但原因不是"技术上不支持"，而是"权限没开放"

这一点很容易搞错，必须说清，否则会做出错误的判断。

**技术上，API 是存在的：**

| 事件 | 场景 |
| --- | --- |
| `GROUP_AT_MESSAGE_CREATE` | 只收 @机器人 的消息（**默认**） |
| `GROUP_MESSAGE_CREATE` | **全量模式**，收群内每一条消息 |

[官方文档原文](https://bot.q.qq.com/wiki/develop/api-v2/autogen/event/group_message_create.html)：

> 当机器人开启了"接收所有消息"功能后，群里的**每一条消息（不限于@机器人）**
> 都会推送此事件。

**但权限处于灰度，个人主体用不了。**

[官方 FAQ](https://bot.q.qq.com/wiki/bot_FAQ/) 原文：

> 公开全量使用：当前该能力正在对**企业开发者灰度**，
> 后续会推全到个人认证，请耐心等待。

> 接收全量消息能力：当**群主**设定允许该机器人接收群内全部消息时，
> 机器人可接收到群内所有成员在群内的发言消息。

### 两个前提条件（任一不满足都收不到全量消息）

1. **平台侧**：主体需有全量模式权限（目前**企业开发者灰度**，个人认证待开放）
2. **群主侧**：群主要在该群的机器人设置里，允许"接收群内全部消息"
   （入口在**手机 QQ → 群设置 → 机器人设置**，是**群主**的开关，
   不是开发者后台的配置项）

**所以：如果机器人是个人主体，群里那个「获取群内全部消息」开关
可能根本不存在，或者在开放平台勾了 `GROUP_MESSAGE_CREATE` 也不会推送。**

> 排查顺序：先确认主体类型 → 再看群主侧有没有该开关 → 最后看开放平台
> 回调配置是否勾选了 `GROUP_MESSAGE_CREATE`。

### 直接影响

| 想法 | 现实 |
| --- | --- |
| 「默默收集群里所有图」 | **当前做不到**（权限未开放）。只能收到 @机器人 时附带的图 |
| 「群消息太多要限流」 | 不需要。只有被 @ 的消息才会进来 |
| 「转发大批量会刷屏」 | 官方机器人场景下不成立，单次消息图不会太多 |

### 正确的心智模型（当前权限下）

```
用户想收图 -> 主动 @机器人 把图/聊天记录丢给它 -> 机器人处理
```

**是「用户主动触发」，不是「机器人被动监听」。**

> 注意：如果将来全量模式对个人主体开放，这个模型就要改回"被动监听"。
> 插件逻辑**不需要改**（收到消息就处理），只是能收到的消息范围变了。

### 与非官方协议的对比

| | 官方机器人 `qq_official_webhook` | 非官方 `aiocqhttp` / OneBot |
| --- | --- | --- |
| 群内全部消息 | ❌ 当前收不到（权限未开放） | ✅ 能收到 |
| 收集方式 | 用户主动 @ | 可默默收集 |
| 适用插件 | `astrbot_plugin_bqbq_collect` | 旧的 `bqbq` 插件 |

本项目两套机器人并存，**不要混淆它们的能力边界**。

### ⚠️ 私聊 vs 群聊：结构完全不同（实测必看）

这是**最容易踩坑的地方** —— 两者不只是"有没有群号"的差别，
组件构成、文本内容、`raw_data` 字段都不一样。

| 字段 | **私聊** | **群聊（@机器人 / 引用）** |
| --- | --- | --- |
| `event.get_group_id()` | `''`（空） | 群 openid（如 `68F5C2...`） |
| `raw_message_type` | `0` | **`103`**（引用消息） |
| **components** | `[At, Plain, Image]` | `[Reply, At, Plain]` |
| **image 在哪** | 顶层 `Image` | 在 **`Reply.chain`** 里 |
| **`message_str`** | `''` 或 `'[表情]'` | `'bqbq收图'`（用户打的字） |
| `raw_data` 键 | 含 `attachments` | 含 `group_id`/`msg_elements` |

#### 两个直接后果

**① 私聊消息没有文字 → 不能用触发词把关**

私聊发图的 `message_str` 是空串或 `[表情]`，**根本没有用户输入的文字**。
若强制要求触发词，私聊会永远收不到。

**② 群聊的图片藏在 `Reply.chain` 里**

群聊要 @机器人 才会推送，若用户是"引用一张图 + @机器人"，
图片在 `Reply.chain` 而非顶层，`event.get_messages()` 直接过滤 `Image` 会漏掉。

#### 所以判断逻辑要分开

```python
is_private = not event.get_group_id()

# 私聊：发图即收（用户主动发图 = 明确意图）
# 群聊：必须带触发词（@机器人 可能只是顺便说话）
if not is_private and not self._has_trigger(text):
    return False
```

#### 取图的正确姿势（两者都要覆盖）

```python
# 顶层 Image（私聊走这条）
images = [c for c in event.get_messages() if type(c).__name__ == "Image"]
# 引用链里的 Image（群聊引用走这条）
images += self._reply_chain_images(event)
```

> 实测 `Reply.chain` 里的 `Image` 与顶层 `Image` **机制完全相同**
> （框架 `preprocess_stage` 对两者都做了本地化），所以可以共用同一套处理逻辑。

### ⚠️ 想做「私聊白名单」？只能用 openid，不能用 QQ 号

官方机器人拿不到 QQ 号 —— `event.get_sender_id()` 返回的是 **openid**
（形如 `A22C9E2359E63789C8E775ECD4A373B3`）。

而且 openid **无法反推 QQ 号**。实测 6 种方法全部失败：

| 方法 | 结果 |
| --- | --- |
| protobuf 解析 | ❌ 不是合法 protobuf |
| `md5(QQ号)` / `sha1(QQ号)` | ❌ 0 命中 |
| `md5("QQ"+号)` / `md5("qq_"+号)` | ❌ 0 命中 |
| base64 解码 | ❌ 得到 24 字节二进制，无可读内容 |
| 字节反转 / XOR 0xFF | ❌ 无意义 |
| 当 u64 时间戳 | ❌ 19-20 位天文数字 |

> **方法论提醒**：16 字节的随机数据有约 **1.6%** 概率碰巧构成合法的
> protobuf tag 序列（实测 1000 个随机 hex，16 个"解析成功"）。
> 所以"能解析"**不等于**"它是 protobuf"。
> 对比 `fileid` 破解成功是因为字段**有可验证语义**
> （`f2 == SHA1(内容)`、`f3 == 文件大小`，均 7/7 验证）。

官方文档也明确（[API 调用指南](https://bot.q.qq.com/wiki/develop/api-v2/dev-prepare/api-call-guide.html)）：

> 不同的 `bot(AppID)` 获取到的用户 `openid`，群 `openid`，频道 `openid` **均不相同**

说明 `openid = f(QQ号, AppID密钥)`，**密钥在腾讯服务端**。
若只是 `hash(QQ号)`，任何人都能撞库验证 —— 这正违背 openid 的设计目的。

**所以白名单只能填 openid。** 好在同一 bot 下它是稳定的。

⚠️ **换 bot（AppID 变了）后 openid 会变，需要重新填写白名单。**

#### 获取 openid 用「绑定命令」，不要让管理员翻日志

```python
@filter.command("bqbq绑定")
async def cmd_bind(self, event):
    sender = event.get_sender_id()          # 这就是 openid
    yield event.plain_result(f"你的 openid：\n{sender}")
```

用户自己发一次命令，机器人把 openid 回给他，他再转给管理员。
比翻日志方便得多，也不用管理员代查。

**安全性**：openid 只对当前这一个 bot 有效，不是 QQ 号，
泄露给第三方也无法用于别处，所以直接回复给请求者是安全的。

配套再加一个管理员命令查看白名单（**脱敏显示**，避免群里暴露他人 openid）：

```python
@filter.command("bqbq白名单")
async def cmd_whitelist(self, event):
    if not self._is_admin(event):      # event.role == "admin"
        yield event.plain_result("只有管理员可以查看白名单")
        return
    # 只显示 前缀…后缀
```

### 附：其它相关平台限制

来自官方 FAQ：

- **只能加自己当群主/管理员的群**（个人主体）
- **未认证**：机器人仅管理员可用，且只能加到管理员当群主的群
- **个人认证**：可公开使用，进群上限 500 个
- **企业认证**：所有场景均可公开使用

---

## 一、`should_call_llm()` 的参数是反的 ⚠️ 最容易错

### 现象

群里的表情包消息处理完后，机器人报：

```
LLM 请求失败：未找到任何可用的对话模型（提供商）。请先在 WebUI 中配置并启用可用模型。
```

### 根因：方法名 / docstring / 实际行为三者矛盾

```python
# astr_message_event.py:94
self.call_llm = False                      # 默认值

# astr_message_event.py:372
def should_call_llm(self, call_llm: bool) -> None:
    """是否在此消息事件中【禁止】默认的 LLM 请求。"""   # 说"禁止"
    self.call_llm = call_llm                            # 参数却叫 call_llm

# stage.py:56-60  ← 消费端才是真相
if (
    not event._has_send_oper
    and event.is_at_or_wake_command
    and not event.call_llm          # ← 注意这个 not
):
    # 调用 LLM
```

### 结论

| 调用 | `call_llm` | `not call_llm` | 是否调 LLM |
| --- | --- | --- | --- |
| 默认 | `False` | `True` | **会调** |
| `should_call_llm(False)` | `False` | `True` | **仍会调** ❌ |
| **`should_call_llm(True)`** | `True` | `False` | **跳过** ✅ |

**要禁止 LLM，必须传 `True`。**

### 教训

用不熟悉的 API 时，**必须找到它的消费点看实际判断逻辑**，
不能只信方法名和 docstring。

---

## 二、`stage.py` 的完整判断有**四个**条件

只盯着 `call_llm` 会漏掉别的阻断路径。完整逻辑：

```python
# stage.py:52-66
if not self.ctx.astrbot_config["provider_settings"].get("enable", True):
    return

if (
    not event._has_send_oper          # A：没发过消息
    and event.is_at_or_wake_command   # B：被 @ / 唤醒
    and not event.call_llm            # C：call_llm 为 False
):
    if ((event.get_result() and not event.is_stopped()) or not event.get_result()):  # D
        async for _ in self.agent_sub_stage.process(event):
            yield
```

### 隐藏条件 A：`_has_send_oper`

```python
# astr_message_event.py:297 / 500
async def send(...):
    self._has_send_oper = True     # ← 发过消息就置 True
```

**发消息的插件（如 `astrbot_plugin_resolver2`）根本不需要碰 `should_call_llm`** ——
它 `yield event.plain_result(...)` 后 `_has_send_oper=True`，条件 A 自然不成立。

### 三种阻断手段对比

| 做法 | 能否阻断 | 评价 |
| --- | --- | --- |
| **`should_call_llm(True)`** | ✅ | **最合适**：精准，不影响其它插件 |
| `stop_event()` | ✅ | 也能阻断（走条件 D），但会终止**整个事件传播**，可能挡住别的插件 |
| `send()` 发消息 | ✅ | `resolver2` 的方式；但纯收集插件不需要发消息 |

**纯收集型插件（静默入库、不发消息）必须用 `should_call_llm(True)`。**

---

## 三、框架会把图片**下载到本地**并覆盖组件字段 ⚠️ 极隐蔽

### 完整数据流（dump 原始 payload 实测）

```
① 适配器 _append_attachments
   Image(url="", file="https://multimedia.nt.qq.com.cn/download?...")
                                                    ↑ 原 URL 在这

② 框架 preprocess_stage/stage.py:130-137
   elif isinstance(component, Image):
       image_path = await component.convert_to_file_path()   # ← 自动下载
       component.file = image_path
       component.path = image_path
       component.url  = image_path      # ← 原 URL 被覆盖，丢失

③ 插件收到
   Image(url="C:\\...\\data\\temp\\media_image_2026...jpg",
         file=同上, path=同上)
```

### 后果

- 组件的 `url` 是**本地路径**，不是 http 地址
- 拿它去 `httpx.get()` 会抛 **`UnsupportedProtocol`**
- 但**图片其实已经在本地了**，直接读文件即可

### 正确做法

```python
# 优先读本地（框架已下载好）
local = self._extract_local_path(comp)     # 检查 path/file/url 是否是存在的本地文件
if local:
    data = Path(local).read_bytes()        # 零网络请求
else:
    url = self._extract_http_url(comp)     # 兜底：才走网络
```

### 验证方法

框架下载的文件大小与 QQ 给的 `size` 一致，内容 md5 与 QQ 的文件名一致：

```
media_image_20261010180718748_01b3.jpg
    190943 字节  =  raw_attachments.size: 190943   ✅
    md5 = 23b61732166ad8bfc8f2826d25995953
    QQ 文件名 = 23B61732166AD8BFC8F2826D25995953.jpg   ✅
```

### 反例：合并转发**不会**被本地化

```
普通消息: components = [At, Plain, Image]      ← 有 Image，会被本地化
合并转发: components = [At, Plain]             ← 没有 Image
          append_attachments count=0           ← 附件是空的
```

因为 `preprocess_stage` **只处理 `Image`/`Record` 组件，不碰 `Plain` 文本**，
而合并转发的图片藏在 `Plain.text` 里（`[附件1] ... URL:https://...`）。

**所以合并转发只能走网络下载。**

---

## 四、`Image.fromURL()` 把地址存进 `.file`，不是 `.url`

```python
img = Image.fromURL("https://x/y.jpg")
img.url   # ''
img.file  # 'https://x/y.jpg'      ← 在这
img.path  # ''
```

所以取值要 `comp.url or comp.file`，不能只看 `.url`。

---

## 五、解析逐行文本时**绝不能开 `re.DOTALL`**

### 反例（我犯过）

```python
_RE_ATTACH = re.compile(
    r"文件名:(?P<name>[0-9A-Fa-f]{32})\.(?P<ext>[A-Za-z0-9]+)"
    r"(?P<mid>.*?)"                    # ← . 在 DOTALL 下跨行
    r"URL:(?P<url>https?://\S+)",
    re.DOTALL,                         # ← 元凶
)
```

### 危害：张冠李戴

```
第1条：【附件1】文件名:AAA...gif （无 URL）
第2条：【附件1】文件名:BBB...gif URL:https://a/2

旧正则解析 -> aaaaaaaa -> https://a/2      ❌ 第1条的 md5 配到了第2条的 URL
```

**后果**：md5 与图片内容不符，**污染数据库**。

### 修复

```python
r"[^\n]*?"      # 限定同一行，从根上杜绝跨行
# 并移除 re.DOTALL
```

### 教训

测试用例必须覆盖**"缺字段"**的情况。我第一版测试的样本每条都带 URL，
恰好绕过了这个 bug。

---

## 六、QQ 官方适配器的数据结构

### 合并转发 = 一段纯文本

框架**完全不解析**合并转发（`qqofficial_platform_adapter.py` 里搜
`forward|Forward|合并|node|Node` 零匹配），只把 QQ 渲染好的文本塞进 `content`：

```
[Parachutes的聊天记录]
=== 消息 1 ===
[消息类型] 合并转发消息
--- 第1条 ---
    [发送者] Parachutes
    [附件1] 类型:动图 文件名:83F73AFE....gif 尺寸:500x500 大小:1.8MB URL:https://...
--- 第2条 ---
    ...
```

关键字段：

| 结构 | 内容 |
| --- | --- |
| `raw_data.content` | **图片 URL 全在这里**（纯文本）✅ |
| `raw_data.message_scene.ext` | `["msg_idx=REFIDX_..."]` —— 无 URL |
| `raw_data.msg_elements` | `[]` —— 空 |
| `components` | `[At, Plain]` —— 无 `Node`/`Image` |

**有利条件**：文件名就是 MD5（32 位十六进制），可直接查重，**不用先下载**。

### 普通消息的 URL 结构

```
https://multimedia.nt.qq.com.cn/download?appid=1406&fileid=<b64>&rkey=<rkey>&spec=0
```

**`fileid` 解码后不是 md5**（实测 5/5 验证）：

```
EhRjgNXLLPb_Jc95AAlDlQjTvUZA8xiq...  ->  base64 解码 75 字节
    hex: 12 14 6380d5cb2cf6ff25cf790009439508d3bd4640f3...
              ↑↑ protobuf 前缀：12=field2, 14=len(20)
              后面是 20 字节 file_uuid，与本图 md5 无关
```

**含义**：普通消息**无法从 URL 反推 md5** → 无法用构造 URL 兜底。

### 两种失败信号完全不同，必须区分

| 来源 | 响应 | 含义 |
| --- | --- | --- |
| 原链接 `multimedia.nt.qq.com.cn` | `x-errno: -5503042` + body `{"retmsg":"file has expired"}` | rkey/会话过期 |
| 构造 URL `gchat.qpic.cn` | `x-errno: -6101` + **空 body** | 存储层无此对象 |

⚠️ **两种错误码都通过 `x-errno` 响应头返回**，只看 JSON body 会漏掉。

### 引用回复（`Reply` 组件）的数据结构

实测三种引用场景（`raw_message_type == 103` 才是引用）：

| 场景 | `Reply.chain` | 图片在哪 |
| --- | --- | --- |
| **引用一张图片** | `[Plain, Image]` | `chain[1]` 的 Image，**已被框架本地化** ✅ |
| **引用合并转发** | `[Plain]` | `chain[0].text` 里（33991 字符，含 `文件名:<md5>.gif` 与 URL）✅ |
| 引用一段文字 | `[Plain]` | 无图 |

**两种都能收**，但取法不同：

- 引用的**图片** → 走 Image 组件，与顶层图片**完全同一套逻辑**
  （框架 `preprocess_stage/stage.py:165-173` 专门处理了 `Reply.chain` 里的 Image）
- 引用的**合并转发** → 解析 `chain[0].text`，与顶层"直接转发聊天记录"格式一致，
  可**复用同一个正则解析器**

适配器源码位置：`qqofficial_platform_adapter.py:776-819`
（`is_quoted_message` → 取 `msg_elements[0].attachments` → 塞进 `quoted_chain` → 构造 `Reply`）

---

## 七、兜底下载：构造 `gchat.qpic.cn` URL

原链接 rkey 失效时的兜底手段：

```
https://gchat.qpic.cn/gchatpic_new/0/0-0-{MD5}/0/{MD5}.jpg
    ?term=255&is_origin=0&client_proto=qq&client_appid=537325647
    &client_type=android&client_ver=9.1.95&client_down_type=auto&client_aio_type=aio
```

- **实测命中率约 74%**
- 失败的换 6 种变体（改路径/扩展名/appid/is_origin）**全是 404**
  → 是服务端没有该对象，不是 URL 构造问题
- 该 URL **纯 MD5 构造、不含时效参数**，所以它没有"过期"概念

**因此：必须在收到消息时立刻转存。** 隔几小时再抢救，会损失约 26%。

---

## 八、回复结果的正确姿势

### ⚠️ 先决定：收集动作要不要触发词

**结论：私聊免触发词，群聊必须带 `bqbq收图`。**
（结构差异与判据详见第零章的「私聊 vs 群聊」）

```python
is_private = not event.get_group_id()
if not is_private and not self._has_trigger(text):
    return False        # 群聊要触发词；私聊直接放行
```

#### 触发词为什么不能是裸关键词

实测裸 `收图` 会误触发：

| 文本 | 裸 `收图` | `bqbq收图` |
| --- | --- | --- |
| `今天不收图了` | ❌ 误触发 | 不触发 ✅ |
| `我帮你收图片` | ❌ 误触发 | 不触发 ✅ |
| `这张图收图率很高` | ❌ 误触发 | 不触发 ✅ |

匹配用 `text.lower()` 做子串，所以大小写不敏感（`BQBQ收图` 也认）。

### 收集型插件必须主动回复

否则用户看到"机器人没反应"，**无法区分「群里没图」和「处理全挂了」**。

### 用生成器 yield

```python
@filter.event_message_type(filter.EventMessageType.ALL)
async def on_message(self, event: AstrMessageEvent):
    ...
    if handled:
        event.should_call_llm(True)      # 传 True！
        if msg:
            yield event.plain_result(msg)   # 有 yield 才是异步生成器
```

框架的 `call_handler()` 会：

```python
ready_to_call = handler(event, ...)
if inspect.isasyncgen(ready_to_call):    # 异步生成器 -> 逐个 yield
    ...
elif inspect.iscoroutine(ready_to_call): # 协程 -> await 一次
    ...
```

### 汇报"本条消息的增量"，不是累计值

```python
before = dict(self.stats)
... # 处理
delta = {k: self.stats[k] - before.get(k, 0) for k in self.stats}
self._last_report = delta
```

⚠️ **每个分支都要赋值！** 我曾在「普通消息」分支漏掉这行，
导致单图**永远不回复**（`_last_report` 一直是空 `{}` → `total==0` → 返回空串）。

### 回复条件：只要"处理过图片"就回复

```python
# 任何一项 > 0 就回复
if (new == 0 and dup == 0 and skip == 0 and fail == 0 and no_url == 0):
    return ""
```

- `new > 0` 新增了图
- `dup > 0` 上传后才知道重复（并发竞态）
- `skip > 0` 预查重命中，已存在
- `fail > 0` 下载/上传失败
- `no_url > 0` 组件没给出可用地址

### ⚠️ 为什么 `skip` 也要回复

**官方机器人当前只能收到【私聊】和【@机器人】的消息**（见第零章），
这两者都是**用户主动触发**的行为。

用户特意丢一张图过来，机器人不该毫无反应 ——
否则用户无法区分「收到了但已存在」和「压根没收到」。

**"skip 回复会刷屏"这个顾虑不成立**：收不到群内全量消息，
不会有大批量被动涌入。

> 想回到"只在有新增/失败时回复"：把 `skip == 0` 去掉即可。
> 不要再引入 `reply_when_no_new` 之类的开关 —— 那会变成死配置。

### 预查重让 `dup` 变得罕见

加了本地预查重后，重发同一张图会走 **`skip`**（连上传都省了），
而不是 `dup`。`dup` 只在并发竞态时出现。

| 路径 | md5 从哪来 | 命中时省掉 |
| --- | --- | --- |
| 普通单图 | 读本地文件后算 | **只省上传** |
| 合并转发 | 文本里直接有 | **下载 + 上传都省** |

---

## 九、调试方法：**先做钩子抓数据，别猜**

这几轮最大的教训。我基于源码推断出"URL 一定是 https"，
结果框架在中间偷偷做了本地化，推断完全错误。

### 有效的钩子写法

**① 钩住适配器的关键函数**（记录输入与输出）

```python
from astrbot.core.platform.sources.qqofficial import (
    qqofficial_platform_adapter as mod,
)
original = mod.QQOfficialPlatformAdapter._append_attachments

async def patched(msg, attachments):
    dump({"hook": "IN", "attachments": shrink(attachments)})
    result = await original(msg, attachments)
    dump({"hook": "OUT", "components": [dump_comp(c) for c in msg]})
    return result

mod.QQOfficialPlatformAdapter._append_attachments = staticmethod(patched)
```

**② 在事件层 dump 组件全字段 + `raw_data`**

```python
@filter.event_message_type(filter.EventMessageType.ALL, priority=200)
async def on_any(self, event: AstrMessageEvent):
    for c in event.get_messages():
        dump({f: getattr(c, f, None) for f in ("url", "file", "path", "_type")})
    raw = getattr(event.message_obj, "raw_message", None)
    dump(getattr(raw, "raw_data", None))
```

**③ 安全措施**

- 字符串超长截断（rkey/base64 会撑爆文件）
- 递归深度限制
- 文件超上限自动停写
- **只读**，不改业务逻辑

---

## 十、其它小坑

| 坑 | 说明 |
| --- | --- |
| `register()` 已废弃 | AstrBot 会自动识别 `Star` 子类，不需要 `@register` 装饰器 |
| `PlatformMetadata` 需要 3 个参数 | `name` / `description` / `id`（dataclass） |
| `AstrBotMessage` 需要 `type` | 构造测试事件时要设 `obj.type = MessageType.GROUP_MESSAGE` |
| 组件对象要有 `type` 属性 | 用真实组件类（`Image.fromURL`）而非 `type("Image",(),{})()` 伪造 |
| `MessageType` 位置 | `astrbot.core.platform.message_type` |
| 插件目录 | `AstrBot/data/plugins/<插件名>/`，需 `main.py` + `metadata.yaml` |
| 数据目录 | `StarTools.get_data_dir("<插件名>")` → `data/plugin_data/<插件名>/` |
| 改 `main.py` 后 | **必须重载插件**；`__pycache__` 的时间戳可用来确认是否已重载 |

---

## 附：本项目相关文件

| 文件 | 说明 |
| --- | --- |
| `data/plugins/astrbot_plugin_bqbq_collect/` | 正式插件 |
| `data/plugins/astrbot_plugin_bqbq_probe_single/` | 诊断钩子（保留调试用） |
| `C:\000soft\qqagent\probe_single.jsonl` | 钩子输出 |
| `docs/astrbot_probe_backup/` | 早期的合并转发结构诊断产物 |
