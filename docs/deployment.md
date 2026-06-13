# 帮信罪主观明知分析系统 — 部署指南

## 目录

1. [环境要求](#1-环境要求)
2. [快速安装](#2-快速安装)
3. [启动服务](#3-启动服务)
4. [配置文件说明](#4-配置文件说明)
5. [数据库迁移](#5-数据库迁移)
6. [常见问题排查](#6-常见问题排查)
7. [生产环境部署](#7-生产环境部署)

---

## 1. 环境要求

### 1.1 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 4 核 2.0 GHz | 8 核 3.0 GHz 以上 |
| 内存 | 16 GB | 32 GB |
| 硬盘 | 50 GB 可用空间 | 100 GB SSD |
| GPU（模型微调和推理） | 无（CPU 模式可用） | NVIDIA RTX 4090 24 GB |
| 网络 | 宽带互联网连接（首次下载模型） | 稳定宽带连接 |

> **说明**：Ollama 运行 qwen2.5:7b 模型约需 8 GB 内存（4-bit 量化）或 16 GB 内存（FP16）。
> 若使用 GPU 推理，建议显存不低于 8 GB。

### 1.2 操作系统

| 系统 | 支持情况 | 注意事项 |
|------|---------|---------|
| Windows 10/11 | 完全支持 | 推荐使用 PowerShell 作为终端 |
| Ubuntu 20.04+ | 完全支持 | 需手动安装 Python 3.11 |
| macOS 13+ | 部分支持 | Neo4j 和 GPU 加速可能受限 |

### 1.3 软件依赖

| 软件 | 版本要求 | 用途 |
|------|---------|------|
| Python | 3.11+ | 后端运行环境 |
| Node.js | 18+ | 前端构建和运行 |
| npm | 9+ | 前端包管理 |
| Ollama | 0.3+ | AI 模型推理引擎 |
| Git | 2.0+ | 版本管理（可选） |

### 1.4 可选依赖

| 软件 | 版本 | 用途 |
|------|------|------|
| PostgreSQL | 14+ | 生产环境数据库 |
| Neo4j | 5.x | 知识图谱数据库 |
| NVIDIA CUDA | 12.1 | GPU 加速推理和微调 |
| NVIDIA cuDNN | 8.9+ | 深度学习加速 |

---

## 2. 快速安装

### 2.1 克隆项目

```powershell
# 进入工作目录
cd C:\Users\Lenovo\Desktop

# 项目已在当前目录，如使用 Git 可执行：
# git clone <仓库地址>
# cd 微信程序开发
```

### 2.2 安装 Ollama 并下载模型

```powershell
# 1. 下载并安装 Ollama（Windows 版本）
#    访问 https://ollama.com/download 下载安装包

# 2. 启动 Ollama 服务（后台运行）
ollama serve

# 3. 拉取所需模型（首次需要下载约 4.7 GB）
ollama pull qwen2.5:7b

# 4. 验证模型已就绪
ollama list
```

> **注意**：首次下载模型需要稳定的网络连接，下载时间取决于网络速度，通常 5~30 分钟。
> 如果网络不稳定，可尝试使用代理或更换模型源。

### 2.3 配置 Python 虚拟环境（后端）

```powershell
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境（PowerShell）
.\.venv\Scripts\Activate.ps1

# 如果遇到执行策略限制，先执行：
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 安装依赖
pip install -r requirements.txt

# （可选）安装测试工具依赖
pip install -r ..\scripts\requirements.txt

# 返回项目根目录
cd ..
```

### 2.4 配置前端

```powershell
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 返回项目根目录
cd ..
```

### 2.5 验证安装

```powershell
# 验证 Python 版本
python --version
# 输出：Python 3.11.x

# 验证 Node.js 版本
node --version
# 输出：v18.x.x

# 验证 Ollama 服务
curl http://localhost:11434/api/tags
# 输出：{"models":[{"name":"qwen2.5:7b", ...}]}
```

---

## 3. 启动服务

系统共包含三个独立服务，建议按顺序依次启动。

### 3.1 启动 Ollama（AI 推理引擎）

```powershell
# 方式一：直接启动（前台运行）
ollama serve

# 方式二：注册为 Windows 服务（开机自启）
# 在 Ollama 设置中勾选 "Run on startup"
```

Ollama 默认监听 `http://localhost:11434`。

### 3.2 启动后端服务（FastAPI - 端口 8000）

```powershell
# 进入后端目录并激活虚拟环境
cd backend
.\.venv\Scripts\Activate.ps1

# 方式一：使用启动脚本（推荐）
python run.py

# 方式二：直接使用 uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

启动成功标志：
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Model 'qwen2.5:7b' is available.
INFO:     Default admin user created: 'admin'
```

### 3.3 启动推理服务（独立推理 - 端口 8001，可选）

推理服务作为后端与 Ollama 之间的代理层，提供缓存和负载均衡功能。

```powershell
# 确保虚拟环境已激活
cd ml\inference
python run.py
```

启动成功标志：
```
INFO:     Uvicorn running on http://0.0.0.0:8001
INFO:     Model 'qwen2.5:7b' is available
```

> **注意**：如果不需要独立推理服务，可跳过此步骤。
> 此时需将 `.env` 中的 `OLLAMA_BASE_URL` 设置为 `http://localhost:11434`。

### 3.4 启动前端服务（Vue 3 - 端口 5173）

```powershell
# 新开一个终端
cd frontend

# 启动开发服务器
npm run dev
```

启动成功标志：
```
VITE v5.x.x  ready in xxx ms
Local:   http://localhost:5173/
Network: http://192.168.x.x:5173/
```

### 3.5 验证所有服务

打开浏览器访问以下地址确认各服务正常运行：

| 服务 | 地址 | 预期结果 |
|------|------|---------|
| 前端页面 | `http://localhost:5173` | 显示系统登录/欢迎页面 |
| 后端健康检查 | `http://localhost:8000/api/health` | 返回 JSON 状态信息 |
| Ollama 状态 | `http://localhost:11434/api/tags` | 返回模型列表 |
| 推理服务 | `http://localhost:8001/health` | 返回推理服务状态 |

---

## 4. 配置文件说明

### 4.1 配置文件位置

```
backend/.env          # 主配置文件（实际生效）
backend/.env.example  # 配置模板（供参考）
```

> 系统启动时会自动加载 `backend/.env` 文件。
> 若 `.env` 不存在，将使用 `config.py` 中的默认值。

### 4.2 配置项详解

```ini
# ============================================
# Ollama 配置
# ============================================

# Ollama 服务地址
# - 使用独立推理服务时：http://localhost:8001
# - 直连 Ollama 时：http://localhost:11434
# 生产环境建议使用独立推理服务并配置 HTTPS
OLLAMA_BASE_URL=http://localhost:8001

# AI 推理模型名称
# 必须与 ollama pull 拉取的模型名称一致
# 推荐：qwen2.5:7b（平衡性能与效果）
# 可选：deepseek-r1:7b、qwen2.5:14b（需要更高显存）
OLLAMA_MODEL=qwen2.5:7b

# ============================================
# 服务器配置
# ============================================

# 后端服务监听地址
# 0.0.0.0 表示监听所有网络接口
# 生产环境建议绑定内网 IP 并通过 Nginx 反向代理
SERVER_HOST=0.0.0.0

# 后端服务端口
# 生产环境通常使用 8000，通过 Nginx 转发到 443
SERVER_PORT=8000

# 调试模式
# true  - 开启热重载、SQL 日志、详细错误信息（仅开发环境）
# false - 关闭调试功能，提升性能（生产环境）
DEBUG=true

# ============================================
# 数据库配置
# ============================================

# 数据库连接 URL
# 开发环境（SQLite - 无需额外安装）：
#   sqlite:///./app.db
# 生产环境（PostgreSQL - 推荐）：
#   postgresql://user:password@localhost:5432/case_analysis
DATABASE_URL=sqlite:///./app.db

# ============================================
# JWT 安全配置
# ============================================

# JWT 签名密钥（生产环境必改）
# ⚠️ 安全警告：
#   - 生产环境未配置或使用默认占位符将导致应用启动失败
#   - 请使用以下命令生成符合密码学安全要求的随机密钥（≥256 位）：
#     python scripts/generate_jwt_secret.py --env-format
#   - 密钥长度要求至少 32 字节（64 个十六进制字符）
#   - 请勿将真实密钥提交到版本控制系统
#
# 生成密钥后，将生成的值替换以下默认占位符
JWT_SECRET_KEY=change-this-to-a-secure-random-secret-key-in-production

# Access Token 过期时间（分钟）
# 建议：生产环境设为 15~60 分钟
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Refresh Token 过期时间（天）
# 建议：生产环境设为 7~30 天
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ============================================
# 默认管理员账户（首次启动时自动创建）
# ============================================

# 管理员用户名
DEFAULT_ADMIN_USERNAME=admin

# 管理员密码（生产环境务必修改！）
# 要求：至少 8 位，包含大小写字母和数字
DEFAULT_ADMIN_PASSWORD=admin123

# ============================================
# 日志配置
# ============================================

# 日志级别
# 可选：DEBUG、INFO、WARNING、ERROR、CRITICAL
# 开发环境：DEBUG
# 生产环境：INFO 或 WARNING
LOG_LEVEL=DEBUG

# ============================================
# 跨域配置
# ============================================

# 允许的跨域来源
# 开发环境：*（允许所有来源）
# 生产环境：http://your-domain.com,https://your-domain.com
CORS_ORIGINS=*

# ============================================
# Neo4j 图数据库配置（可选）
# ============================================

# Neo4j 连接地址
# 若留空，系统将使用内存图作为替代
# 生产环境建议部署 Neo4j 并填写此配置
NEO4J_URI=bolt://localhost:7687

# Neo4j 用户名
NEO4J_USER=neo4j

# Neo4j 密码
# 应使用强密码，避免使用默认密码 neo4j123
NEO4J_PASSWORD=neo4j123
```

### 4.3 推理服务额外配置

`ml/inference/server.py` 中额外支持以下环境变量：

| 变量名 | 默认值 | 说明 |
|-------|--------|------|
| `INFERENCE_HOST` | `0.0.0.0` | 推理服务监听地址 |
| `INFERENCE_PORT` | `8001` | 推理服务端口 |
| `OLLAMA_UPSTREAM_URL` | `http://localhost:11434` | 上游 Ollama 地址 |

---

## 5. 数据库迁移

### 5.1 初始化数据库

首次启动后端服务时，系统会自动执行以下操作：

1. 根据 SQLAlchemy 模型创建所有数据库表
2. 创建默认管理员用户（用户名/密码由 `.env` 配置）
3. 预缓存示例案件的分析结果

无需手动执行迁移命令。

### 5.2 手动执行 Alembic 迁移

如需对数据库 schema 进行版本控制管理，可使用 Alembic：

```powershell
# 确保虚拟环境已激活
cd backend
.\.venv\Scripts\Activate.ps1

# 生成迁移脚本（模型变更后执行）
alembic revision --autogenerate -m "描述本次变更"

# 应用迁移
alembic upgrade head

# 回滚迁移（回退一个版本）
alembic downgrade -1

# 查看迁移历史
alembic history

# 查看当前版本
alembic current
```

### 5.3 从 SQLite 切换到 PostgreSQL

```powershell
# 1. 安装和启动 PostgreSQL（略）

# 2. 创建数据库
psql -U postgres
CREATE DATABASE case_analysis;
\q

# 3. 修改 .env 中的 DATABASE_URL
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/case_analysis

# 4. 重启后端服务（系统会自动创建表结构）
```

---

## 6. 常见问题排查

### 6.1 Ollama 相关问题

**问题：Ollama 连接失败**

```text
ERROR: Cannot connect to Ollama at http://localhost:11434
```

排查步骤：

```powershell
# 1. 确认 Ollama 服务已启动
ollama serve

# 2. 检查端口是否被占用
netstat -ano | findstr :11434

# 3. 测试 API 连通性
curl http://localhost:11434/api/tags

# 4. 检查 .env 中的 OLLAMA_BASE_URL 配置是否正确
```

**问题：模型未找到**

```text
WARNING: Model 'qwen2.5:7b' not found.
```

解决方案：

```powershell
# 1. 查看已安装的模型列表
ollama list

# 2. 如未安装，拉取所需模型
ollama pull qwen2.5:7b

# 3. 检查 .env 中 OLLAMA_MODEL 是否与 ollama list 输出一致
```

**问题：Ollama 显存不足**

```text
Error: CUDA out of memory
```

解决方案：

- 降低模型量化级别：`ollama pull qwen2.5:7b-q4_K_M`（4-bit 量化）
- 切换到更小的模型：`ollama pull qwen2.5:3b`
- 关闭其他 GPU 应用程序
- 在 CPU 模式下运行（较慢但稳定）

### 6.2 后端相关问题

**问题：端口被占用**

```text
ERROR: [WinError 10048] 通常每个套接字地址（协议/网络地址/端口）只允许使用一次
```

```powershell
# 查找占用 8000 端口的进程
netstat -ano | findstr :8000

# 终止占用进程（替换最后的 PID）
taskkill /PID <进程ID> /F

# 或修改 .env 使用其他端口
SERVER_PORT=8002
```

**问题：依赖安装失败**

```powershell
# 更新 pip
python -m pip install --upgrade pip

# 单独安装失败依赖
pip install <包名> --no-cache-dir

# 使用国内镜像源（如果网络慢）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**问题：SQLite 数据库损坏**

```powershell
# 删除旧的数据库文件（系统会在下次启动时自动重建）
Remove-Item backend/app.db -Force

# 注意：此操作会清除所有数据，如需保留请先备份
```

### 6.3 前端相关问题

**问题：npm install 失败**

```powershell
# 清除 npm 缓存
npm cache clean --force

# 使用淘宝镜像
npm install --registry=https://registry.npmmirror.com

# 检查 Node.js 版本
node --version  # 需要 18+
```

**问题：前端无法连接后端**

```text
Error: Network Error
axiosError: timeout of xxxms exceeded
```

排查步骤：

1. 确认后端服务已启动（访问 `http://localhost:8000/api/health`）
2. 检查 `.env` 中 `CORS_ORIGINS` 是否包含前端地址
3. 前端 API 基础地址需配置为后端地址（查看 `frontend/src/data/config.js`）

### 6.4 Neo4j 相关问题

**问题：Neo4j 连接失败**

```powershell
# 1. 确认 Neo4j 服务已启动
#    访问 http://localhost:7474 查看 Neo4j 浏览器界面

# 2. 测试 Bolt 协议连接
curl http://localhost:7687

# 3. 检查 .env 中的 Neo4j 配置
#    如不使用 Neo4j，将 NEO4J_URI 留空即可
```

### 6.5 通用问题

**问题：中文乱码**

```powershell
# 确保终端支持 UTF-8
chcp 65001

# 在 PowerShell 中设置编码
$OutputEncoding = [Console]::OutputEncoding = [Text.UTF8Encoding]::UTF8
```

**问题：文件权限错误**

```powershell
# 确保运行用户对以下目录有读写权限：
# - backend/app.db（数据库文件）
# - backend/logs/（日志目录）
# - backend/.cache/（缓存目录）
```

---

## 7. 生产环境部署

### 7.1 安全加固清单

| 项目 | 操作 | 重要性 |
|------|------|--------|
| JWT 密钥 | 使用 `python scripts/generate_jwt_secret.py` 生成 ≥256 位安全密钥并替换 | 必做 |
| JWT 密钥验证 | 确认生产环境已配置有效 JWT_SECRET_KEY，否则应用将无法启动 | 必做 |
| 管理员密码 | 修改为强密码（至少 12 位，含特殊字符） | 必做 |
| 调试模式 | `DEBUG=false` | 必做 |
| CORS 来源 | 指定具体域名而非 `*` | 必做 |
| 数据库 | 切换到 PostgreSQL | 推荐 |
| HTTPS | 配置 SSL 证书和 Nginx 反向代理 | 推荐 |
| 日志级别 | 设为 `INFO` 或 `WARNING` | 推荐 |
| 防火墙 | 限制非必要端口的外部访问 | 必做 |

### 7.2 JWT 密钥安全最佳实践

#### 为什么 JWT 密钥如此重要？

JWT（JSON Web Token）使用 HMAC-SHA256 算法进行签名，密钥用于：
- 签发 Access Token 和 Refresh Token
- 验证客户端提交的 Token 是否有效
- 防止 Token 被伪造或篡改

如果密钥泄露，攻击者可以：
- 伪造任意用户身份的 JWT Token
- 以管理员身份访问系统所有功能
- 绕过身份验证机制

#### 安全密钥生成与配置

```powershell
# 1. 生成符合密码学安全要求的 JWT 密钥（≥256 位）
python scripts/generate_jwt_secret.py --env-format

# 输出示例：
# JWT_SECRET_KEY=a1b2c3d4e5f6...（64 个十六进制字符）

# 2. 将生成的密钥写入 .env 文件
# 编辑 backend/.env 文件，将 JWT_SECRET_KEY 替换为生成的值

# 3. 验证配置是否正确
# 启动应用，确认无安全警告或错误
```

#### 密钥管理要求

| 要求 | 说明 |
|------|------|
| 长度 | 至少 32 字节（64 个十六进制字符，即 256 位） |
| 随机性 | 必须使用密码学安全的随机数生成器（如 Python `secrets` 模块） |
| 存储 | 仅存储在 `.env` 文件或环境变量中，禁止硬编码在源码中 |
| 版本控制 | `.env` 文件必须加入 `.gitignore`，禁止提交到版本控制系统 |
| 轮换 | 建议定期更换密钥（如每季度），更换后所有现有 Token 将失效 |
| 泄露处理 | 如果怀疑密钥泄露，立即更换并通知所有用户重新登录 |

#### 应用启动验证机制

系统实现了启动时安全验证：
- **生产环境** (`APP_ENV=production`)：如果未配置 JWT_SECRET_KEY 或使用默认占位符，应用将拒绝启动并输出错误信息
- **开发环境** (`APP_ENV=development`)：如果未配置，会显示安全警告但允许使用占位符继续运行，方便开发调试

### 7.3 推荐生产环境配置

```ini
# backend/.env（生产环境示例）

OLLAMA_BASE_URL=http://localhost:8001
OLLAMA_MODEL=qwen2.5:7b

SERVER_HOST=127.0.0.1
SERVER_PORT=8000
DEBUG=false

DATABASE_URL=postgresql://caseuser:StrongPassword123!@localhost:5432/case_analysis

# ⚠️ 必须使用 generate_jwt_secret.py 脚本生成的安全密钥替换以下示例
# 生成命令: python scripts/generate_jwt_secret.py --env-format
JWT_SECRET_KEY=5f8a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=YourStrongAdminP@ss123

LOG_LEVEL=INFO

CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

### 7.3 使用 Nginx 反向代理

```
# /etc/nginx/sites-available/case-analysis

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/ssl/certs/your-domain.com.pem;
    ssl_certificate_key /etc/ssl/private/your-domain.com.key;

    # 前端静态文件
    location / {
        root /path/to/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # 健康检查（对外暴露）
    location /health {
        proxy_pass http://127.0.0.1:8000/api/health;
        proxy_set_header Host $host;
    }
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

### 7.4 前端构建

```powershell
cd frontend

# 构建生产版本
npm run build

# 构建产物在 frontend/dist/ 目录
# 将其部署到 Nginx 或 CDN
```

### 7.5 使用系统服务管理（Windows）

创建计划任务或使用 [NSSM](https://nssm.cc/) 将各服务注册为 Windows 服务：

```powershell
# 使用 NSSM 注册后端服务
nssm install CaseAnalysisBackend "C:\path\to\backend\.venv\Scripts\python.exe" "run.py"
nssm set CaseAnalysisBackend AppDirectory "C:\path\to\backend"
nssm start CaseAnalysisBackend
```

### 7.6 使用 systemd 管理（Linux）

```ini
# /etc/systemd/system/case-analysis-backend.service
[Unit]
Description=帮信罪分析系统 - 后端服务
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/case-analysis/backend
ExecStart=/opt/case-analysis/backend/.venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 启用并启动服务
sudo systemctl enable case-analysis-backend
sudo systemctl start case-analysis-backend

# 查看日志
sudo journalctl -u case-analysis-backend -f
```

### 7.7 性能优化建议

| 优化项 | 说明 | 效果 |
|-------|------|------|
| 启用分析缓存 | 系统已内置 MD5 缓存，相同案件文本避免重复调用 LLM | 显著降低推理延迟 |
| 使用 PostgreSQL | 替代 SQLite，支持并发读写 | 提升多用户场景性能 |
| 部署独立推理服务 | 通过端口 8001 代理 Ollama，可单独扩缩容 | 提升推理吞吐量 |
| Nginx 静态缓存 | 缓存前端静态资源 | 减少后端负载 |
| 配置 Neo4j 索引 | 为知识图谱节点创建索引 | 加速图查询 |
| 调整 Ollama 并发 | 设置 `OLLAMA_NUM_PARALLEL=4` | 提升并发推理能力 |

### 7.8 监控与维护

**健康检查端点：**

```bash
# 后端综合健康状态
curl http://localhost:8000/api/health

# 推理服务状态
curl http://localhost:8001/health

# Ollama 模型状态
curl http://localhost:11434/api/tags
```

**日志文件位置：**

```
backend/logs/
├── app_2025-01-01.log      # 应用日志（自动按天轮转，保留 7 天）
└── inference_2025-01-01.log # 推理服务日志（自动按天轮转，保留 7 天）
```

**定期维护任务：**

| 频率 | 任务 | 说明 |
|------|------|------|
| 每日 | 检查日志文件 | 确认无异常错误堆栈 |
| 每周 | 清理过期缓存 | 删除 `backend/.cache/` 中超过 7 天的缓存文件 |
| 每月 | 备份数据库 | 导出 SQLite 文件或 PostgreSQL dump |
| 每月 | 检查磁盘空间 | 确认日志和缓存未占满磁盘 |
| 每季度 | 更新模型 | 检查并更新 Ollama 模型版本 |

### 7.9 备份策略

```powershell
# SQLite 备份（开发环境）
Copy-Item backend/app.db "backend/backups/app_$(Get-Date -Format 'yyyyMMdd').db"

# PostgreSQL 备份（生产环境）
pg_dump -U caseuser -h localhost case_analysis > "backend/backups/db_$(date +%Y%m%d).sql"

# 配置文件备份
Copy-Item backend/.env "backend/backups/.env_$(Get-Date -Format 'yyyyMMdd')"
```

---

## 附录：快速启动命令速查

```powershell
# === 一键启动（Windows PowerShell，需要四个独立终端）===

# 终端 1：Ollama
ollama serve

# 终端 2：后端
cd backend
.\.venv\Scripts\Activate.ps1
python run.py

# 终端 3：前端
cd frontend
npm run dev

# 终端 4：推理服务（可选）
cd ml\inference
python run.py
```

> **首次部署**：请务必阅读第 7 节生产环境部署中的安全加固清单，
> 确保在生产环境中修改所有默认密码和密钥。
