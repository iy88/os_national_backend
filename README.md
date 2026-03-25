# os_national_backend

Service Outsourcing National Competition Backend repo.

# Env

- Python: 3.12.13
- Flask: 3.1.3
- Conda env: `os_national`

# Setup

## 1. 安装依赖

```bash
conda activate os_national
pip install -r requirements.txt
```

## 2. 配置环境变量

复制环境配置模板并修改：

```bash
cp .env.dev .env  # 开发环境
# 或
cp .env.prod .env  # 生产环境
```

然后编辑 `.env` 文件，配置 MySQL、Redis、SMTP、JWT 等信息。

## 3. 初始化数据库

```bash
flask init-db
```

或直接启动服务，表会自动创建。

## 4. 启动服务

```bash
python app.py
```

服务默认运行在 `http://localhost:5000`

# Database

数据库表结构见 [docs/db.md](docs/db.md)

# API

API 文档见 [docs/api.md](docs/api.md)

## 主要接口

| 方法   | URL                      | 说明      |
|------|--------------------------|---------|
| POST | /email/verification/send | 发送邮箱验证码 |
| POST | /user/register           | 用户注册    |
| POST | /user/login              | 用户登录    |
| GET  | /health                  | 健康检查    |
