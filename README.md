# Forum (Django + PostgreSQL)

一个仿照参考站首页三栏布局的轻量论坛/博客项目：支持**多用户登录发帖**、**Markdown**、**评论 + 回复**、**点赞**、**站内搜索**，并提供 Docker/Podman 编排。

## 功能清单（首版）

- **首页**：三栏布局（分类/标签、帖子流、推荐榜/每日一言/天气占位）  
- **帖子详情**：Markdown 渲染、点赞/取消点赞、评论 + 二级回复  
- **用户**：注册/登录/退出  
- **发帖中心（定制后台 UI）**：与前台同风格的发帖与“我的帖子”列表  
- **站内搜索**：按标题与正文关键字搜索（`?q=`）

> `发现 / 相册 / 刷刷 / 问问`：首版为占位导航项（未实现实际页面）。

## 技术栈

- 后端：Django
- 数据库：PostgreSQL（容器环境）；本地无环境变量时自动回退到 SQLite
- Markdown：`markdown`（服务端渲染），SimpleMDE（编辑器，CDN 引入）
- 容器：Docker Compose（Podman 也可用）

## 目录结构（关键）

- `forumsite/`：Django 项目配置
- `core/`：核心业务（模型、视图、URL、表单）
- `templates/`：页面模板
- `static/`：静态资源（CSS）
- `media/`：上传文件（头像/封面图，开发环境）

## 本地运行（不使用容器）

> 不设置 `POSTGRES_*` 环境变量时，默认使用 SQLite，适合快速本地调试。

```bash
cd E:\python\forum

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate

python manage.py runserver
```

访问：`http://127.0.0.1:8000/`

## Docker / Podman 一键启动（推荐）

项目已提供 `docker-compose.yml`（包含 `web` + `db`）。

```bash
cd E:\python\forum
docker compose up --build
```

Podman 示例（若你已安装 `podman-compose`）：

```bash
podman-compose up --build
```

启动后访问：`http://localhost:8000/`

### 容器环境下首次初始化

另开一个终端执行：

```bash
docker compose exec web python manage.py migrate
```

> 项目已内置数据迁移，会自动创建默认管理员账户。

### 默认管理员账户

项目已内置默认管理员账户，迁移时会自动创建：

| 字段 | 值 |
|------|-----|
| 用户名 | `admin` |
| 密码 | `admin123` |
| 邮箱 | `admin@forum.local` |

**安全提示**：首次登录后请立即修改密码！

### 密码修改功能

支持两种密码修改方式：

1. **旧密码验证**：输入旧密码和新密码直接修改
2. **邮箱验证**：向绑定邮箱发送验证码，验证后修改（开发环境会在页面显示验证码）

访问路径：登录后点击右上角用户名 → 修改密码

## 环境变量（PostgreSQL）

当以下变量都存在时会启用 PostgreSQL：

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`（默认 `db`）
- `POSTGRES_PORT`（默认 `5432`）

`docker-compose.yml` 已为 `web` 服务配置了这些变量。

## 常用命令

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## 开发说明

- **Markdown 编辑器**：发帖页 `dashboard` 使用 SimpleMDE（CDN），需要联网；若你希望改为本地静态资源方式，可继续提需求。
- **PowerShell 注意**：PowerShell 不支持 `&&` 链式命令（会报错），请分行执行或用 `;`。

