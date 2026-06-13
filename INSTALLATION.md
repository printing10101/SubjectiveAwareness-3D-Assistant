# 用户安装教程

## 一、系统要求说明

### 1.1 操作系统兼容性

| 操作系统 | 支持版本 | 备注 |
|----------|---------|------|
| Windows | Windows 10 (64位) / Windows 11 | 推荐 Windows 11，需启用 WSL2（如需 GPU 加速） |
| macOS | macOS 12 (Monterey) 及以上 | Apple Silicon (M1/M2/M3) 或 Intel 芯片均可 |
| Linux | Ubuntu 20.04+ / CentOS 8+ / Debian 11+ | 内核版本 >= 5.4 |

### 1.2 硬件配置要求

#### 内存（RAM）

| 配置级别 | 容量 | 说明 |
|---------|------|------|
| 最低配置 | 8 GB | 仅运行后端服务，不推荐同时运行 AI 模型 |
| 推荐配置 | 16 GB 及以上 | 可同时运行 Ollama 模型 + 后端 + 前端 |

#### 硬盘空间

| 项目 | 占用空间（GB） | 说明 |
|------|--------------|------|
| Ollama 程序 | ~0.5 GB | Ollama 本体 |
| AI 模型（deepseek-r1:7b） | ~4.5 GB | 模型文件占用 |
| Python 虚拟环境 | ~1 GB | 后端依赖包 |
| Node.js 依赖 | ~0.3 GB | 前端 node_modules |
| 数据库及日志 | ~0.5 GB | SQLite 数据库 + 运行日志 |
| 其他项目文件 | ~0.2 GB | 项目代码、配置等 |
| **总计（推荐预留）** | **至少 10 GB** | 建议预留 20 GB 以保证运行流畅 |

#### GPU 要求（可选）

| 配置 | 说明 |
|------|------|
| 最低显卡要求 | NVIDIA GTX 1060 6GB / AMD RX 580 8GB 及以上 |
| 推荐显卡 | NVIDIA RTX 3060 12GB 及以上 |
| 显存 | 最低 6GB，推荐 8GB 及以上 |
| 无独显 | 可使用 CPU 运行模型，但推理速度会显著降低（建议 16GB 以上内存） |

> **注意**：Ollama 支持自动检测 GPU 并使用 GPU 加速。无独立显卡时，模型将自动切换为 CPU 运行模式。

#### 其他硬件要求

- **网络**：稳定互联网连接，用于下载依赖包及 AI 模型（首次安装需要）
- **端口**：确保以下端口可用：`11434`（Ollama）、`8000`（后端）、`3000`（前端）

### 1.3 软件依赖

| 软件 | 最低版本 | 下载地址 |
|------|---------|---------|
| Python | 3.10 及以上 | https://www.python.org/downloads/ |
| Node.js | 18.x 及以上 | https://nodejs.org/ |
| npm | 9.x 及以上 | 随 Node.js 自动安装 |
| Ollama | 最新版 | https://ollama.com/ |

---

## 二、详细安装步骤

### 2.1 下载压缩包

#### 方式一：从 Git 仓库克隆（推荐）

```powershell
# 使用 Git 克隆项目
git clone <项目仓库地址>
cd 微信程序开发
```

#### 方式二：下载 ZIP 压缩包

1. 访问项目仓库页面，点击 **"Code"** 按钮
2. 选择 **"Download ZIP"**
3. 下载完成后进行校验（见下方步骤）

#### 文件校验（ZIP 方式）

下载完成后，建议校验文件完整性：

```powershell
# Windows PowerShell 计算 SHA256
Get-FileHash -Path "微信程序开发.zip" -Algorithm SHA256

# Linux / macOS 计算 SHA256
sha256sum 微信程序开发.zip
```

将计算结果与发布页面提供的 SHA256 值进行对比，确保一致后再解压。

### 2.2 解压操作

#### Windows 系统

- **推荐工具**：系统自带解压功能 / 7-Zip / WinRAR
- **操作步骤**：
  1. 右键点击 ZIP 文件
  2. 选择"全部提取"（系统自带）或"解压到当前文件夹"（7-Zip）
  3. 等待解压完成

