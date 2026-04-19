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

## Admin 表 (admins)

| 字段            | 类型           | 约束                          | 说明            |
|---------------|--------------|-----------------------------|---------------|
| aid           | INT          | PRIMARY KEY, AUTO_INCREMENT | 管理员唯一标识      |
| username      | VARCHAR(80)  | UNIQUE, NOT NULL            | 管理员用户名       |
| email         | VARCHAR(120) | UNIQUE, NOT NULL            | 管理员邮箱        |
| password_hash | VARCHAR(256) | NOT NULL                    | 密码（bcrypt 加密） |
| created_at    | DATETIME     | DEFAULT CURRENT_TIMESTAMP   | 创建时间          |
| updated_at    | DATETIME     | ON UPDATE CURRENT_TIMESTAMP  | 更新时间          |

## AdminInfo 表 (admin_info)

| 字段         | 类型          | 约束                                  | 说明        |
|------------|-------------|-------------------------------------|-----------|
| aid        | INT         | PRIMARY KEY, FOREIGN KEY(admins.aid) | 关联 Admin 表 |
| avatar_id  | INT         | FOREIGN KEY(files.fid), NULLABLE     | 头像文件 ID   |
| gender     | VARCHAR(10) | NULLABLE                            | 性别        |
| age        | INT         | NULLABLE                            | 年龄        |
| basic_info | TEXT        | NULLABLE                            | 基本信息      |
| bio        | TEXT        | NULLABLE                            | 简介        |
| updated_at | DATETIME    | ON UPDATE CURRENT_TIMESTAMP          | 更新时间      |

## File 表 (files)

| 字段                | 类型           | 约束                               | 说明        |
|-------------------|--------------|----------------------------------|-----------|
| fid               | INT          | PRIMARY KEY, AUTO_INCREMENT      | 文件唯一标识    |
| original_filename | VARCHAR(255) | NOT NULL                         | 原始文件名     |
| secure_filename   | VARCHAR(255) | UNIQUE, NOT NULL                 | 安全文件名（唯一） |
| created_at        | DATETIME     | DEFAULT CURRENT_TIMESTAMP        | 上传时间      |
| updated_at        | DATETIME     | ON UPDATE CURRENT_TIMESTAMP      | 更新时间      |

## 表关系

- `UserInfo.uid` 外键关联 `User.uid` (ON DELETE CASCADE)，一对一关系，注册时自动创建
- `UserInfo.avatar_id` 外键关联 `File.fid` (ON DELETE SET NULL)，表示用户头像
- `AdminInfo.aid` 外键关联 `Admin.aid` (ON DELETE CASCADE)，一对一关系，管理员注册时自动创建
- `AdminInfo.avatar_id` 外键关联 `File.fid` (ON DELETE SET NULL)，表示管理员头像
- File 表不再与 User 绑定，改为纯文件存储（供用户头像、角色头像等使用）

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

## RoleplayCharacter 表 (roleplay_characters)

| 字段         | 类型           | 约束                                  | 说明                        |
|------------|--------------|-------------------------------------|---------------------------|
| rid        | INT          | PRIMARY KEY, AUTO_INCREMENT         | 角色唯一标识                    |
| type       | VARCHAR(20)  | NOT NULL                            | 类型（game_expert=电竞明星 / esports_player=电竞选手 / game_hero=游戏英雄） |
| name       | VARCHAR(80)  | NOT NULL                            | 角色显示名                      |
| created_at | DATETIME     | DEFAULT CURRENT_TIMESTAMP           | 创建时间                      |
| updated_at | DATETIME     | ON UPDATE CURRENT_TIMESTAMP         | 更新时间                      |

## RoleplayCharacterDetail 表 (roleplay_character_details)

| 字段         | 类型          | 约束                                  | 说明                        |
|------------|-------------|-------------------------------------|---------------------------|
| rid        | INT         | PRIMARY KEY, FOREIGN KEY(roleplay_characters.rid) | 角色唯一标识（关联 RoleplayCharacter） |
| bio        | TEXT        | NULLABLE                            | 简介                        |
| phrases    | TEXT        | NULLABLE                            | 名人名言/短语（JSON 数组）           |
| avatar_id  | INT         | FOREIGN KEY(files.fid), NULLABLE    | 头像文件 ID                    |
| images_id  | TEXT        | NULLABLE                            | 图片文件 ID 数组（JSON 数组）         |
| updated_at | DATETIME    | ON UPDATE CURRENT_TIMESTAMP          | 更新时间                      |

## RoleplaySession 表 (roleplay_sessions)

| 字段         | 类型           | 约束                                  | 说明                        |
|------------|--------------|-------------------------------------|---------------------------|
| uid        | INT          | PRIMARY KEY, FOREIGN KEY(users.uid) | 关联 User 表                |
| rid        | INT          | PRIMARY KEY, FOREIGN KEY(roleplay_characters.rid) | 关联 RoleplayCharacter 表 |
| created_at | DATETIME     | DEFAULT CURRENT_TIMESTAMP           | 创建时间                      |
| updated_at | DATETIME     | ON UPDATE CURRENT_TIMESTAMP         | 更新时间                      |

**唯一约束**：(uid, rid) 唯一确定一个会话

## RoleplayMessage 表 (roleplay_messages)

| 字段         | 类型          | 约束                                               | 说明               |
|------------|-------------|--------------------------------------------------|------------------|
| mid        | INT         | PRIMARY KEY, AUTO_INCREMENT                      | 消息唯一标识           |
| uid        | INT         | FOREIGN KEY(users.uid), NOT NULL                 | 关联 User 表         |
| rid        | INT         | FOREIGN KEY(roleplay_characters.rid), NOT NULL   | 所属角色              |
| role       | VARCHAR(20) | NOT NULL                                         | user / assistant |
| content    | TEXT        | NOT NULL                                         | 消息内容             |
| created_at | DATETIME    | DEFAULT CURRENT_TIMESTAMP                        | 创建时间             |
| updated_at | DATETIME    | ON UPDATE CURRENT_TIMESTAMP                      | 更新时间             |

## Roleplay 表关系

- `RoleplayCharacter` 不关联用户（角色表不关联 User）
- `RoleplayCharacterDetail.rid` 外键关联 `RoleplayCharacter.rid` (ON DELETE CASCADE)，一对一关系
- `RoleplayCharacterDetail.avatar_id` 外键关联 `File.fid` (ON DELETE SET NULL)，表示角色头像
- `RoleplayCharacterDetail.images_id` 存储多个图片文件 ID（JSON 数组）
- `RoleplaySession.uid` 外键关联 `User.uid` (ON DELETE CASCADE)
- `RoleplaySession.rid` 外键关联 `RoleplayCharacter.rid` (ON DELETE CASCADE)
- `RoleplayMessage.uid` 外键关联 `User.uid` (ON DELETE CASCADE)
- `RoleplayMessage.rid` 外键关联 `RoleplayCharacter.rid` (ON DELETE CASCADE)
