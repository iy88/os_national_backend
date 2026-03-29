# 数据库设计

## User 表 (users)

| 字段            | 类型           | 约束                          | 说明            |
|---------------|--------------|-----------------------------|---------------|
| uid           | INT          | PRIMARY KEY, AUTO_INCREMENT | 用户唯一标识        |
| username      | VARCHAR(80)  | UNIQUE, NOT NULL            | 用户名           |
| email         | VARCHAR(120) | UNIQUE, NOT NULL            | 邮箱            |
| password_hash | VARCHAR(60)  | NOT NULL                    | 密码（bcrypt 加密） |
| created_at    | DATETIME     | DEFAULT CURRENT_TIMESTAMP   | 创建时间          |
| updated_at    | DATETIME     | ON UPDATE CURRENT_TIMESTAMP  | 更新时间          |

## UserInfo 表 (user_info)

| 字段         | 类型          | 约束                                  | 说明        |
|------------|-------------|-------------------------------------|-----------|
| uid        | INT         | PRIMARY KEY, FOREIGN KEY(users.uid) | 关联 User 表 |
| avatar_id  | INT         | FOREIGN KEY(files.fid), NULLABLE    | 头像文件 ID   |
| gender     | VARCHAR(10) | NULLABLE                            | 性别        |
| age        | INT         | NULLABLE                            | 年龄        |
| basic_info | TEXT        | NULLABLE                            | 基本信息      |
| bio        | TEXT        | NULLABLE                            | 简介        |
| updated_at | DATETIME    | ON UPDATE CURRENT_TIMESTAMP          | 更新时间      |

## File 表 (files)

| 字段                | 类型           | 约束                               | 说明        |
|-------------------|--------------|----------------------------------|-----------|
| fid               | INT          | PRIMARY KEY, AUTO_INCREMENT      | 文件唯一标识    |
| uid               | INT          | FOREIGN KEY(users.uid), NOT NULL | 关联 User 表 |
| original_filename | VARCHAR(255) | NOT NULL                         | 原始文件名     |
| secure_filename   | VARCHAR(255) | UNIQUE, NOT NULL                 | 安全文件名（唯一） |
| created_at        | DATETIME     | DEFAULT CURRENT_TIMESTAMP        | 上传时间      |
| updated_at        | DATETIME     | ON UPDATE CURRENT_TIMESTAMP      | 更新时间      |

## 表关系

- `UserInfo.uid` 外键关联 `User.uid` (ON DELETE CASCADE)，一对一关系，注册时自动创建
- `UserInfo.avatar_id` 外键关联 `File.fid` (ON DELETE SET NULL)，表示用户头像
- `File.uid` 外键关联 `User.uid` (ON DELETE CASCADE)，多对一关系（一个用户可上传多个文件）

## ConversationSession 表 (conversation_sessions)

| 字段         | 类型           | 约束                               | 说明           |
|------------|--------------|----------------------------------|--------------|
| sid        | INT          | PRIMARY KEY, AUTO_INCREMENT      | 会话唯一标识       |
| uid        | INT          | FOREIGN KEY(users.uid), NOT NULL | 关联 User 表    |
| title      | VARCHAR(255) | NOT NULL                         | 会话标题（AI 自动生成，或用户手动编辑） |
| created_at | DATETIME     | DEFAULT CURRENT_TIMESTAMP        | 创建时间         |
| updated_at | DATETIME     | ON UPDATE CURRENT_TIMESTAMP      | 更新时间         |

## Message 表 (messages)

| 字段         | 类型          | 约束                                               | 说明               |
|------------|-------------|--------------------------------------------------|------------------|
| mid        | INT         | PRIMARY KEY, AUTO_INCREMENT                      | 消息唯一标识           |
| sid        | INT         | FOREIGN KEY(conversation_sessions.sid), NOT NULL | 所属会话             |
| role       | VARCHAR(20) | NOT NULL                                         | user / assistant |
| content    | TEXT        | NOT NULL                                         | 消息内容             |
| created_at | DATETIME    | DEFAULT CURRENT_TIMESTAMP                        | 创建时间             |
| updated_at | DATETIME    | ON UPDATE CURRENT_TIMESTAMP                      | 更新时间             |

## Route 表 (routes)

| 字段         | 类型           | 约束                                  | 说明                        |
|------------|--------------|-------------------------------------|---------------------------|
| rid        | INT          | PRIMARY KEY, AUTO_INCREMENT         | 路线唯一标识                    |
| uid        | INT          | FOREIGN KEY(users.uid), NOT NULL    | 关联 User 表                 |
| mid        | INT          | FOREIGN KEY(messages.mid), NOT NULL | 关联消息（assistant role）      |
| title      | VARCHAR(255) | NOT NULL                            | 路线标题（复制自 session.title）   |
| content    | TEXT         | NOT NULL                            | 路线内容（复制自 message.content） |
| created_at | DATETIME     | DEFAULT CURRENT_TIMESTAMP           | 创建时间                      |

## AI 对话表关系

- `ConversationSession.uid` 外键关联 `User.uid` (ON DELETE CASCADE)，一个用户可有多个会话
- `Message.sid` 外键关联 `ConversationSession.sid` (ON DELETE CASCADE)，一个会话可有多个消息
- `Route.uid` 外键关联 `User.uid` (ON DELETE CASCADE)，一个用户可有多个收藏
- `Route.mid` 外键关联 `Message.mid` (ON DELETE CASCADE)，一个消息可被多个收藏引用

**关系链**：User (1) → Session (N) → Message (N) ← Route (1)