#### macOS / Linux 系统

```bash
# 解压 ZIP 文件
unzip 微信程序开发.zip -d /目标/路径/
```

#### 解压路径要求

> **重要**：安装路径中**不能包含中文字符及特殊字符**，否则可能导致 Python 或 Node.js 依赖安装失败。
>
> 推荐路径示例：
> - Windows：`C:\Projects\WeChatCaseAnalysis\`
> - macOS / Linux：`~/Projects/WeChatCaseAnalysis/`

#### 解压后目录结构

```
微信程序开发/
├── README.md                 # 项目说明文档
├── backend/                  # 后端服务（FastAPI）
│   ├── app/                  # 后端核心代码
│   ├── main.py               # 后端启动入口
│   ├── requirements.txt      # Python 依赖清单
│   ├── .env.example          # 环境变量模板
│   └── alembic/              # 数据库迁移工具
├── frontend/                 # 前端应用（Vue 3）
│   ├── src/                  # 前端源代码
│   ├── package.json          # Node.js 依赖清单
│   └── vite.config.js        # Vite 构建配置
├── data/                     # 示例案件数据
└── scripts/                  # 辅助脚本
```

### 2.3 安装 Ollama 及 AI 模型

#### 步骤 1：安装 Ollama

| 系统 | 安装方式 |
|------|---------|
| Windows | 访问 https://ollama.com/download/windows 下载安装包，双击运行 |
| macOS | 访问 https://ollama.com/download/mac 下载安装包，或执行：`brew install ollama` |
| Linux | 终端执行：`curl -fsSL https://ollama.com/install.sh | sh` |

#### 步骤 2：启动 Ollama 服务

```powershell
# Windows（安装后会自动注册为系统服务，开机自启）
# 如需手动启动：
ollama serve

# macOS / Linux
ollama serve
```

#### 步骤 3：下载 AI 模型

```powershell
# 拉取 DeepSeek-R1-7B 模型（约 4.5GB，请确保网络稳定）
ollama pull deepseek-r1:7b
```

> **提示**：如果下载速度较慢，可以设置代理（见第四章常见问题排查）。

#### 步骤 4：验证模型安装

```powershell
# 查看已安装的模型列表
ollama list

# 预期输出应包含 deepseek-r1:7b
# NAME                   ID          SIZE    MODIFIED
# deepseek-r1:7b         xxxxxxxx    4.5 GB  xxx ago
```

### 2.4 安装后端服务

#### 步骤 1：创建 Python 虚拟环境（推荐）

```powershell
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv
```

#### 步骤 2：激活虚拟环境

```powershell
# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Windows CMD
venv\Scripts\activate.bat

# macOS / Linux
source venv/bin/activate
```

> **PowerShell 执行策略问题**：如果提示"在此系统上禁止运行脚本"，请以管理员身份运行 PowerShell 后执行：
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

#### 步骤 3：安装后端依赖

```powershell
pip install -r requirements.txt
```

安装过程可能需要几分钟，请耐心等待。

> **如果某些依赖安装失败**：
> - `PyMuPDF`：需要 C++ 编译环境，可尝试 `pip install PyMuPDF --only-binary :all:`
> - `paddlepaddle`：如需 CPU 版本，使用 `pip install paddlepaddle`；如需 GPU 版本，参考 https://www.paddlepaddle.org.cn/

#### 步骤 4：配置环境变量

```powershell
# 复制环境变量模板
# Windows PowerShell
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

#### 步骤 5：编辑 .env 文件

使用文本编辑器打开 `.env` 文件，根据实际情况修改配置。重点关注以下配置项：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SERVER_PORT` | `8000` | 后端服务端口，如果被占用可修改为其他端口 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 服务地址，一般无需修改 |
| `OLLAMA_MODEL` | `deepseek-r1:7b` | AI 模型名称，需与 `ollama pull` 的模型一致 |
| `DATABASE_URL` | `sqlite:///./app.db` | 数据库连接字符串 |

