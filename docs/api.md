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
  - [10. 发送消息（SSE 流式）](#10-发送消息sse-流式)
- [路线收藏接口](#路线收藏接口)
  - [11. 获取收藏列表](#11-获取收藏列表)
  - [12. 获取收藏详情](#12-获取收藏详情)
  - [13. 收藏路线](#13-收藏路线)
  - [14. 删除收藏](#14-删除收藏)
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
| createdAt            | string | 创建时间             |
| updatedAt            | string | 最后更新时间           |

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
| incompleteMid      | int/null | 未完成的流式消息 ID（可恢复） |

---

### 10. 发送消息（SSE 流式）

- **URL**: `POST /agent/travel-route-plan/message`
- **描述**: 发送消息给 AI，自动创建会话，SSE 流式返回响应
- **认证**: 需要 Bearer Token
- **返回**: `text/event-stream`

**请求**:

```
POST /agent/travel-route-plan/message
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "我想去云南旅行，5天时间",
  "sid": 1  // 可选，不传则创建新会话
}
```

| 字段      | 类型     | 必填 | 说明             |
|---------|--------|----|----------------|
| content | string | 是  | 消息内容           |
| sid     | int    | 否  | 会话 ID，不传则创建新会话 |

**SSE 响应格式**:

```
data: {"type": "start", "sid": 1, "mid": 123}

data: {"type": "content", "content": "云南"}
data: {"type": "content", "content": "5天"}
data: {"type": "content", "content": "推荐路线：第一天抵达昆明..."}

data: {"type": "done", "sid": 1, "mid": 123}
```

**说明**:
- `start`: 流开始，包含会话 ID 和消息 ID
- `content`: **实时增量发送**，每个 chunk 都单独发送一个 SSE 事件
- `done`: 流结束

**恢复模式**（检测到 Redis 有进行中的流）:

```
data: {"type": "start", "sid": 1, "mid": 123, "resume": true}

data: {"type": "content", "content": "...接上次未完成部分继续输出..."}
data: {"type": "content", "content": "...持续增量输出..."}

data: {"type": "done", "sid": 1, "mid": 123}
```

说明：恢复模式仍保持 stream 语义，服务端会尽量跳过已缓存前缀，仅继续推送剩余内容。

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
      "content": "云南5日游推荐路线：第一天抵达昆明...",
      "createdAt": "2026-03-27T10:00:00Z"
    }
  ]
}
```

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
    "createdAt": "2026-03-27T10:00:00Z"
  }
}
```

---

### 13. 收藏路线

- **URL**: `POST /route`
- **描述**: 收藏 AI 返回的路线（只提供 mid，后端自动复制 session.title 和 message.content）
- **认证**: 需要 Bearer Token

**请求**:

```
POST /route
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
  "route": {
    "rid": 1,
    "mid": 5,
    "title": "2026-03-27 10:30",
    "content": "云南5日游推荐路线：第一天抵达昆明...",
    "createdAt": "2026-03-27T10:00:00Z"
  }
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

### 14. 删除收藏

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
