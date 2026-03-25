# 数据库设计

## User 表 (users)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| uid | INT | PRIMARY KEY, AUTO_INCREMENT | 用户唯一标识 |
| username | VARCHAR(80) | UNIQUE, NOT NULL | 用户名 |
| email | VARCHAR(120) | UNIQUE, NOT NULL | 邮箱 |
| password_hash | VARCHAR(60) | NOT NULL | 密码（bcrypt 加密） |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

## UserInfo 表 (user_info)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| uid | INT | PRIMARY KEY, FOREIGN KEY(users.uid) | 关联 User 表 |
| avatar_id | INT | FOREIGN KEY(files.fid), NULLABLE | 头像文件 ID |
| gender | VARCHAR(10) | NULLABLE | 性别 |
| age | INT | NULLABLE | 年龄 |
| basic_info | TEXT | NULLABLE | 基本信息 |
| bio | TEXT | NULLABLE | 简介 |

## File 表 (files)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| fid | INT | PRIMARY KEY, AUTO_INCREMENT | 文件唯一标识 |
| uid | INT | FOREIGN KEY(users.uid), NOT NULL | 关联 User 表 |
| original_filename | VARCHAR(255) | NOT NULL | 原始文件名 |
| secure_filename | VARCHAR(255) | UNIQUE, NOT NULL | 安全文件名（唯一） |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 上传时间 |

## 表关系

- `UserInfo.uid` 外键关联 `User.uid` (ON DELETE CASCADE)，一对一关系，注册时自动创建
- `UserInfo.avatar_id` 外键关联 `File.fid` (ON DELETE SET NULL)，表示用户头像
- `File.uid` 外键关联 `User.uid` (ON DELETE CASCADE)，多对一关系（一个用户可上传多个文件）