#### 步骤 6：初始化数据库

```powershell
# 执行数据库迁移（首次安装）
alembic upgrade head
```

#### 步骤 7：验证配置

配置成功后，运行以下命令进行验证：

```powershell
# 检查 Python 环境
python -c "import fastapi, uvicorn, sqlalchemy; print('依赖检查通过')"

# 预期输出：依赖检查通过
```

### 2.5 安装前端服务

#### 步骤 1：安装前端依赖

```powershell
# 进入前端目录
cd frontend

# 安装依赖（确保已安装 Node.js 18+）
npm install
```

#### 步骤 2：验证安装

```powershell
# 检查前端依赖是否正确安装
npm run lint

# 如无报错，则说明依赖安装成功
```

### 2.6 启动服务

#### 方式一：使用三个终端分别启动（推荐用于开发调试）

```powershell
# ============ 终端 1：启动 Ollama 服务 ============
# （如果 Ollama 已注册为系统服务，可跳过此步）
ollama serve

# ============ 终端 2：启动后端服务 ============
cd backend
.\venv\Scripts\Activate.ps1   # Windows PowerShell
# source venv/bin/activate    # macOS / Linux
python run.py

# ============ 终端 3：启动前端服务 ============
cd frontend
npm run dev
```

#### 方式二：后台运行（推荐用于生产环境）

```powershell
# 后端后台运行（Windows）
Start-Process -WindowStyle Hidden -FilePath "python" -ArgumentList "run.py" -WorkingDirectory "backend"

# 后端后台运行（Linux / macOS）
cd backend && nohup python run.py > backend.log 2>&1 &

# 前端后台运行（Linux / macOS）
cd frontend && nohup npm run dev > frontend.log 2>&1 &
```

#### 服务启动验证

1. **后端服务验证**：
   - 浏览器访问：`http://localhost:8000/health`
   - 预期返回 JSON：
     ```json
     {
       "status": "healthy",
       "ollama": "available",
       "model": "deepseek-r1:7b",
       "timestamp": "2026-05-26T10:00:00Z"
     }
     ```
   - API 文档：`http://localhost:8000/docs`（Swagger UI）

2. **前端服务验证**：
   - 浏览器访问：`http://localhost:5173`（默认端口，如被占用会自动递增）
   - 应能看到系统欢迎页面

3. **日志文件检查**：
   - 后端日志位于：`backend/logs/app_YYYY-MM-DD.log`
   - 查看是否有 `ERROR` 级别的日志信息

---

## 三、配置说明

### 3.1 环境变量配置

#### 临时环境变量设置

```powershell
# Windows PowerShell
$env:SERVER_PORT = "8080"
$env:OLLAMA_MODEL = "deepseek-r1:14b"

# Linux / macOS (bash / zsh)
export SERVER_PORT=8080
export OLLAMA_MODEL=deepseek-r1:14b
```

#### 永久环境变量配置

**Windows**：
1. 右键"此电脑" → "属性" → "高级系统设置" → "环境变量"
2. 在"系统变量"或"用户变量"中新建/编辑变量
3. 点击"确定"保存后，**需要重启终端**才能生效

**macOS / Linux**：
```bash
# 编辑 shell 配置文件（根据使用的 shell 选择对应文件）
# bash 用户
echo 'export SERVER_PORT=8080' >> ~/.bashrc
source ~/.bashrc

# zsh 用户（macOS 默认）
echo 'export SERVER_PORT=8080' >> ~/.zshrc
source ~/.zshrc
```

#### 关键环境变量说明

| 变量名 | 取值 | 说明 |
|--------|------|------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 服务地址 |
| `OLLAMA_MODEL` | `deepseek-r1:7b` | 使用的 AI 模型名称 |
| `SERVER_HOST` | `0.0.0.0` | 后端监听地址（`0.0.0.0` 表示所有网卡） |
| `SERVER_PORT` | `8000` | 后端服务端口 |
| `DEBUG` | `true` / `false` | 开发模式（`true` 支持热重载） |
| `DATABASE_URL` | `sqlite:///./app.db` | 数据库连接字符串 |
| `JWT_SECRET_KEY` | 随机字符串 | JWT 密钥（生产环境必须配置） |
| `CORS_ORIGINS` | `http://localhost:5173` | 允许跨域访问的前端地址 |
| `APP_ENV` | `development` / `production` | 运行环境标识 |

