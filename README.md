# os_national_backend

OS National 后端 API 服务，为用户提供 AI 对话（旅行规划、角色扮演）及相关功能。

# 技术栈

- **Python**: 3.12（Conda env: `os_national`）
- **Flask**: 3.x
- **ORM**: SQLAlchemy（Flask-SQLAlchemy）
- **数据库**: MySQL（PyMySQL 驱动）
- **缓存**: Redis（邮箱验证码、流式消息上下文）
- **AI**: 腾讯云 ADP / DashScope（Application API / Generation API）
- **认证**: JWT（bcrypt 密码）
- **邮件**: SMTP

# 项目结构

```
os_national_backend/
├── app.py                      # Flask 应用入口，Blueprint 注册，/health
├── config.py                   # 配置类，环境变量读取
├── requirements.txt            # Python 依赖
├── .env.dev / .env.prod        # 环境配置模板
├── models/
│   ├── __init__.py            # db 实例 + 所有模型导出
│   ├── user.py                # User, UserInfo, File
│   ├── admin.py               # Admin, AdminInfo
│   ├── conversation.py        # ConversationSession, Message
│   ├── route.py               # Route
│   └── roleplay.py            # RoleplayCharacter, RoleplayCharacterDetail,
│                               # RoleplaySession, RoleplayMessage
├── api/
│   ├── __init__.py            # 导出所有 Blueprint
│   ├── user.py                # /user/* — 注册/登录/个人信息
│   ├── admin.py               # /admin/* — 管理员登录/个人信息
│   ├── email.py               # /email/* — 邮箱验证码
│   ├── file.py                # /file/* — 头像/图片上传/获取
│   ├── agent.py               # /agent/travel-route-plan/* — AI 旅行规划对话
│   ├── route.py               # /route/* — 路线收藏
│   ├── roleplay.py            # /agent/roleplay/* — 角色扮演对话
│   └── roleplay_admin.py      # /admin/roleplay/* — 角色管理
├── utils/
│   ├── jwt_utils.py           # JWT 生成/验证/装饰器（支持 role 区分）
│   ├── password_utils.py       # bcrypt 加密/验证
│   ├── email_utils.py         # 邮箱验证/SMTP 发送
│   ├── file_utils.py          # 文件处理/token（generate_file_token）
│   ├── ai_provider.py         # AI Provider 工厂（腾讯 ADP / DashScope）
│   └── redis_client.py        # Redis 所有 key 函数
├── scripts/
│   └── find_orphan_images.py  # 检查孤立图片脚本
└── docs/
    ├── api.md                 # API 文档
    └── db.md                  # 数据库文档
```

---

# 核心架构设计

## 请求处理流程

```
请求 → Flask Blueprint → JWT 验证 → 业务逻辑 → SQLAlchemy (MySQL)
                                      ↕
                                 Redis (Streams / 缓存 / 锁)
                                      ↕
                          AI Provider (Tencent ADP / DashScope)
```

## SSE 流式架构（Producer-Consumer 模式）

Agent 和 Roleplay 均采用 SSE（Server-Sent Events）流式响应，核心是**双进程分离**：

- **Consumer**：Flask HTTP 线程，负责接收请求、立即写入 DB 占位消息、返回 SSE Response 给前端。前端通过 fetch API 接收流式数据。
- **Producer**：后台 `threading.Thread`，负责调用 AI Provider 流式接口、写入 Redis（内容 + 事件流）。

两者通过 **Redis Stream** 通信：

| 存储类型 | Redis Key | 机制 | 用途 |
|---------|-----------|------|------|
| 内容缓存 | `stream_content:{mid}` | String，APPEND | 累加文本片段，持久化，可用于恢复 |
| 事件流 | `stream_events:{mid}` | Stream，XADD | content/done/error 事件，支持追尾消费 |
| 状态机 | `stream_state:{mid}` | Hash | running/done/error 状态，轮询检测完成 |
| 分布式锁 | `stream_producer:{sid}` | String，SET NX EX | 确保同一 sid 只有一个 Producer |
| AI session | `ai_session:{sid}` | String | DashScope session_id 缓存复用 |

**关键设计**：
- `stream_content` 和 `stream_events` 分离——内容用于恢复（一次性全量），事件用于追尾（增量消费）。
- Producer 写入 `append_stream_content`（APPEND）同时写入 `append_stream_event`（XADD），两者互不阻塞。
- Consumer 先发 `catchup`（全量内容），再从 `stream_last_event_id` 继续追尾新事件。
- 前端断开连接时 Producer 继续运行，写完后写入 `done` 事件；Consumer 的 XREAD 超时后自动退出。

