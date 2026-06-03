# API 文档

## 目录

- [用户认证](#用户认证)
    - [1. 发送邮箱验证码](#1-发送邮箱验证码)
    - [2. 用户注册](#2-用户注册)
    - [3. 用户登录](#3-用户登录)
- [管理员认证](#管理员认证)
    - [4. 管理员登录](#4-管理员登录)
- [用户信息](#用户信息)
    - [5. 获取用户信息](#5-获取用户信息)
    - [6. 更新用户信息](#6-更新用户信息)
- [管理员信息](#管理员信息)
    - [7. 获取管理员信息](#7-获取管理员信息)
    - [8. 更新管理员信息](#8-更新管理员信息)
- [文件接口](#文件接口)
    - [9. 上传头像](#9-上传头像)
    - [10. 获取头像](#10-获取头像)
    - [11. 获取图片文件](#11-获取图片文件)
- [Agent AI 接口](#agent-ai-接口)
    - [12. 获取会话列表](#12-获取会话列表)
    - [13. 获取会话详情](#13-获取会话详情)
    - [14. 编辑会话标题](#14-编辑会话标题)
    - [15. 发送消息（SSE 流式）](#15-发送消息sse-流式)
- [路线收藏接口](#路线收藏接口)
    - [16. 获取收藏列表](#16-获取收藏列表)
    - [17. 获取收藏详情](#17-获取收藏详情)
    - [18. 收藏路线](#18-收藏路线)
    - [19. 编辑收藏路线](#19-编辑收藏路线)
    - [20. 删除收藏](#20-删除收藏)
- [Roleplay 角色扮演接口](#roleplay-角色扮演接口)
    - [21. 获取角色列表](#21-获取角色列表)
    - [22. 获取角色详情](#22-获取角色详情)
    - [23. 发送消息（SSE 流式）](#23-发送消息sse-流式)
    - [24. 获取对话列表](#24-获取对话列表)
- [Roleplay 管理员接口](#roleplay-管理员接口)
    - [25. 创建角色](#25-创建角色)
    - [26. 更新角色](#26-更新角色)
    - [27. 删除角色](#27-删除角色)
    - [28. Dashboard 统计](#28-dashboard-统计)
- [工具接口](#工具接口)
    - [29. 健康检查](#29-健康检查)
- [Travel Recommendation 接口（旅行推荐）](#travel-recommendation-接口旅行推荐)
    - [30. 获取旅行推荐列表（公共读，匿名）](#30-获取旅行推荐列表公共读匿名)
    - [31. 获取单条旅行推荐详情（公共读，匿名）](#31-获取单条旅行推荐详情公共读匿名)
- [Travel Recommendation 后台管理接口](#travel-recommendation-后台管理接口)
    - [32. 主表 CRUD](#32-主表-crud)
    - [33. 子表 CRUD](#33-子表-crud)

## 用户认证

### 1. 发送邮箱验证码

- **URL**: `POST /api/email/verification/send`
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

- **URL**: `POST /api/user/register`
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

- **URL**: `POST /api/user/login`
- **描述**: 用户登录，返回 JWT token（role='user'）

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

## 管理员认证

### 4. 管理员登录

- **URL**: `POST /api/admin/login`
- **描述**: 管理员登录，返回 JWT token（role='admin'）

**请求**:

```json
{
  "username": "admin",
  "password": "secure_password"
}
```

| 字段       | 类型     | 必填 | 说明     |
|----------|--------|----|--------|
| username | string | 是  | 管理员用户名 |
| password | string | 是  | 密码     |

**响应 (成功)**:

```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "userInfo": {
    "uid": 1,
    "username": "admin",
    "email": "admin@example.com",
    "avatarToken": "eyJ..."
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

### 5. 获取用户信息

- **URL**: `GET /api/user/profile`
- **描述**: 获取当前登录用户的详细信息
- **认证**: 需要 Bearer Token（user role）

**请求**:

```
GET /api/user/profile
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

### 6. 更新用户信息

- **URL**: `PUT /api/user/profile`
- **描述**: 批量（增量）更新当前用户信息，所有字段均为可选
- **认证**: 需要 Bearer Token（user role）

**请求**:

```
PUT /api/user/profile
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

## 管理员信息

### 7. 获取管理员信息

- **URL**: `GET /api/admin/profile`
- **描述**: 获取当前登录管理员的详细信息
- **认证**: 需要 Bearer Token（admin role）

**请求**:

```
GET /api/admin/profile
Authorization: Bearer <token>
```

**响应 (成功)**:

```json
{
  "success": true,
  "userInfo": {
    "uid": 1,
    "username": "admin",
    "email": "admin@example.com",
    "gender": "male",
    "age": 30,
    "basicInfo": "...",
    "bio": "...",
    "avatarToken": "eyJ..."
  }
}
```

**响应 (失败 - 401)**:

```json
{
  "success": false,
  "message": "Token is missing"
}
```

**响应 (失败 - 403)**:

```json
{
  "success": false,
  "message": "Admin access required"
}
```

---

### 8. 更新管理员信息

- **URL**: `PUT /api/admin/profile`
- **描述**: 批量（增量）更新当前管理员信息
- **认证**: 需要 Bearer Token（admin role）

**请求**:

```
PUT /api/admin/profile
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "new_admin_username"
}
```

| 字段       | 类型     | 必填 | 说明               |
|----------|--------|----|------------------|
| username | string | 否  | 用户名（3-80 字符），需唯一 |

**响应 (成功)**:

```json
{
  "success": true,
  "message": "Profile updated",
  "userInfo": {
    "uid": 1,
    "username": "new_admin_username",
    "email": "admin@example.com",
    "gender": "male",
    "age": 30,
    "basicInfo": "...",
    "bio": "...",
    "avatarToken": "eyJ..."
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

**响应 (失败 - 403)**:

```json
{
  "success": false,
  "message": "Admin access required"
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

### 9. 上传头像

- **URL**: `POST /api/file/avatar/upload`
- **描述**: 上传用户头像（从 JWT 获取 user_id），如已有头像则替换旧头像（删除旧文件及记录）
- **Content-Type**: `multipart/form-data`
- **认证**: 需要 Bearer Token（user role）

**请求**:

| 字段   | 类型   | 必填 | 说明   |
|------|------|----|------|
| file | file | 是  | 头像文件 |

**限制**:

- 文件大小：最大 2097152 字节（2MB）
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

### 10. 获取头像

- **URL**: `GET /api/file/avatar/fetch?token=<token>`
- **描述**: 根据 avatar token 获取头像图片
- **返回**: 图片二进制数据，MIME 类型

**请求**:

```
GET /api/file/avatar/fetch?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
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

### 11. 获取图片文件

- **URL**: `GET /api/file/image/fetch?token=<token>`
- **描述**: 根据 file token 获取图片文件（用于 roleplay 角色图片等）
- **返回**: 图片二进制数据，MIME 类型

**请求**:

```
GET /api/file/image/fetch?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
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
  "message": "Image not found"
}
```

---

## Agent AI 接口

### 12. 获取会话列表

- **URL**: `GET /api/agent/travel-route-plan/chat/list`
- **描述**: 获取当前用户的所有 AI 对话会话列表
- **认证**: 需要 Bearer Token（user role）

**请求**:

```
GET /api/agent/travel-route-plan/chat/list
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

| 字段                   | 类型       | 说明               |
|----------------------|----------|------------------|
| sid                  | int      | 会话唯一标识           |
| title                | string   | 会话标题（暂时用时间戳）     |
| hasIncompleteMessage | bool     | 是否有未完成的流式消息（可恢复） |
| createdAt            | datetime | 创建时间             |
| updatedAt            | datetime | 最后更新时间           |

---

### 13. 获取会话详情

- **URL**: `GET /api/agent/travel-route-plan/chat/detail/:sid`
- **描述**: 获取指定会话的详细信息（含消息历史）
- **认证**: 需要 Bearer Token（user role）

**请求**:

```
GET /api/agent/travel-route-plan/chat/detail/1
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
      {
        "mid": 1,
        "role": "user",
        "content": "我想去云南",
        "createdAt": "2026-03-27T10:00:00Z"
      },
      {
        "mid": 2,
        "role": "assistant",
        "content": "云南推荐路线...",
        "createdAt": "2026-03-27T10:00:05Z"
      }
    ],
    "incompleteMid": null,
    "createdAt": "2026-03-27T10:00:00Z",
    "updatedAt": "2026-03-27T10:00:05Z"
  }
}
```

| 字段                   | 类型       | 说明               |
|----------------------|----------|------------------|
| messages             | array    | 消息列表             |
| messages[].mid       | int      | 消息 ID            |
| messages[].role      | string   | user / assistant |
| messages[].content   | string   | 消息内容             |
| messages[].createdAt | datetime | 消息创建时间           |
| messages[].updatedAt | datetime | 消息更新时间           |
| incompleteMid        | int/null | 未完成的流式消息 ID（可恢复） |

---

### 14. 编辑会话标题

- **URL**: `PUT /api/agent/travel-route-plan/chat/title/edit/:sid`
- **描述**: 编辑指定会话的标题
- **认证**: 需要 Bearer Token（user role）

**请求**:

```
PUT /api/agent/travel-route-plan/chat/title/edit/1
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "新标题"
}
```

| 字段    | 类型     | 必填 | 说明  |
|-------|--------|----|-----|
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

| 字段        | 类型       | 说明    |
|-----------|----------|-------|
| sid       | int      | 会话 ID |
| title     | string   | 会话标题  |
| createdAt | datetime | 创建时间  |
| updatedAt | datetime | 更新时间  |

**响应 (失败 - 404)**:

```json
{
  "success": false,
  "message": "Session not found"
}
```

---

### 15. 发送消息（SSE 流式）

- **URL**: `POST /api/agent/travel-route-plan/message`
- **描述**: 发送消息给 AI，自动创建会话，SSE 流式返回响应；也可指定 `regenerateMid` 重新生成某条 AI 回复
- **认证**: 需要 Bearer Token（user role）
- **返回**: `text/event-stream`

**请求（正常发送）**:

```
POST /api/agent/travel-route-plan/message
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "我想去云南旅行，5天时间",
  "sid": 1  // 可选，不传则创建新会话
}
```

| 字段      | 类型     | 必填 | 说明                       |
|---------|--------|----|--------------------------|
| content | string | 是* | 消息内容（新会话/继续会话必填，恢复模式可不传） |
| sid     | int    | 否  | 会话 ID，不传则创建新会话           |

**请求（重新生成）**:

```
POST /api/agent/travel-route-plan/message
Authorization: Bearer <token>
Content-Type: application/json

{
  "sid": 1,
  "regenerateMid": 123
}
```

| 字段            | 类型     | 必填 | 说明                     |
|---------------|--------|----|------------------------|
| sid           | int    | 是  | 会话 ID                  |
| regenerateMid | int    | 是  | 要重新生成的 assistant 消息 ID |
| content       | string | 否  | 重新生成模式下不传（忽略）          |

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
- `done`: 流结束，**第一轮对话/重新生成完成时 payload 包含 `title` 字段**（自动生成的会话标题，10～18字）；错误处理完成后也会发送
  `done`
- `ping`: 服务端 keepalive 注释行（`:` 开头），客户端无需处理，代理也不会缓冲

**错误处理**：

| 错误类型      | HTTP 状态码 | 错误消息                                       | 说明                                    |
|-----------|----------|--------------------------------------------|---------------------------------------|
| 重新生成冲突    | 409      | "该消息正在重新生成中，请稍候再试"（code: REGENERATE_IN_PROGRESS） | 同一 `regenerateMid` 已有一个正在进行的重新生成请求    |
| AI 生成失败   | —        | API 返回的原始错误信息或"生成失败，请稍后重试。"                     | 如 API 调用失败、无效 session 等              |
| 系统内部错误    | —        | "系统内部错误，请稍后重试。"                               | 如数据库落盘失败、未分类异常                        |

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

说明：恢复模式先发一次 `catchup` 事件将全量缓存内容一次性推送给前端（用于快速同步），随后继续追尾新产生的 chunk。Producer
意外中断时，会自动重启并继续。若消费者超过 120 秒无任何事件则判定超时，发送 error 事件后结束流。

---

## 路线收藏接口

### 16. 获取收藏列表

- **URL**: `GET /api/route/list`
- **描述**: 获取当前用户收藏的所有路线
- **认证**: 需要 Bearer Token（user role）

**请求**:

```
GET /api/route/list
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

| 字段        | 类型       | 说明      |
|-----------|----------|---------|
| rid       | int      | 路线唯一标识  |
| mid       | int      | 关联消息 ID |
| title     | string   | 路线标题    |
| createdAt | datetime | 创建时间    |
| updatedAt | datetime | 更新时间    |

---

### 17. 获取收藏详情

- **URL**: `GET /api/route/detail/:rid`
- **描述**: 获取指定收藏路线的详细信息
- **认证**: 需要 Bearer Token（user role）

**请求**:

```
GET /api/route/detail/1
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

| 字段        | 类型       | 说明      |
|-----------|----------|---------|
| rid       | int      | 路线唯一标识  |
| mid       | int      | 关联消息 ID |
| title     | string   | 路线标题    |
| content   | string   | 路线内容    |
| createdAt | datetime | 创建时间    |
| updatedAt | datetime | 更新时间    |

---

### 18. 收藏路线

- **URL**: `POST /api/route/favorite`
- **描述**: 收藏 AI 返回的路线（只提供 mid，后端自动复制 session.title 和 message.content）
- **认证**: 需要 Bearer Token（user role）

**请求**:

```
POST /api/route/favorite
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

### 19. 编辑收藏路线

- **URL**: `PUT /api/route/edit/:rid`
- **描述**: 编辑收藏路线的标题或内容
- **认证**: 需要 Bearer Token（user role）

**请求**:

```
PUT /api/route/edit/1
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "新标题",
  "content": "新内容"
}
```

| 字段      | 类型     | 必填 | 说明  |
|---------|--------|----|-----|
| title   | string | 否  | 新标题 |
| content | string | 否  | 新内容 |

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

| 字段        | 类型       | 说明      |
|-----------|----------|---------|
| rid       | int      | 路线唯一标识  |
| mid       | int      | 关联消息 ID |
| title     | string   | 路线标题    |
| content   | string   | 路线内容    |
| createdAt | datetime | 创建时间    |
| updatedAt | datetime | 更新时间    |

**响应 (失败 - 404)**:

```json
{
  "success": false,
  "message": "Route not found"
}
```

---

### 20. 删除收藏

- **URL**: `DELETE /api/route/delete/:rid`
- **描述**: 删除指定的收藏路线
- **认证**: 需要 Bearer Token（user role）

**请求**:

```
DELETE /api/route/delete/1
Authorization: Bearer <token>
```

**响应 (成功)**:

```json
{
  "success": true,
  "message": "Route deleted"
}
```

---

## Roleplay 角色扮演接口

### 角色类型说明

| type           | 说明   | 场景示例               |
|----------------|------|--------------------|
| game_expert    | 电竞明星 | 游戏攻略咨询、游戏推荐、玩法技巧   |
| esports_player | 电竞选手 | 电竞比赛分析、游戏技术指导、战术讨论 |
| game_hero      | 游戏英雄 | 角色扮演对话、剧情互动、虚拟陪伴   |

### 21. 获取角色列表

- **URL**: `GET /api/agent/roleplay/list/:type`
- **描述**: 获取指定类型的角色列表（不含详情），支持分页和字段搜索
- **认证**: 需要 Bearer Token（user role）

**路径参数**:

| 参数   | 类型     | 必填 | 说明                                                           |
|------|--------|----|--------------------------------------------------------------|
| type | string | 是  | 角色类型：game_expert / esports_player / game_hero，或 `all` 表示全部类型 |

**查询参数**:

| 参数        | 类型     | 必填 | 说明                            |
|-----------|--------|----|-------------------------------|
| page      | int    | 否  | 页码（默认 1，< 1 时返回 400）          |
| page_size | int    | 否  | 每页数量（默认 10，最大 50，< 1 时返回 400） |
| search    | string | 否  | 搜索关键词，匹配 name 或 bio           |

**请求**:

```
GET /api/agent/roleplay/list/game_expert?page=1&page_size=10&search=游戏
Authorization: Bearer <token>
```

**响应 (成功)**:

```json
{
  "success": true,
  "characters": [
    {
      "rid": 1,
      "type": "game_expert",
      "name": "电竞明星小王",
      "bio": "10年游戏经验，专注RPG和策略游戏",
      "avatar_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "createdAt": "2026-03-27T10:00:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "page_size": 10
}
```

| 字段           | 类型       | 说明            |
|--------------|----------|---------------|
| rid          | int      | 角色唯一标识        |
| type         | string   | 角色类型          |
| name         | string   | 角色显示名         |
| bio          | string   | 角色简介          |
| avatar_token | string   | 头像 Token（JWT） |
| createdAt    | datetime | 创建时间          |
| total        | int      | 符合条件总数        |
| page         | int      | 当前页码          |
| page_size    | int      | 每页数量          |

**响应 (失败 - 400)**:

```json
{
  "success": false,
  "message": "Invalid character type"
}
```

**响应 (失败 - 400，参数异常)**:

```json
{
  "success": false,
  "message": "Invalid page or page_size"
}
```

---

### 22. 获取角色详情

- **URL**: `GET /api/agent/roleplay/detail/:rid`
- **描述**: 获取角色的详细信息（含简介、名言短语等）
- **认证**: 需要 Bearer Token（user role）

**请求**:

```
GET /api/agent/roleplay/detail/1
Authorization: Bearer <token>
```

**响应 (成功)**:

```json
{
  "success": true,
  "character": {
    "rid": 1,
    "type": "game_expert",
    "name": "电竞明星小王",
    "bio": "10年游戏经验，专注RPG和策略游戏",
    "phrases": [
      "游戏最重要的是体验过程",
      "适度娱乐，沉迷伤身"
    ],
    "images_token": [
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    ],
    "avatar_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "updatedAt": "2026-03-27T10:00:00Z",
    "createdAt": "2026-03-27T09:00:00Z"
  }
}
```

| 字段           | 类型       | 说明               |
|--------------|----------|------------------|
| rid          | int      | 角色唯一标识           |
| type         | string   | 角色类型             |
| name         | string   | 角色显示名            |
| bio          | string   | 角色简介             |
| phrases      | string[] | 名言/短语数组          |
| images_token | string[] | 图片 Token 数组（JWT） |
| avatar_token | string   | 头像 Token（JWT）    |
| updatedAt    | datetime | 详情更新时间           |
| createdAt    | datetime | 角色创建时间           |

**响应 (失败 - 404)**:

```json
{
  "success": false,
  "message": "Character not found"
}
```

---

### 23. 发送消息（SSE 流式）

- **URL**: `POST /api/agent/roleplay/message/send/:rid`
- **描述**: 向角色发送消息，SSE 流式返回响应；也可指定 `regenerateMid` 重新生成某条 AI 回复
- **认证**: 需要 Bearer Token（user role）
- **返回**: `text/event-stream`

**请求（正常发送）**:

```
POST /api/agent/roleplay/message/send/1
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "你好，我最近想玩一些RPG游戏，有什么推荐吗？"
}
```

| 字段      | 类型     | 必填 | 说明                       |
|---------|--------|----|--------------------------|
| content | string | 是* | 消息内容（新会话/继续会话必填，恢复模式可不传） |
| rid     | int    | 是  | 角色 ID（路径参数）              |

**请求（重新生成）**:

```
POST /api/agent/roleplay/message/send/1
Authorization: Bearer <token>
Content-Type: application/json

{
  "regenerateMid": 123
}
```

| 字段            | 类型     | 必填 | 说明                     |
|---------------|--------|----|------------------------|
| rid           | int    | 是  | 角色 ID（路径参数）            |
| regenerateMid | int    | 是  | 要重新生成的 assistant 消息 ID |
| content       | string | 否  | 重新生成模式下不传（忽略）          |

**重新生成说明**：

- 传入 `regenerateMid` 时进入重生成模式，忽略 `content`
- `regenerateMid` 必须是该用户该角色会话下的 assistant 消息
- 旧消息会被删除，用新消息替代
- 强制从数据库读取完整消息历史
- system prompt 会重新注入

**SSE 响应格式**:

```
data: {"type": "start", "uid": 1, "rid": 1, "mid": 123}

data: {"type": "content", "content": "你好！"}
data: {"type": "content", "content": "很高兴为你推荐..."}

: ping
data: {"type": "done", "uid": 1, "rid": 1, "mid": 123}
```

**说明**:

- `start`: 流开始，包含用户 ID、角色 ID 和消息 ID
- `content`: 实时增量发送
- `catchup`: 恢复模式专用
- `error`: 错误时发送，错误消息会落盘
- `done`: 流结束
- `ping`: keepalive

**错误处理**：与 Agent AI 接口相同（包含 `REGENERATE_IN_PROGRESS` 409 冲突）。

**恢复模式**：与 Agent AI 接口相同。

---

### 24. 获取对话列表

- **URL**: `GET /api/agent/roleplay/message/list/:rid`
- **描述**: 获取与角色的所有对话记录（按时间升序）
- **认证**: 需要 Bearer Token（user role）

**请求**:

```
GET /api/agent/roleplay/message/list/1
Authorization: Bearer <token>
```

**响应 (成功)**:

```json
{
  "success": true,
  "messages": [
    {
      "mid": 1,
      "role": "user",
      "content": "你好",
      "createdAt": "2026-03-27T10:00:00Z"
    },
    {
      "mid": 2,
      "role": "assistant",
      "content": "你好！有什么游戏问题可以问我",
      "createdAt": "2026-03-27T10:00:05Z"
    },
    {
      "mid": 3,
      "role": "user",
      "content": "推荐一些RPG游戏",
      "createdAt": "2026-03-27T10:01:00Z"
    },
    {
      "mid": 4,
      "role": "assistant",
      "content": "推荐《巫师3》、《老滚5》...",
      "createdAt": "2026-03-27T10:01:10Z"
    }
  ],
  "incompleteMid": null
}
```

| 字段                   | 类型       | 说明               |
|----------------------|----------|------------------|
| messages             | array    | 消息列表（按时间升序）      |
| messages[].mid       | int      | 消息 ID            |
| messages[].role      | string   | user / assistant |
| messages[].content   | string   | 消息内容             |
| messages[].createdAt | datetime | 消息创建时间           |
| incompleteMid        | int/null | 未完成的流式消息 ID（可恢复） |

**响应 (失败 - 404)**:

```json
{
  "success": false,
  "message": "Character not found"
}
```

---

## Roleplay 管理员接口

### 角色类型说明

| type           | 说明   | 场景示例               |
|----------------|------|--------------------|
| game_expert    | 电竞明星 | 游戏攻略咨询、游戏推荐、玩法技巧   |
| esports_player | 电竞选手 | 电竞比赛分析、游戏技术指导、战术讨论 |
| game_hero      | 游戏英雄 | 角色扮演对话、剧情互动、虚拟陪伴   |

### 25. 创建角色

- **URL**: `POST /api/admin/roleplay/create`
- **描述**: 创建新角色，支持同时上传头像和图片（均为可选）
- **认证**: 需要 Bearer Token（admin role）
- **Content-Type**: `application/json` 或 `multipart/form-data`

**请求（JSON）**:

```json
{
  "type": "game_expert",
  "name": "电竞明星小王",
  "bio": "10年游戏经验，专注RPG和策略游戏",
  "phrases": [
    "游戏最重要的是体验过程",
    "适度娱乐，沉迷伤身"
  ]
}
```

| 字段      | 类型       | 必填 | 说明                                            |
|---------|----------|----|-----------------------------------------------|
| type    | string   | 是  | 角色类型：game_expert / esports_player / game_hero |
| name    | string   | 是  | 角色显示名（3-80 字符）                                |
| bio     | string   | 否  | 角色简介                                          |
| phrases | string[] | 否  | 名言/短语数组                                       |

**请求（multipart/form-data）**:

| 字段      | 类型     | 必填 | 说明          |
|---------|--------|----|-------------|
| type    | string | 是  | 角色类型        |
| name    | string | 是  | 角色显示名       |
| bio     | string | 否  | 角色简介        |
| phrases | string | 否  | JSON 数组字符串  |
| avatar  | file   | 否  | 头像文件（可选）    |
| images  | file   | 否  | 图片文件（多选，可选） |

**限制**:

- 文件大小：最大 2097152 字节（2MB）
- 支持格式：png, jpg, jpeg, gif, webp

**响应 (成功 - 201)**:

```json
{
  "success": true,
  "message": "Character created",
  "character": {
    "rid": 1,
    "type": "game_expert",
    "name": "电竞明星小王",
    "bio": "10年游戏经验，专注RPG和策略游戏",
    "phrases": [
      "游戏最重要的是体验过程",
      "适度娱乐，沉迷伤身"
    ],
    "avatar_token": null,
    "images_token": [],
    "created_at": "2026-03-27T10:00:00Z"
  }
}
```

**响应 (失败 - 400)**:

```json
{
  "success": false,
  "message": "type and name are required"
}
```

**响应 (失败 - 400，文件过大)**:

```json
{
  "success": false,
  "message": "Avatar file too large, max size is 2097152 bytes"
}
```

**响应 (失败 - 403)**:

```json
{
  "success": false,
  "message": "Admin access required"
}
```

---

### 26. 更新角色

- **URL**: `PUT /api/admin/roleplay/<int:rid>/update`
- **描述**: 更新角色信息，支持 multipart/form-data（上传头像/图片）或 JSON，支持删除头像/图片
- **认证**: 需要 Bearer Token（admin role）
- **Content-Type**: `application/json` 或 `multipart/form-data`

**请求（JSON）**:

```json
{
  "name": "新角色名",
  "bio": "新简介",
  "phrases": [
    "新名言1",
    "新名言2"
  ],
  "delete_avatar": false,
  "delete_images_token": [
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  ]
}
```

| 字段                  | 类型       | 必填 | 说明                           |
|---------------------|----------|----|------------------------------|
| name                | string   | 否  | 角色显示名                        |
| bio                 | string   | 否  | 角色简介                         |
| phrases             | string[] | 否  | 名言/短语数组                      |
| avatar              | file     | 否  | 新头像文件（替换旧头像 multipart 专用）    |
| images              | file     | 否  | 新增图片文件（追加到现有列表 multipart 专用） |
| delete_avatar       | bool     | 否  | 是否删除头像（true 时删除）             |
| delete_images_token | string[] | 否  | 要删除的图片 token 列表（增量删除）        |

**请求（multipart/form-data）**:

| 字段                  | 类型     | 必填 | 说明                  |
|---------------------|--------|----|---------------------|
| name                | string | 否  | 角色显示名               |
| bio                 | string | 否  | 角色简介                |
| phrases             | string | 否  | JSON 数组字符串          |
| avatar              | file   | 否  | 新头像文件               |
| images              | file   | 否  | 新增图片文件（多选，可多次发送）    |
| delete_avatar       | string | 否  | `true` 时删除头像        |
| delete_images_token | string | 否  | 要删除的图片 token（可多次发送） |

**响应 (成功)**:

```json
{
  "success": true,
  "message": "Character updated",
  "character": {
    "rid": 1,
    "type": "game_expert",
    "name": "新角色名",
    "bio": "新简介",
    "phrases": [
      "新名言1",
      "新名言2"
    ],
    "avatar_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "images_token": [
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    ]
  }
}
```

**响应 (失败 - 404)**:

```json
{
  "success": false,
  "message": "Character not found"
}
```

**响应 (失败 - 400，文件过大)**:

```json
{
  "success": false,
  "message": "Avatar file too large, max size is 2097152 bytes"
}
```

或

```json
{
  "success": false,
  "message": "Image file too large, max size is 2097152 bytes"
}
```

**响应 (失败 - 403)**:

```json
{
  "success": false,
  "message": "Admin access required"
}
```

---

### 27. 删除角色

- **URL**: `DELETE /api/admin/roleplay/<int:rid>/delete`
- **描述**: 删除角色（需无关联会话），同时删除关联的头像和图片文件
- **认证**: 需要 Bearer Token（admin role）

**请求**:

```
DELETE /api/admin/roleplay/1/delete
Authorization: Bearer <token>
```

**响应 (成功)**:

```json
{
  "success": true,
  "message": "Character deleted"
}
```

**响应 (失败 - 404)**:

```json
{
  "success": false,
  "message": "Character not found"
}
```

**响应 (失败 - 409)**:

```json
{
  "success": false,
  "message": "Cannot delete character with active sessions"
}
```

**响应 (失败 - 403)**:

```json
{
  "success": false,
  "message": "Admin access required"
}
```

---

### 28. Dashboard 统计

- **URL**: `GET /api/admin/dashboard`
- **描述**: 后台主页大屏统计数据概览
- **认证**: 需要 Bearer Token（admin role）

**请求**:

```
GET /api/admin/dashboard
Authorization: Bearer <token>
```

**响应 (成功)**:

```json
{
  "success": true,
  "users": {
    "total": 1234,
    "today_new": 10
  },
  "characters": {
    "total": 12,
    "by_type": {
      "game_expert": 4,
      "esports_player": 4,
      "game_hero": 4
    }
  },
  "sessions": {
    "total": 5678,
    "travel": 4000,
    "roleplay": 1678
  },
  "messages": {
    "total": 23456,
    "travel": 18000,
    "roleplay": 5456
  },
  "routes": {
    "total": 890
  },
  "files": {
    "total": 345
  }
}
```

| 字段                 | 类型     | 说明                      |
|--------------------|--------|-------------------------|
| users.total        | int    | 用户总数                    |
| users.today_new    | int    | 今日新增用户                  |
| characters.total   | int    | 角色总数                    |
| characters.by_type | object | 各类型角色数量                 |
| sessions.total     | int    | 会话总数（travel + roleplay） |
| sessions.travel    | int    | 旅行规划会话数                 |
| sessions.roleplay  | int    | 角色扮演会话数                 |
| messages.total     | int    | 消息总数（travel + roleplay） |
| messages.travel    | int    | 旅行规划消息数                 |
| messages.roleplay  | int    | 角色扮演消息数                 |
| routes.total       | int    | 收藏路线总数                  |
| files.total        | int    | 文件总数                    |

**响应 (失败 - 403)**:

```json
{
  "success": false,
  "message": "Admin access required"
}
```

---

## 工具接口

### 29. 健康检查

- **URL**: `GET /health`
- **描述**: 服务健康检查

**响应**:

```json
{
  "status": "ok"
}
```

---

## Travel Recommendation 接口（旅行推荐）

首页 SVG 地图数据 + 后台管理。数据从 `os_national_frontend/src/data/cities.json` 迁移而来，原静态 JSON 字段被拆为 8 张表，公共读 API 返回结构与原 JSON 兼容（驼峰字段名 `eSportsInfo` / `travelTips` / `displayName` / `center` 保留）。

### 30. 获取旅行推荐列表（公共读，匿名）

- **URL**: `GET /api/travel/recommendation`
- **描述**: 获取所有启用的旅行推荐（首页地图 + 城市详情共用）
- **认证**: 无需认证

**响应**:

```json
{
  "success": true,
  "recommendations": [
    {
      "id": 1,
      "name": "西安 · 长安荣耀之旅",
      "displayName": "西安",
      "center": [108.95, 34.27],
      "players": [
        {"name": "一诺（徐必成）", "hero": "公孙离", "team": "成都AG超玩会", "desc": "..."}
      ],
      "heroes": [...],
      "eSportsInfo": ["🏆 ...", "..."],
      "food": ["..."],
      "travelTips": ["..."],
      "tasks": [{"title": "...", "desc": "...", "reward": "..."}],
      "recommendedRoutes": ["..."]
    }
  ]
}
```

只返回 `is_active=1` 的记录，按 `id ASC` 排序（与 cities.json 的 key 顺序一致）。

### 31. 获取单条旅行推荐详情（公共读，匿名）

- **URL**: `GET /api/travel/recommendation/<int:rec_id>`
- **认证**: 无需认证
- **响应**: 成功返回 `{success, recommendation: {...}}`；`is_active=0` 或不存在返回 404。

---

## Travel Recommendation 后台管理接口

管理 1 张主表 + 7 张子表。所有 endpoint 需要 **Bearer Token + admin 角色**。

**响应公共字段**：所有返回的推荐和子项都带 `createdAt` / `updatedAt`（ISO8601 + `Z` 后缀，UTC）。更新时由 SQLAlchemy `onupdate` 自动刷新 `updated_at` 字段（无需调用方手动传）。

### 32. 主表 CRUD

#### 32.1 列表

- `GET /api/admin/api/travel/recommendation?page=1&page_size=10&search=`
- 支持模糊搜索 `name` / `display_name`
- 返回 `{success, recommendations, total, page, page_size}`，默认按 `id DESC`
- 列表项结构（snake_case 字段 + camelCase 时间戳）：
  ```json
  {
    "id": 1, "name": "...", "display_name": "...", "center_lon": 108.95, "center_lat": 34.27,
    "is_active": true,
    "players": [...], "heroes": [...], "esports_info": [...], "foods": [...],
    "travel_tips": [...], "tasks": [...], "routes": [...],
    "createdAt": "2026-06-03T12:00:00Z", "updatedAt": "2026-06-03T12:34:56Z"
  }
  ```

#### 32.2 详情

- `GET /api/admin/api/travel/recommendation/<int:rec_id>`
- 返回 `{success, recommendation}`，含全部 7 张子表（同 32.1 的结构）

#### 32.3 创建

- `POST /api/admin/api/travel/recommendation`
- **必填**: `name`, `display_name`, `center_lon`, `center_lat`
- **可选**: `is_active`（默认 true）
- **子表字段**（任选）: `players[]`, `heroes[]`, `esports_info[]`, `foods[]`, `travel_tips[]`, `tasks[]`, `routes[]`
- 同一 `display_name` 重复时返回 409
- 响应 201 + `{success, recommendation}`，`createdAt` = `updatedAt` = 创建时刻

#### 32.4 整条更新

- `PUT /api/admin/api/travel/recommendation/<int:rec_id>`
- 仅更新 body 中**明确包含的字段**；子表数组若传入则**整体替换**（缺失则保留现有）
- 改 `display_name` 触发唯一约束校验
- 响应中 `updatedAt` 自动刷新为最新值；`createdAt` 保持不变

#### 32.5 删除

- `DELETE /api/admin/api/travel/recommendation/<int:rec_id>`
- FK ON DELETE CASCADE 自动清空 7 张子表

### 33. 子表 CRUD

7 张子表统一模式：`/api/admin/api/travel/recommendation/<int:rec_id>/<resource>[/<int:item_id>]`

每个返回的子项都带 `createdAt` / `updatedAt`（格式同主表）。`PUT` 更新子项时 `updatedAt` 自动刷新。

| 子表 | resource 路径 | 列表字段（除 createdAt / updatedAt 外） |
|------|-------------|----------|
| 推荐选手 | `players` | `id, recommendation_id, name, hero, team, description, display_order` |
| 推荐英雄 | `heroes` | `id, recommendation_id, name, role, style, description, display_order` |
| 电竞资讯 | `esports_info` | `id, recommendation_id, content, display_order` |
| 美食 | `foods` | `id, recommendation_id, content, display_order` |
| 旅行贴士 | `travel_tips` | `id, recommendation_id, content, display_order` |
| 打卡任务 | `tasks` | `[{id, recommendation_id, title, description, reward, display_order}]` |
| 推荐路线 | `routes` | `[{id, recommendation_id, content, display_order}]` |

每个 resource 支持 4 个操作：

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/admin/api/travel/recommendation/<rid>/<resource>` | 列出该推荐下所有子项（按 display_order ASC） |
| `POST` | `/api/admin/api/travel/recommendation/<rid>/<resource>` | 新增一个子项；`display_order` 不传则自动取 max+1 |
| `PUT` | `/api/admin/api/travel/recommendation/<rid>/<resource>/<item_id>` | 局部更新，只改 body 中包含的字段 |
| `DELETE` | `/api/admin/api/travel/recommendation/<rid>/<resource>/<item_id>` | 删除单条 |

**校验**：

- `rid` 不存在 → 404 `Recommendation not found`
- `item_id` 不属于该 `rid` → 404 `Resource not found`
- 必填字段缺失（`name` / `title` / `content`）→ 400

**示例**：

```bash
# 新增一个 player
curl -X POST /api/admin/api/travel/recommendation/1/players \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "一诺", "hero": "公孙离", "team": "成都AG", "description": "..."}'

# 删除
curl -X DELETE /api/admin/api/travel/recommendation/1/players/5 \
  -H "Authorization: Bearer <admin_token>"
```
```