### 3.2 Ollama 配置

#### 配置文件路径

| 系统 | 配置路径 |
|------|---------|
| Windows | `%USERPROFILE%\.ollama\config.json` |
| macOS | `~/.ollama/config.json` |
| Linux | `~/.ollama/config.json` |

#### 核心配置项

```json
{
  "OLLAMA_HOST": "0.0.0.0:11434",
  "OLLAMA_ORIGINS": "*",
  "OLLAMA_KEEP_ALIVE": "5m",
  "OLLAMA_NUM_PARALLEL": 1
}
```

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `OLLAMA_HOST` | 监听地址与端口 | `127.0.0.1:11434` |
| `OLLAMA_ORIGINS` | 允许的来源 | `*` |
| `OLLAMA_KEEP_ALIVE` | 模型在内存中保留时间 | `5m` |
| `OLLAMA_NUM_PARALLEL` | 并发请求数 | `1` |
| `OLLAMA_NUM_GPU_LAYERS` | GPU 推理层数（数字越大 GPU 使用越多） | 自动检测 |

#### 配置修改生效方法

修改配置后，需要重启 Ollama 服务：

```powershell
# Windows
# 方式1：任务管理器中找到 Ollama 进程，结束任务后重新启动
# 方式2：服务管理器中重启 Ollama 服务
ollama serve

# Linux / macOS
pkill ollama
ollama serve
```

### 3.3 数据库配置

#### 支持的数据库类型

| 数据库类型 | 版本要求 | 连接字符串格式 |
|-----------|---------|---------------|
| SQLite（默认） | 3.x | `sqlite:///./app.db` |
| PostgreSQL | 12+ | `postgresql://user:password@localhost:5432/dbname` |
| MySQL | 8.0+ | `mysql+pymysql://user:password@localhost:3306/dbname` |

#### 配置步骤

1. 编辑 `.env` 文件中的 `DATABASE_URL`：

```env
# 使用 SQLite（默认）
DATABASE_URL=sqlite:///./app.db

# 使用 PostgreSQL
DATABASE_URL=postgresql://username:password@localhost:5432/case_analysis

# 使用 MySQL
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/case_analysis
```

2. 执行数据库迁移：

```powershell
cd backend
alembic upgrade head
```

#### 连接测试

```powershell
# 启动后端服务后访问健康检查
curl http://localhost:8000/health

# 如果数据库连接正常，服务应正常启动
```

---

## 四、常见问题排查

### 4.1 端口占用问题

#### 查看端口占用

```powershell
# Windows 查看端口占用
netstat -ano | findstr :8000
# 输出示例：TCP    0.0.0.0:8000    0.0.0.0:0    LISTENING    12345
# 最后一列是进程 PID

# 查看对应进程
tasklist | findstr 12345

# Linux / macOS
lsof -i :8000
# 或
netstat -tulpn | grep :8000
```

#### 解决方案

**方案 1：停止占用进程**

```powershell
# Windows 停止进程
taskkill /PID 12345 /F

# Linux / macOS
kill -9 12345
```

**方案 2：修改服务端口**

编辑 `.env` 文件，修改端口配置：

```env
# 将后端端口改为 8080
SERVER_PORT=8080
```

### 4.2 依赖缺失问题

#### 常见依赖项及安装命令

| 依赖项 | 用途 | Windows | Linux | macOS |
|--------|------|---------|-------|-------|
| Python 3.10+ | 后端运行环境 | https://www.python.org/downloads/ | `sudo apt install python3 python3-venv` | `brew install python` |
| Node.js 18+ | 前端构建环境 | https://nodejs.org/ | `sudo apt install nodejs npm` | `brew install node` |
| Visual C++ Build Tools | 编译部分 Python 包 | https://visualstudio.microsoft.com/visual-cpp-build-tools/ | - | - |
| Git | 代码管理 | https://git-scm.com/ | `sudo apt install git` | `brew install git` |