## AI Provider 工厂模式

```
get_ai_provider(provider_name, api_key, app_id=None, model=None)
```

| Provider | 触发条件 | API | 上下文恢复 | 用途 |
|----------|---------|-----|-----------|------|
| `DashScopeApplicationProvider` | `provider=dashscope` + `app_id` | `Application.call()` | session_id（180天） | Agent 对话、Roleplay 角色对话 |
| `DashScopeGenerationProvider` | `provider=dashscope` + `model` | `Generation.call()` | 无 | AI 自动生成标题（首轮对话结束） |
| `TencentADPProvider` | `provider=tencent_adp` + `app_id` | SSE WSS API | MD5(sid) 确定性 conversationId | Agent 对话、Roleplay 角色对话 |
| `TencentADPGenerationProvider` | `provider=tencent_adp` + `model` | OpenAI SDK MaaS | 无 | AI 自动生成标题 |

**`chat_stream` 接口**（统一签名）：
```python
chat_stream(messages: list, sid: int, resume: bool = False, session_id: str | None = None)
```
- `sid`：强制传入会话 ID，用于生成确定性上下文标识
- `resume`：是否从当前 active session 恢复
- `session_id`：AI 提供商 session_id（可选）

**`InvalidAISessionError`**：DashScope 返回 400/401/404/422 且 message 含 session 关键词时抛出，触发调用方清除缓存 session_id 并用全量历史重试。

**Tencent ADP 特性**：
- 使用 SSE 流式协议，只处理 `text.delta` 事件
- 自动过滤 `thought` 类型消息（思考过程），只输出 `reply` 内容
- 新会话时支持 system prompt 注入（roleplay 场景）

## JWT 认证体系

共用同一套 JWT 机制（HS256 + JWT_SECRET），两种 token：

| Token 类型 | Payload | 用途 |
|-----------|---------|------|
| Auth Token | `{user_id, exp, iat}` | API 认证，`token_required` 装饰器验证 |
| Avatar Token | `{user_id, fid, exp, iat}` | 头像访问，`decode_avatar_token` 解码 |

## 配置体系

`Config` 类（非 Flask Config 对象），所有配置从 `.env` 读取：

| 分类 | 关键字段 |
|------|---------|
| Flask | `FLASK_ENV`, `HOST`, `PORT`, `FLASK_DEBUG` |
| MySQL | `MYSQL_HOST/PORT/USER/PASSWORD/DATABASE` |
| Redis | `REDIS_HOST/PORT/DB/PASSWORD` |
| SMTP | `SMTP_SERVER/PORT/USE_SSL/USERNAME/PASSWORD/SENDER` |
| JWT | `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRATION_HOURS` |
| File | `UPLOAD_FOLDER`, `MAX_AVATAR_SIZE`, `ALLOWED_AVATAR_EXTENSIONS` |
| AI | `AI_PROVIDER`, `AI_API_KEY`, `AI_APP_ID`, `AI_TITLE_MODEL` |
| Roleplay | `ROLEPLAY_APP_ID_GAME_EXPERT/ESPORTS_PLAYER/GAME_HERO`, `ROLEPLAY_APP_ID_MAP` |

---

# 数据模型层

## 用户模块（models/user.py）

### User

用户账户表。

| 字段 | 类型 | 说明 |
|------|------|------|
| uid | INT (PK) | 用户唯一标识 |
| username | VARCHAR(80) UNIQUE | 用户名 |
| email | VARCHAR(120) UNIQUE | 邮箱 |
| password_hash | VARCHAR(256) | bcrypt 加密密码 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

**设计要点**：JWT payload 只存 user_id，由 `token_required` 注入 `current_user_id`。bcrypt 密码存储，不明文传输。

---

### UserInfo

用户扩展信息，一对一关联 User（`uid` 主键 + FK）。

| 字段 | 类型 | 说明 |
|------|------|------|
| uid | INT (PK, FK) | 关联 User |
| avatar_id | INT (FK→files.fid) | 头像，ON DELETE SET NULL |
| gender | VARCHAR(10) | 性别 |
| age | INT | 年龄 |
| basic_info | TEXT | 基本信息 |
| bio | TEXT | 简介 |
| updated_at | DATETIME | 更新时间 |

