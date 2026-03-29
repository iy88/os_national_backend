# API 文档

## 目录

- [用户认证](#用户认证)
  - [1. 发送邮箱验证码](#1-发送邮箱验证码)
  - [2. 用户注册](#2-用户注册)
  - [3. 用户登录](#3-用户登录)
- [用户信息](#用户信息)
  - [4. 获取用户信息](#4-获取用户信息)
  - [5. 更新用户信息](#5-更新用户信息)
- [文件接口](#文件接口)
  - [6. 上传头像](#6-上传头像)
  - [7. 获取头像](#7-获取头像)
- [Agent AI 接口](#agent-ai-接口)
  - [8. 获取会话列表](#8-获取会话列表)
  - [9. 获取会话详情](#9-获取会话详情)
  - [10. 编辑会话标题](#10-编辑会话标题)
  - [11. 发送消息（SSE 流式）](#11-发送消息sse-流式)
- [路线收藏接口](#路线收藏接口)
  - [12. 获取收藏列表](#12-获取收藏列表)
  - [13. 获取收藏详情](#13-获取收藏详情)
  - [14. 收藏路线](#14-收藏路线)
  - [15. 编辑收藏路线](#15-编辑收藏路线)
  - [16. 删除收藏](#16-删除收藏)
- [工具接口](#工具接口)
  - [健康检查](#健康检查)

## 用户认证

### 1. 发送邮箱验证码

- **URL**: `POST /email/verification/send`
- **描述**: 发送邮箱验证码到指定邮箱，验证码存储在 Redis 中，有效期 5 分钟

**请求**:

```json
{
  "email": "user@example.com"
}
```

**响应 (成功)**:

```json
{
  "success": true,
  "message": "Verification code sent"
}
```

**响应 (失败)**:

```json
{
  "success": false,
  "message": "Invalid email format"
}
```

---

### 2. 用户注册

- **URL**: `POST /user/register`
- **描述**: 注册新用户，需先发送邮箱验证码

**请求**:

```json
{
  "username": "optional_username",
  "email": "user@example.com",
  "verifyCode": "123456",
  "password": "secure_password"
}
```

| 字段         | 类型     | 必填 | 说明                              |
|------------|--------|----|---------------------------------|
| email      | string | 是  | 邮箱地址                            |
| password   | string | 是  | 密码（6-128 字符，明文传输，后端加密存储）        |
| verifyCode | string | 是  | 6 位邮箱验证码                        |
| username   | string | 否  | 用户名（3-80 字符），不填则使用 email @ 前的部分 |

**响应 (成功 - 201)**:

```json
{
  "success": true,
  "message": "Registration successful",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "userInfo": {
    "uid": 1,
    "username": "user",
    "email": "user@example.com"
  }
}
```

**响应 (失败)**:

```json
{
  "success": false,
  "message": "Invalid or expired verification code"
}
```

---

### 3. 用户登录

- **URL**: `POST /user/login`
- **描述**: 用户登录，返回 JWT token

**请求**:

```json
{
  "username": "user@example.com",
  "password": "secure_password"
}
```

或

```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

| 字段       | 类型     | 必填 | 说明          |
|----------|--------|----|-------------|
| username | string | 否* | 用户名或邮箱（二选一） |
| email    | string | 否* | 邮箱地址（二选一）   |
| password | string | 是  | 密码          |

**响应 (成功)**:

```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "userInfo": {
    "uid": 1,
    "username": "user",
    "email": "user@example.com",
    "avatarToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

**响应 (失败 - 401)**:

```json
{
  "success": false,
  "message": "Invalid credentials"
}
```

---

## 用户信息

### 4. 获取用户信息

- **URL**: `GET /user/profile`
- **描述**: 获取当前登录用户的详细信息
- **认证**: 需要 Bearer Token

**请求**:

```
GET /user/profile
Authorization: Bearer <token>
```

**响应 (成功)**:

```json
{
  "success": true,
  "userInfo": {
    "uid": 1,
    "username": "user",
    "email": "user@example.com",
    "gender": "男",
    "age": 25,
    "basicInfo": "基本信息",
    "bio": "简介",
    "avatarToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

| 字段          | 类型     | 说明                   |
|-------------|--------|----------------------|
| avatarToken | string | 头像 JWT token（有头像时返回） |

**响应 (失败 - 401)**:

```json
{
  "success": false,
  "message": "Token is missing"
}
```

---

### 5. 更新用户信息

- **URL**: `PUT /user/profile`
- **描述**: 批量（增量）更新当前用户信息，所有字段均为可选
- **认证**: 需要 Bearer Token

**请求**:

```
PUT /user/profile
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "new_username",
  "gender": "女",
  "age": 30,
  "basicInfo": "新基本信息",
  "bio": "新简介"
}
```

| 字段        | 类型     | 必填 | 说明               |
|-----------|--------|----|------------------|
| username  | string | 否  | 用户名（3-80 字符），需唯一 |
| gender    | string | 否  | 性别               |
| age       | int    | 否  | 年龄               |
| basicInfo | string | 否  | 基本信息             |
| bio       | string | 否  | 简介               |

**响应 (成功)**:

```json
{
  "success": true,
  "message": "Profile updated",
  "userInfo": {
    "uid": 1,
    "username": "new_username",
    "email": "user@example.com",
    "gender": "女",
    "age": 30,
    "basicInfo": "新基本信息",
    "bio": "新简介"
  }
}
```

**响应 (失败 - 401)**:

```json
{
  "success": false,
  "message": "Invalid token"
}
```

| 字段       | 类型     | 说明     |
|----------|--------|------|
| rid      | int    | 路线唯一标识 |
| mid      | int    | 关联消息 ID |
| title    | string | 路线标题   |
| content  | string | 路线内容   |
| createdAt | datetime | 创建时间  |
| updatedAt | datetime | 更新时间  |

**响应 (失败 - 409)**:

```json
{
  "success": false,
  "message": "Username already exists"
}
```

---

## 文件接口

### 6. 上传头像

- **URL**: `POST /file/avatar/upload`
- **描述**: 上传用户头像，如已有头像则替换旧头像（删除旧文件及记录）
- **Content-Type**: `multipart/form-data`

**请求**:

| 字段      | 类型     | 必填 | 说明    |
|---------|--------|----|-------|
| user_id | string | 是  | 用户 ID |
| file    | file   | 是  | 头像文件  |

**限制**:

- 文件大小：最大 2MB
- 支持格式：png, jpg, jpeg, gif, webp

**响应 (成功)**:

```json
{
  "success": true,
  "message": "Avatar uploaded",
  "avatar_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**响应 (失败 - 400)**:

```json
{
  "success": false,
  "message": "Invalid file type"
}
```

**响应 (失败 - 413)**:

```json
{
  "success": false,
  "message": "File too large"
}
```

---

### 7. 获取头像

- **URL**: `GET /file/avatar/fetch?token=<avatar_token>`
- **描述**: 根据 avatar token 获取头像图片
- **返回**: 图片二进制数据，MIME 类型

**请求**:

```
GET /file/avatar/fetch?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**响应**: 图片二进制数据

**响应 (失败 - 401)**:

```json
{
  "success": false,
  "message": "Invalid or expired token"
}
```

**响应 (失败 - 404)**:

```json
{
  "success": false,
  "message": "Avatar not found"
}
```

---

## 工具接口

### 健康检查

- **URL**: `GET /health`
- **描述**: 服务健康检查

**响应**:

```json
{
  "status": "ok"
}
```

---

## Agent AI 接口

### 8. 获取会话列表

- **URL**: `GET /agent/travel-route-plan/chat/list`
- **描述**: 获取当前用户的所有 AI 对话会话列表
- **认证**: 需要 Bearer Token

**请求**:

```
GET /agent/travel-route-plan/chat/list
Authorization: Bearer <token>
```

**响应 (成功)**:

```json
{
  "success": true,
  "sessions": [
    {
      "sid": 1,
      "title": "2026-03-27 10:30",
      "hasIncompleteMessage": true,
      "createdAt": "2026-03-27T10:00:00Z",
      "updatedAt": "2026-03-27T10:30:00Z"
    }
  ]
}
```

| 字段                   | 类型     | 说明               |
|----------------------|--------|------------------|
| sid                  | int    | 会话唯一标识           |
| title                | string | 会话标题（暂时用时间戳）     |
| hasIncompleteMessage | bool   | 是否有未完成的流式消息（可恢复） |
| createdAt            | datetime | 创建时间             |
| updatedAt            | datetime | 最后更新时间           |

---

### 9. 获取会话详情

- **URL**: `GET /agent/travel-route-plan/chat/detail/:sid`
- **描述**: 获取指定会话的详细信息（含消息历史）
- **认证**: 需要 Bearer Token

**请求**:

```
GET /agent/travel-route-plan/chat/detail/1
Authorization: Bearer <token>
```

**响应 (成功)**:

```json
{
  "success": true,
  "session": {
    "sid": 1,
    "title": "2026-03-27 10:30",
    "messages": [
      {"mid": 1, "role": "user", "content": "我想去云南", "createdAt": "2026-03-27T10:00:00Z"},
      {"mid": 2, "role": "assistant", "content": "云南推荐路线...", "createdAt": "2026-03-27T10:00:05Z"}
    ],
    "incompleteMid": null,
    "createdAt": "2026-03-27T10:00:00Z",
    "updatedAt": "2026-03-27T10:00:05Z"
  }
}
```

| 字段                 | 类型       | 说明               |
|--------------------|----------|------------------|
| messages           | array    | 消息列表             |
| messages[].mid     | int      | 消息 ID            |
| messages[].role    | string   | user / assistant |
| messages[].content | string   | 消息内容             |
| messages[].createdAt | datetime | 消息创建时间         |
| messages[].updatedAt | datetime | 消息更新时间         |
| incompleteMid      | int/null | 未完成的流式消息 ID（可恢复） |

---

### 10. 编辑会话标题

- **URL**: `PUT /agent/travel-route-plan/chat/title/edit/:sid`
- **描述**: 编辑指定会话的标题
- **认证**: 需要 Bearer Token

**请求**:

```
PUT /agent/travel-route-plan/chat/title/edit/1
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "新标题"
}
```

| 字段   | 类型     | 必填 | 说明   |
|-------|--------|----|------|
| title | string | 是  | 新标题 |

**响应 (成功)**:

```json
{
  "success": true,
  "session": {
    "sid": 1,
    "title": "新标题",
    "createdAt": "2026-03-27T10:00:00Z",
    "updatedAt": "2026-03-27T12:00:00Z"
  }
}
```

| 字段       | 类型     | 说明   |
|----------|--------|------|
| sid      | int    | 会话 ID |
| title    | string | 会话标题 |
| createdAt | datetime | 创建时间 |
| updatedAt | datetime | 更新时间 |

**响应 (失败 - 404)**:

```json
{
  "success": false,
  "message": "Session not found"
}
```

---

### 11. 发送消息（SSE 流式）

- **URL**: `POST /agent/travel-route-plan/message`
- **描述**: 发送消息给 AI，自动创建会话，SSE 流式返回响应；也可指定 `regenerateMid` 重新生成某条 AI 回复
- **认证**: 需要 Bearer Token
- **返回**: `text/event-stream`

**请求（正常发送）**:

```
POST /agent/travel-route-plan/message
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "我想去云南旅行，5天时间",
  "sid": 1  // 可选，不传则创建新会话
}
```

| 字段      | 类型     | 必填 | 说明                          |
|---------|--------|----|-----------------------------|
| content | string | 是* | 消息内容（新会话/继续会话必填，恢复模式可不传） |
| sid     | int    | 否  | 会话 ID，不传则创建新会话            |

**请求（重新生成）**:

```
POST /agent/travel-route-plan/message
Authorization: Bearer <token>
Content-Type: application/json

{
  "sid": 1,
  "regenerateMid": 123
}
```

| 字段           | 类型 | 必填 | 说明                                       |
|--------------|----|----|------------------------------------------|
| sid          | int | 是  | 会话 ID                                    |
| regenerateMid | int | 是  | 要重新生成的 assistant 消息 ID             |
| content       | string | 否  | 重新生成模式下不传（忽略）                          |

**重新生成说明**：
- 传入 `regenerateMid` 时进入重生成模式，忽略 `content`
- `regenerateMid` 必须是该用户会话下的 assistant 消息
- 旧消息会被删除，用新消息替代
- 强制从数据库读取完整消息历史，不使用 AI session_id
- 若 `regenerateMid` 是该会话第一条 assistant 消息，则新消息也会重新生成标题

**SSE 响应格式**:

```
data: {"type": "start", "sid": 1, "mid": 123}

data: {"type": "content", "content": "云南"}
data: {"type": "content", "content": "5天"}
data: {"type": "content", "content": "推荐路线：第一天抵达昆明..."}

: ping
data: {"type": "done", "sid": 1, "mid": 123, "title": "云南5日游推荐"}
```

**说明**:
- `start`: 流开始，包含会话 ID 和消息 ID
- `content`: **实时增量发送**，每个 chunk 都单独发送一个 SSE 事件
- `catchup`: 恢复模式专用，直接读取 Redis 缓存的全量内容一次性推送
- `error`: 发生错误时发送，**错误消息会落盘到数据库**；随后仍会发送 `done` 事件结束流
- `done`: 流结束，**第一轮对话/重新生成完成时 payload 包含 `title` 字段**（自动生成的会话标题，10～18字）；错误处理完成后也会发送 `done`
- `ping`: 服务端 keepalive 注释行（`:` 开头），客户端无需处理，代理也不会缓冲

**错误处理**：

| 错误类型 | 错误消息 | 说明 |
|---------|---------|------|
| AI 生成失败 | API 返回的原始错误信息或"生成失败，请稍后重试。" | 如 API 调用失败、无效 session 等 |
| 系统内部错误 | "系统内部错误，请稍后重试。" | 如数据库落盘失败、未分类异常 |

错误发生时，错误消息会**优先落盘到该条 assistant 消息**，再通过 SSE 通知前端，确保数据不丢失。

```
data: {"type": "error", "message": "生成失败，请稍后重试。"}
data: {"type": "done", "sid": 1, "mid": 123}
```

**恢复模式**（检测到 Redis 有进行中的流）:

```
data: {"type": "start", "sid": 1, "mid": 123, "resume": true}

data: {"type": "catchup", "content": "已完成的全部内容拼接..."}
data: {"type": "content", "content": "...继续输出新内容..."}

data: {"type": "done", "sid": 1, "mid": 123}
```

说明：恢复模式先发一次 `catchup` 事件将全量缓存内容一次性推送给前端（用于快速同步），随后继续追尾新产生的 chunk。Producer 意外中断时，会自动重启并继续。若消费者超过 120 秒无任何事件则判定超时，发送 error 事件后结束流。

---

## 路线收藏接口

### 11. 获取收藏列表

- **URL**: `GET /route/list`
- **描述**: 获取当前用户收藏的所有路线
- **认证**: 需要 Bearer Token

**请求**:

```
GET /route/list
Authorization: Bearer <token>
```

**响应 (成功)**:

```json
{
  "success": true,
  "routes": [
    {
      "rid": 1,
      "mid": 5,
      "title": "2026-03-27 10:30",
      "createdAt": "2026-03-27T10:00:00Z",
      "updatedAt": "2026-03-27T10:00:00Z"
    }
  ]
}
```

| 字段       | 类型     | 说明     |
|----------|--------|------|
| rid      | int    | 路线唯一标识 |
| mid      | int    | 关联消息 ID |
| title    | string | 路线标题   |
| createdAt | datetime | 创建时间  |
| updatedAt | datetime | 更新时间  |

---

### 12. 获取收藏详情

- **URL**: `GET /route/detail/:rid`
- **描述**: 获取指定收藏路线的详细信息
- **认证**: 需要 Bearer Token

**请求**:

```
GET /route/detail/1
Authorization: Bearer <token>
```

**响应 (成功)**:

```json
{
  "success": true,
  "route": {
    "rid": 1,
    "mid": 5,
    "title": "2026-03-27 10:30",
    "content": "云南5日游推荐路线：第一天抵达昆明...",
    "createdAt": "2026-03-27T10:00:00Z",
    "updatedAt": "2026-03-27T10:00:00Z"
  }
}
```

| 字段       | 类型     | 说明     |
|----------|--------|------|
| rid      | int    | 路线唯一标识 |
| mid      | int    | 关联消息 ID |
| title    | string | 路线标题   |
| content  | string | 路线内容   |
| createdAt | datetime | 创建时间  |
| updatedAt | datetime | 更新时间  |

---

### 13. 收藏路线

- **URL**: `POST /route/favorite`
- **描述**: 收藏 AI 返回的路线（只提供 mid，后端自动复制 session.title 和 message.content）
- **认证**: 需要 Bearer Token

**请求**:

```
POST /route/favorite
Authorization: Bearer <token>
Content-Type: application/json

{
  "mid": 5
}
```

| 字段  | 类型  | 必填 | 说明                            |
|-----|-----|----|-------------------------------|
| mid | int | 是  | 消息 ID（必须是 assistant role 的消息） |

**响应 (成功 - 201)**:

```json
{
  "success": true,
  "message": "Route favorited"
}
```

**响应 (失败 - 409)**:

```json
{
  "success": false,
  "message": "Already favorited"
}
```

---

### 14. 编辑收藏路线

- **URL**: `PUT /route/edit/:rid`
- **描述**: 编辑收藏路线的标题或内容
- **认证**: 需要 Bearer Token

**请求**:

```
PUT /route/edit/1
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "新标题",
  "content": "新内容"
}
```

| 字段     | 类型     | 必填 | 说明     |
|---------|--------|----|------|
| title   | string | 否  | 新标题   |
| content | string | 否  | 新内容   |

**响应 (成功)**:

```json
{
  "success": true,
  "route": {
    "rid": 1,
    "mid": 5,
    "title": "新标题",
    "content": "新内容",
    "createdAt": "2026-03-27T10:00:00Z",
    "updatedAt": "2026-03-27T12:00:00Z"
  }
}
```

| 字段       | 类型     | 说明     |
|----------|--------|------|
| rid      | int    | 路线唯一标识 |
| mid      | int    | 关联消息 ID |
| title    | string | 路线标题   |
| content  | string | 路线内容   |
| createdAt | datetime | 创建时间  |
| updatedAt | datetime | 更新时间  |

**响应 (失败 - 404)**:

```json
{
  "success": false,
  "message": "Route not found"
}
```

---

### 15. 删除收藏

- **URL**: `DELETE /route/delete/:rid`
- **描述**: 删除指定的收藏路线
- **认证**: 需要 Bearer Token

**请求**:

```
DELETE /route/delete/1
Authorization: Bearer <token>
```

**响应 (成功)**:

```json
{
  "success": true,
  "message": "Route deleted"
}
```