#### 依赖版本不兼容处理

```powershell
# 如果遇到依赖冲突，尝试升级 pip 后重新安装
python -m pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir

# 如果特定包报错，单独安装
pip install <包名>==<版本号>
```

### 4.3 模型下载失败

#### 网络问题排查

1. 检查网络连接是否正常：

```powershell
ping ollama.com
```

2. 如果下载中断或超时，尝试使用代理：

```powershell
# Windows PowerShell
$env:HTTPS_PROXY = "http://your-proxy-server:port"
ollama pull deepseek-r1:7b

# Linux / macOS
export HTTPS_PROXY=http://your-proxy-server:port
ollama pull deepseek-r1:7b
```

3. 检查 Ollama 服务是否正常运行：

```powershell
# 查看 Ollama 服务状态
curl http://localhost:11434/api/tags

# 预期返回已下载的模型列表
```

#### 手动下载模型

如果自动下载始终失败，可以手动下载模型文件：

1. 访问 Ollama 模型仓库获取模型文件
2. 将模型文件放置到默认目录：

| 系统 | 模型存储路径 |
|------|-------------|
| Windows | `%USERPROFILE%\.ollama\models` |
| macOS | `~/.ollama/models` |
| Linux | `~/.ollama/models` |

3. 重新启动 Ollama 服务：

```powershell
ollama serve
```

### 4.4 服务启动失败

#### 日志文件位置

| 模块 | 日志路径 |
|------|---------|
| 后端应用日志 | `backend/logs/app_YYYY-MM-DD.log` |
| Ollama 日志 | 终端输出或系统日志 |

#### 常见启动错误及解决方案

| 错误信息 | 可能原因 | 解决方案 |
|---------|---------|---------|
| `Ollama startup check failed` | Ollama 服务未启动 | 运行 `ollama serve` 启动服务 |
| `Model 'xxx' not found` | 模型未下载 | 运行 `ollama pull <模型名>` |
| `Address already in use` | 端口被占用 | 修改 `.env` 中的 `SERVER_PORT` 或停止占用进程 |
| `ModuleNotFoundError` | Python 依赖未安装 | 重新运行 `pip install -r requirements.txt` |
| `CORS_ORIGINS 不允许使用通配符` | 生产环境使用了 `*` | 修改为具体域名，或将 `APP_ENV` 改为 `development` |
| `JWT_SECRET_KEY 未配置` | 生产环境未配置 JWT 密钥 | 运行密钥生成脚本并配置到 `.env` |

---

## 五、首次使用指南

### 5.1 系统访问

#### Web 界面访问

启动所有服务后，打开浏览器访问：

```
http://localhost:5173
```

> **注意**：端口号可能与示例不同，请查看前端启动时终端输出的实际端口。

#### API 接口访问

| 接口 | URL | 说明 |
|------|-----|------|
| 健康检查 | `GET http://localhost:8000/health` | 检查服务状态 |
| API 文档 | `GET http://localhost:8000/docs` | Swagger UI 交互式文档 |
| 分析接口 | `POST http://localhost:8000/api/analyze` | 提交案件分析请求 |

#### 本地访问与远程访问配置

| 场景 | 配置 | 说明 |
|------|------|------|
| 本地访问 | `SERVER_HOST=0.0.0.0` | 允许本机及局域网访问 |
| 远程访问 | `SERVER_HOST=0.0.0.0` + 防火墙开放端口 | 需配置防火墙及 CORS 安全策略 |

**远程访问注意事项**：
- 修改 `.env` 中的 `CORS_ORIGINS`，将允许的访问地址添加到列表中
- 确保 `APP_ENV=production`，并配置安全的 `JWT_SECRET_KEY`
- 建议在远程访问前配置 HTTPS 及认证机制

### 5.2 默认管理员账号

首次启动系统时，会自动创建默认管理员账号：