---

## 管理员模块（models/admin.py）

### Admin

管理员账户表（结构与 User 完全对称）。

| 字段 | 类型 | 说明 |
|------|------|------|
| aid | INT (PK) | 管理员唯一标识 |
| username | VARCHAR(80) UNIQUE | 管理员用户名 |
| email | VARCHAR(120) UNIQUE | 管理员邮箱 |
| password_hash | VARCHAR(256) | bcrypt 加密密码 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

**设计要点**：JWT payload 包含 `role='admin'`，通过 `token_required(require_admin=True)` 区分管理员接口。

---

### AdminInfo

管理员扩展信息，一对一关联 Admin（`aid` 主键 + FK）。

| 字段 | 类型 | 说明 |
|------|------|------|
| aid | INT (PK, FK) | 关联 Admin |
| avatar_id | INT (FK→files.fid) | 头像，ON DELETE SET NULL |
| gender | VARCHAR(10) | 性别 |
| age | INT | 年龄 |
| basic_info | TEXT | 基本信息 |
| bio | TEXT | 简介 |
| updated_at | DATETIME | 更新时间 |

---

### File

纯文件存储表，**无 uid 字段**（不与 User 直接绑定）。供用户头像、角色头像等复用。

| 字段 | 类型 | 说明 |
|------|------|------|
| fid | INT (PK) | 文件唯一标识 |
| original_filename | VARCHAR(255) | 原始文件名 |
| secure_filename | VARCHAR(255) UNIQUE | 安全文件名（uuid.hex + 扩展名） |
| created_at | DATETIME | 上传时间 |
| updated_at | DATETIME | 更新时间 |

**设计要点**：`secure_filename` 全局唯一，通过 `uuid.uuid4().hex` 生成，保证文件命名安全。文件通过 `UserInfo.avatar_id` / `AdminInfo.avatar_id` / `RoleplayCharacterDetail.avatar_id` / `RoleplayCharacterDetail.images_id` 间接关联。

---

## 对话模块（models/conversation.py）

### ConversationSession

AI 对话会话。

| 字段 | 类型 | 说明 |
|------|------|------|
| sid | INT (PK) | 会话唯一标识 |
| uid | INT (FK) | 关联 User |
| title | VARCHAR(255) | 会话标题（AI 首轮自动生成，或用户手动编辑） |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

---

### Message

会话消息。

| 字段 | 类型 | 说明 |
|------|------|------|
| mid | INT (PK) | 消息唯一标识 |
| sid | INT (FK) | 所属会话 |
| role | VARCHAR(20) | `user` / `assistant` |
| content | TEXT | 消息内容（AI 流式输出完整存储） |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

**设计要点**：`assistant` 消息的 content 在 SSE 完成后一次性落盘。流式传输过程中通过 Redis 缓存，前端断开可从 `stream_content:{mid}` 恢复。

---

## 路线收藏模块（models/route.py）

### Route

反规范化存储（denormalized），在收藏时刻复制 `session.title` 和 `message.content`。

| 字段 | 类型 | 说明 |
|------|------|------|
| rid | INT (PK) | 收藏唯一标识 |
| uid | INT (FK) | 关联 User |
| mid | INT (FK→messages.mid) | 关联 assistant 消息 |
| title | VARCHAR(255) | 路线标题（复制自 session.title） |
| content | TEXT | 路线内容（复制自 message.content） |
| created_at | DATETIME | 创建时间 |

**设计要点**：收藏后用户可独立编辑 title/content，不影响原始会话数据。mid 确保关联性，ON DELETE CASCADE 防止孤立收藏。

---

## Roleplay 模块（models/roleplay.py）

### RoleplayCharacter

角色基础信息。

| 字段 | 类型 | 说明 |
|------|------|------|
| rid | INT (PK) | 角色唯一标识 |
| type | VARCHAR(20) | 类型：`game_expert`（电竞明星）/ `esports_player`（电竞选手）/ `game_hero`（游戏英雄） |
| name | VARCHAR(80) | 角色显示名 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

**角色类型说明**：

| type | 说明 | 场景示例 |
|------|------|---------|
| game_expert | 电竞明星 | 游戏攻略咨询、游戏推荐、玩法技巧 |
| esports_player | 电竞选手 | 电竞比赛分析、游戏技术指导、战术讨论 |
| game_hero | 游戏英雄 | 角色扮演对话、剧情互动、虚拟陪伴 |

---

