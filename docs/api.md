# API 文档

## 目录

- [用户认证](#用户认证)
- [用户信息](#用户信息)
- [文件接口](#文件接口)

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

| 字段         | 类型     | 必填 | 说明                                |
|------------|--------|----|-----------------------------------|
| email      | string | 是  | 邮箱地址                             |
| password   | string | 是  | 密码（6-128 字符，明文传输，后端加密存储）    |
| verifyCode | string | 是  | 6 位邮箱验证码                         |
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
    "email": "user@example.com"
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

| 字段        | 类型   | 说明             |
|-------------|--------|----------------|
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

| 字段       | 类型    | 必填 | 说明                        |
|----------|--------|----|---------------------------|
| username | string | 否  | 用户名（3-80 字符），需唯一         |
| gender   | string | 否  | 性别                          |
| age      | int    | 否  | 年龄                          |
| basicInfo | string | 否  | 基本信息                       |
| bio      | string | 否  | 简介                          |

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

| 字段    | 类型   | 必填 | 说明     |
|---------|--------|----|----------|
| user_id | string | 是  | 用户 ID  |
| file    | file  | 是  | 头像文件 |

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