| 字段 | 默认值 |
|------|--------|
| 用户名 | `admin` |
| 密码 | `admin123` |

> **安全警告**：首次登录后请立即修改默认密码！生产环境必须在 `.env` 中修改 `DEFAULT_ADMIN_PASSWORD`。

### 5.3 Demo 案例运行

系统内置了三个 Demo 案例，覆盖三种不同的分析结果：

| 案例 | 场景 | 预期结论 |
|------|------|---------|
| 案例一 | 明显明知 - 低价大量收购银行卡 | 明显具有"主观明知" |
| 案例二 | 边缘情况 - 代购争议 | 处于明知与不明知的边缘 |
| 案例三 | 正常交易 - 确实不明知 | 确实不具有"主观明知" |

#### 运行步骤

1. 确保 Ollama、后端、前端三个服务均已启动
2. 浏览器访问 `http://localhost:5173`
3. 在欢迎页面选择预设的 Demo 案例
4. 点击 **"开始分析"** 按钮
5. 等待 AI 分析完成（首次分析可能需要 1-3 分钟）
6. 自动跳转至报告页面，查看三维度分析结果：
   - **行为评估**：行为异常度评分及理由
   - **认知评估**：认知匹配度分析及模式匹配
   - **辩解评估**：辩解合理性分析及矛盾点

#### 预期输出结果

分析报告应包含以下结构化的 JSON 数据：

```json
{
  "behavior_assessment": {
    "score": 8.5,
    "reasoning": "行为分析推理过程...",
    "key_indicators": ["低价收购", "大量办卡"]
  },
  "cognitive_assessment": {
    "score": 7.0,
    "reasoning": "认知匹配分析...",
    "pattern_match": "匹配的作案模式描述..."
  },
  "defense_assessment": {
    "score": 3.0,
    "reasoning": "辩解合理性分析...",
    "contradictions": ["矛盾点描述"]
  },
  "overall_summary": "整体分析总结..."
}
```

#### Demo 案例自定义修改

如需添加或修改 Demo 案例：

1. 编辑前端源代码：`frontend/src/data/demoCases.js`
2. 按照现有格式添加新的案例对象
3. 保存后，前端热重载会自动生效

### 5.4 输入数据格式要求

| 项目 | 要求 |
|------|------|
| 输入类型 | 纯文本 |
| 最小长度 | 10 字符 |
| 最大长度 | 50,000 字符 |
| 建议包含内容 | 嫌疑人信息、案件事实、交易细节、沟通记录、辩解内容、证据线索 |

---

## 六、附录

### A. 快速启动命令参考

```powershell
# ===== 完整启动流程（三个终端） =====

# 终端 1：Ollama
ollama serve

# 终端 2：后端
cd backend
.\venv\Scripts\Activate.ps1
python run.py

# 终端 3：前端
cd frontend
npm run dev
```

### B. 端口速查表

| 服务 | 默认端口 | 配置变量 |
|------|---------|---------|
| Ollama | 11434 | `OLLAMA_BASE_URL` |
| 后端 API | 8000 | `SERVER_PORT` |
| 前端开发服务器 | 5173 | Vite 配置（自动递增） |
| 推理服务器 | 8001 | `INFERENCE_PORT` |

### C. 性能优化建议

| 场景 | 建议 |
|------|------|
| 模型加载慢 | 增加 `OLLAMA_KEEP_ALIVE` 时间，避免频繁重新加载 |
| 推理速度慢 | 配置 GPU 加速（设置 `OLLAMA_NUM_GPU_LAYERS`） |
| 内存不足 | 关闭不需要的服务，或换用更小的模型 |
| 首次分析慢 | 系统会在启动时预热 Demo 案例缓存，首次响应可能较慢 |

### D. 升级维护

| 操作 | 命令 |
|------|------|
| 更新后端依赖 | `pip install -r requirements.txt --upgrade` |
| 更新前端依赖 | `npm update` |
| 更新 Ollama | 重新下载安装包覆盖安装 |
| 更新模型 | `ollama pull deepseek-r1:7b` |
| 数据库迁移 | `alembic upgrade head` |