### RoleplayCharacterDetail

角色详情，与 RoleplayCharacter 一对一。

| 字段 | 类型 | 说明 |
|------|------|------|
| rid | INT (PK, FK) | 关联 RoleplayCharacter |
| bio | TEXT | 角色简介 |
| phrases | TEXT | 名人名言/短语（JSON 数组，如 `["适度娱乐","沉迷伤身"]`） |
| avatar_id | INT (FK→files.fid) | 头像，ON DELETE SET NULL |
| images_id | TEXT | 图片 ID 数组（JSON 数组，如 `[1,2,3]`） |
| updated_at | DATETIME | 更新时间 |

---

### RoleplaySession

角色对话会话，**`(uid, rid)` 复合主键**，一个用户一个角色只有一个会话。

| 字段 | 类型 | 说明 |
|------|------|------|
| uid | INT (PK, FK) | 关联 User |
| rid | INT (PK, FK) | 关联 RoleplayCharacter |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

**唯一约束**：`UNIQUE(uid, rid)`，确保一个用户对一个角色只会有一个会话。

---

### RoleplayMessage

角色对话消息。

| 字段 | 类型 | 说明 |
|------|------|------|
| mid | INT (PK) | 消息唯一标识 |
| uid | INT (FK) | 关联 User |
| rid | INT (FK) | 关联 RoleplayCharacter |
| role | VARCHAR(20) | `user` / `assistant` |
| content | TEXT | 消息内容 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

**索引**：`INDEX(uid, rid)`，用于按用户+角色快速查询对话历史。

---

# API 层

## email_bp — `/email`

### POST /email/verification/send

发送 6 位邮箱验证码到 Redis，TTL 5 分钟（`VERIFICATION_CODE_EXPIRE=300`）。

**请求**：
```json
{ "email": "user@example.com" }
```

**响应**：
```json
{ "success": true, "message": "Verification code sent" }
```

**流程**：邮箱格式校验 → 生成 6 位随机码 → Redis SETEX → SMTP 发送。

---

## user_bp — `/user`

### POST /user/register

用户注册，流程：邮箱格式 → 验证码校验 → 密码长度 → User + UserInfo 创建 → JWT 返回。

**请求**：
```json
{
  "email": "user@example.com",
  "password": "secure_password",
  "verifyCode": "123456",
  "username": "optional_username"
}
```

**响应 (201)**：
```json
{
  "success": true,
  "token": "eyJhbGc...",
  "userInfo": { "uid": 1, "username": "user", "email": "user@example.com" }
}
```

---

### POST /user/login

支持 username 或 email 登录，bcrypt 验证后返回 JWT。

**请求**：
```json
{ "username": "user@example.com", "password": "password" }
// 或
{ "email": "user@example.com", "password": "password" }
```

**响应**：
```json
{
  "success": true,
  "token": "eyJhbGc...",
  "userInfo": { "uid": 1, "username": "user", "email": "...", "avatarToken": "..." }
}
```

---

### GET /user/profile

JWT 认证。返回完整用户信息，`avatarToken` 有头像时返回。

### PUT /user/profile

JWT 认证。增量更新（username/gender/age/basicInfo/bio），不传字段保持不变。

---

## file_bp — `/file`

### POST /file/avatar/upload

头像上传，multipart/form-data（`user_id` + `file`）。

**限制**：最大 2MB，格式 png/jpg/jpeg/gif/webp。

**替换逻辑**：
1. 查找旧头像 → 删除物理文件 + File 记录
2. 生成 `uuid.hex.{ext}` 安全文件名，保存到 `UPLOAD_FOLDER`
3. 创建 File 记录，更新 `UserInfo.avatar_id`
4. 返回 JWT avatar token（有效期同 JWT）

### GET /file/avatar/fetch?token=\<jwt\>

通过 Avatar Token 获取头像图片。JWT 解码取 `fid` → File 记录 → 物理文件存在检查 → `send_file` 配合正确 MIME。

---

## agent_bp — `/agent/travel-route-plan`

### GET /chat/list

JWT 认证。返回用户所有会话列表，含 `hasIncompleteMessage`（检查 Redis `stream:{sid}` 是否存在）。

### GET /chat/detail/:sid

JWT 认证。返回会话详情（含全部消息 + `incompleteMid`）。

### PUT /chat/title/edit/:sid

JWT 认证。编辑会话标题。

### POST /message

**核心 SSE 接口**，支持三种模式：

**正常发送**：
- `sid` 可选，不传则创建新 Session
- DB：立即写入 `user message` + `assistant placeholder`（空 content），commit
- 若 `existing_session && ai_session_id`：仅发送 `{"role": "user", "content}`，AI 用 session_id 关联上下文
- 后台 Producer 拉流，chunk 同时写入 Redis + SSE 推送给前端
- 首轮对话结束时调用 Generation API 自动生成标题（10～18字）

**恢复模式**（Redis 有进行中的流）：
- 先发 `catchup` 事件（`stream_content` 全量内容一次性推送）
- 再从 `stream_events` 最后一条继续追尾新 chunk

**重生成**（`regenerateMid`）：
- 校验旧消息是 assistant 且属于该用户会话
- 删除旧 assistant 消息，创建新 placeholder
- 从 DB 构建**全量消息历史**（`session_id=None`），重新拉流
- 若原消息是首轮 assistant，新消息也会重新生成标题

**SSE 事件类型**：`start` / `content` / `catchup` / `done` / `error` / `ping`（keepalive）

---

## route_bp — `/route`

### GET /list

JWT 认证。收藏列表（denormalized title/content）。

### GET /detail/:rid

JWT 认证。收藏详情含完整 content。

### POST /favorite

JWT 认证。按 `mid` 收藏，校验 assistant role + 用户所有权，复制 `session.title` + `message.content`。

### PUT /edit/:rid

JWT 认证。标题/内容独立编辑（均可选）。

### DELETE /delete/:rid

JWT 认证。删除收藏。

---

## roleplay_bp — `/agent/roleplay`

### GET /list/:type

JWT 认证。指定类型角色列表（`game_expert` / `esports_player` / `game_hero`），不含详情。

### GET /detail/:rid

JWT 认证。角色详情（含 bio、phrases JSON 数组、detailAvatarId）。

### POST /message/send/:rid

**SSE 流式对话**，向指定角色发送消息。

**架构特点**：
- **system prompt 动态注入**：`bio` + `phrases` 拼接，每次请求实时构建，不存库，注入到 messages 数组首位
- **ai_session_id 缓存复用**：Redis 缓存 `rp_stream:{uid}:{rid}:ai_session`，失败自动回退全量历史
- **支持重生成**：`regenerateMid` 参数，与 agent_bp 逻辑一致
- **恢复模式**：同 agent_bp，`catchup` + 追尾

### GET /message/list/:rid

JWT 认证。对话历史（按 `created_at` **升序**，含 `incompleteMid`）。

---

# Redis Key 设计

## AI 对话语境（stream:*）

| Key | 类型 | 用途 | TTL |
|-----|------|------|-----|
| `stream:{sid}` | String | 当前流式消息 MID | 3600s |
| `stream_content:{mid}` | String (APPEND) | 累加文本内容 | 3600s |
| `stream_events:{mid}` | Stream (XADD) | content/done/error 事件 | 3600s |
| `stream_state:{mid}` | Hash | running/done/error + message | 3600s |
| `stream_producer:{sid}` | String (SET NX EX) | 生产者分布式锁 | 3600s |
| `ai_session:{sid}` | String | AI session_id/conversation_id | 3600s |

## Roleplay 语境（rp_stream:{uid}:{rid}:*）

| Key | 类型 | 用途 | TTL |
|-----|------|------|-----|
| `rp_stream:{uid}:{rid}` | String | 当前流式消息 MID | 3600s |
| `rp_stream_content:{mid}` | String (APPEND) | 累加文本内容 | 3600s |
| `rp_stream_events:{mid}` | Stream (XADD) | 事件流 | 3600s |
| `rp_stream_state:{mid}` | Hash | running/done/error | 3600s |
| `rp_stream:{uid}:{rid}:producer` | String | 生产者锁 | 3600s |
| `rp_stream:{uid}:{rid}:ai_session` | String | AI session_id/conversation_id | 3600s |

## 邮箱验证码

| Key | 类型 | TTL |
|-----|------|-----|
| `email_verify:{email}` | String（6位验证码） | 300s |

---

# 工具层

## jwt_utils.py

- `generate_token(user_id)`：创建 JWT，payload = `{user_id, exp, iat}`
- `decode_token(token)`：验证并解码，失败返回 None
- `token_required`：Flask 装饰器，从 `Authorization: Bearer <token>` 提取，注入 `current_user_id` 到路由函数首个参数

## password_utils.py

bcrypt 加密/验证（`generate_password_hash` / `check_password_hash`）。

## email_utils.py

- `is_valid_email(email)`：正则校验
- `generate_verification_code()`：6 位随机数字符串
- `send_verification_email(to_email, code)`：SMTP 发送

## file_utils.py

- `allowed_avatar_file(filename)`：扩展名白名单校验
- `save_avatar_file(file)`：生成 `uuid.hex.{ext}` 安全文件名并保存
- `get_avatar_file_path(filename)`：返回完整物理路径
- `generate_avatar_token(user_id, fid)`：JWT Avatar Token
- `decode_avatar_token(token)`：解码取 fid

## ai_provider.py

- `get_ai_provider(provider_name, api_key, app_id=None, model=None)`：工厂函数
- `AIProvider`：抽象基类，定义 `chat_stream(messages, sid, resume, session_id)` / `chat_stream_resume` / `get_last_session_id`
- `DashScopeApplicationProvider`：Application API，`chat_stream` 支持 session_id 传递和 `InvalidAISessionError`
- `DashScopeGenerationProvider`：Generation API，`chat_non_stream()` 用于标题生成
- `TencentADPProvider`：ADP Agent API，SSE 流式，自动过滤 thought 消息，支持 system prompt
- `TencentADPGenerationProvider`：腾讯云 MaaS API（OpenAI SDK 兼容），`chat_non_stream()` 用于标题生成
- `InvalidAISessionError`：session 无效时抛出，触发调用方回退

---

# 数据库设计

## 时间戳策略

所有 DATETIME 字段统一使用：
```python
datetime.now(timezone.utc).replace(tzinfo=None)
```
UTC 时间不带时区，存储为 MySQL DATETIME（无时区信息），实际代表中国标准时间（UTC+8）。

## File 表无 uid 设计

File 表不与 User 直接绑定，改为**纯文件存储**。所有者通过以下方式间接关联：
- 用户头像：`UserInfo.avatar_id → files.fid`
- 角色头像：`RoleplayCharacter.avatar_id → files.fid`
- 角色详情头像：`RoleplayCharacterDetail.avatar_id → files.fid`

## ER 关系链

```
User (1) → UserInfo (1)
User (1) → ConversationSession (N) → Message (N) ← Route (N)
User (1) → RoleplaySession (N) ← RoleplayMessage (N)
RoleplayCharacter (1) → RoleplayCharacterDetail (1)
RoleplayCharacter (1) ← Route (N)  (via Message FK)
```

---

# 开发指南

## 1. 安装依赖

```bash
conda activate os_national
pip install -r requirements.txt
```

## 2. 配置环境变量

```bash
cp .env.dev .env   # 开发环境
# 或
cp .env.prod .env  # 生产环境
```

编辑 `.env` 配置 MySQL、Redis、SMTP、JWT、AI API Key 等。

## 3. 初始化数据库

```bash
flask init-db
```

## 4. 启动服务

```bash
python app.py
```

默认运行在 `http://localhost:5000`（或 `.env` 中配置的 HOST/PORT）。

---

# API 验收

## 健康检查

```bash
curl http://localhost:5000/health
```

## 用户注册与登录

```bash
# 发送验证码
curl -X POST http://localhost:5000/email/verification/send \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# 注册
curl -X POST http://localhost:5000/user/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "123456", "verifyCode": "123456"}'

# 登录
curl -X POST http://localhost:5000/user/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "123456"}'
```

## AI 对话（SSE）

```bash
# 发送消息（替换 <token> 为登录获取的 JWT）
curl -X POST http://localhost:5000/agent/travel-route-plan/message \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"content": "我想去云南旅行，5天时间推荐"}' \
  -N

# 获取会话列表
curl http://localhost:5000/agent/travel-route-plan/chat/list \
  -H "Authorization: Bearer <token>"
```

## Roleplay

```bash
# 角色列表
curl http://localhost:5000/agent/roleplay/list/game_expert \
  -H "Authorization: Bearer <token>"

# 角色详情
curl http://localhost:5000/agent/roleplay/detail/1 \
  -H "Authorization: Bearer <token>"

# 发送消息
curl -X POST http://localhost:5000/agent/roleplay/message/send/1 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"content": "你好，推荐一些 RPG 游戏"}' \
  -N
```

---

# 详细文档

- **API 文档**：[docs/api.md](docs/api.md)
- **数据库文档**：[docs/db.md](docs/db.md)
