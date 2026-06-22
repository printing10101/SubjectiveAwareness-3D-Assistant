# 帮信罪"主观明知"智能分析系统（MVP）

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3.x-4FC08D.svg)](https://vuejs.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](#开源协议)

---

## 项目背景与目标

### 背景意义

**帮助信息网络犯罪活动罪**（简称"帮信罪"）是近年来司法实践中高发、频涉的罪名之一。该罪的核心构成要件——**"主观明知"**——在实务中往往难以认定。传统办案模式下，检察官需要人工梳理案件事实、比对既有案例、综合判断嫌疑人的主观认知状态，这一过程高度依赖办案经验，且存在以下痛点：

- **认定标准不统一**：不同检察官对"明知"的判断可能存在主观差异
- **办案效率受限**：人工阅读卷宗、比对案例耗时较长，难以应对案件量激增
- **经验传承困难**：资深检察官的办案经验难以系统性地传递给新人

### 解决的实际问题

本系统致力于通过人工智能技术，辅助检察官快速、一致地完成"主观明知"要素的审查判断，具体解决以下问题：

1. **标准化分析框架**：将司法实践中的审查逻辑固化为三维度分析模型，确保分析过程可追溯、可复现
2. **自动化审查辅助**：AI 自动提取案件关键事实、比对行为模式、评估辩解合理性，大幅缩短人工审查时间
3. **智能类案参考**：基于知识图谱技术，自动检索相似案例及量刑建议，为检察官提供决策参考

### 核心目标

- 验证大语言模型在司法领域复杂判断任务中的可行性
- 构建可解释、可审计的 AI 辅助分析流程
- 为司法智能化改革提供可落地的 MVP 验证原型

---

## 主要功能特性

### 核心功能

| 功能模块 | 说明 |
|----------|------|
| **三维度智能分析** | 基于行为评估、认知匹配、辩解合理性三个维度，对案件"主观明知"要素进行结构化分析 |
| **可视化分析报告** | 自动生成包含评分、推理过程、关键指标的结构化分析报告 |
| **Demo 案例体验** | 内置三类典型案例（明显明知/边缘情况/确实不明知），支持一键体验完整分析流程 |
| **案件管理** | 支持案件的创建、查询、更新与删除，提供持久化存储 |
| **知识图谱检索** | 基于 Neo4j 图数据库，实现相似案例检索与法律知识图谱展示 |
| **文档解析** | 支持 PDF/Word 案件材料自动解析，提取文本内容进行分析 |
| **实验对比** | 支持不同模型版本的分析结果对比，辅助模型评估与选型 |

### 技术亮点

- **本地化部署**：基于 Ollama + DeepSeek-R1 开源模型，数据不出本机，满足司法数据安全要求
- **可解释输出**：每个维度的评分均附带推理过程和关键依据，非"黑箱"判断
- **RESTful API**：前后端完全解耦，提供标准化 API 接口，易于集成至现有检察业务系统
- **异步架构**：全链路异步处理（httpx + uvicorn），高并发场景下保持稳定响应

---

## 技术架构说明

### 开发环境要求

```bash
# 安装 pre-commit 钩子（提交前自动进行代码规范检查）
pip install pre-commit
pre-commit install
# 可选：全量运行所有钩子验证
pre-commit run --all-files
```

### 完整技术栈

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| **前端** | Vue 3 + Vue Router + Pinia + Vite | 单页应用，响应式状态管理 |
| **后端** | FastAPI + Pydantic + Uvicorn | RESTful API，自动数据校验 |
| **AI模型** | Ollama + DeepSeek-R1-7B | 本地部署的开源大语言模型 |
| **HTTP客户端** | httpx（后端）+ Axios（前端） | 异步HTTP通信 |

### 系统架构图

```
┌──────────────┐     HTTP请求      ┌──────────────┐    本地API调用     ┌──────────────┐
│   Vue 3 前端  │ ────────────────▶ │  FastAPI后端  │ ────────────────▶ │   Ollama服务   │
│   (Port 3000) │ ◀──────────────── │  (Port 8000)  │ ◀──────────────── │  (Port 11434)  │
└──────────────┘                   └──────────────┘                   └──────────────┘
  - 案件输入界面                      - 三维度分析逻辑                     - DeepSeek-R1-7B
  - 报告展示                          - LLM Prompt管理                     - 模型推理
  - Demo案例                         - CORS中间件                         - JSON解析
```

---

## 环境部署指南

### 前置要求

| 软件 | 最低版本 | 说明 |
|------|----------|------|
| Node.js | 18.x 或更高 | 前端构建环境 |
| Python | 3.10 或更高 | 后端运行环境 |
| Ollama | 最新版 | 本地LLM服务 |

### 一、安装 Ollama 及 AI 模型

#### 1. 安装 Ollama

访问 [Ollama 官网](https://ollama.com/) 下载并安装对应系统版本。

#### 2. 启动 Ollama 服务

```powershell
# 启动 Ollama 服务（Windows）
ollama serve

# 或使用以下命令直接拉取并运行模型
ollama run deepseek-r1:7b
```

#### 3. 下载模型

```powershell
# 拉取 DeepSeek-R1-7B 模型（约 4GB）
ollama pull deepseek-r1:7b
```

#### 4. 验证安装

```powershell
# 查看已安装的模型列表
ollama list

# 预期输出应包含 deepseek-r1:7b
```

**配置说明**：
- Ollama 默认监听端口：`11434`
- 模型文件默认存储路径：`~/.ollama/models`

---

### 二、后端服务部署

#### 1. 创建 Python 虚拟环境（推荐）

```powershell
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境（Windows PowerShell）
.\venv\Scripts\Activate.ps1
```

#### 2. 安装后端依赖

```powershell
cd backend

# 安装所有依赖
pip install -r requirements.txt
```

**依赖清单**：

| 包名 | 最低版本 | 用途 |
|------|----------|------|
| fastapi[all] | >=0.100.0 | Web 框架 |
| uvicorn[standard] | >=0.23.2 | ASGI 服务器 |
| pydantic | >=2.0.0 | 数据校验 |
| httpx | >=0.24.1 | 异步 HTTP 客户端 |
| python-multipart | >=0.0.6 | 表单数据解析 |
| python-dotenv | >=1.0.0 | 环境变量管理 |
| loguru | >=0.7.0 | 日志管理 |

#### 3. 配置环境变量

```powershell
# 复制环境变量模板
cp .env.example .env
```

**.env 文件说明**：

```env
# Ollama 服务地址
OLLAMA_BASE_URL=http://localhost:11434

# 使用的模型名称
OLLAMA_MODEL=deepseek-r1:7b

# 后端服务监听地址
SERVER_HOST=0.0.0.0

# 后端服务端口
SERVER_PORT=8000
```

#### 4. 启动后端服务

```powershell
# 方式一：直接运行（开发模式，支持热重载）
python main.py

# 方式二：使用 uvicorn 命令
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**启动验证**：

- API 文档：访问 `http://localhost:8000/docs`
- 健康检查：访问 `http://localhost:8000/health`
- 日志文件：`backend/logs/app_YYYY-MM-DD.log`

---

### 三、前端项目部署

#### 1. 安装前端依赖

```powershell
cd frontend

# 安装所有依赖
npm install
```

#### 2. 启动开发服务器

```powershell
# 启动开发服务器（默认端口 3000）
npm run dev
```

**环境变量配置**：

前端通过 `vite.config.js` 中的代理配置将 API 请求转发到后端：

```js
// vite.config.js
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

#### 3. 构建生产版本

```powershell
# 构建生产环境静态文件
npm run build

# 预览构建结果
npm run preview
```

构建产物输出至 `frontend/dist/` 目录，可部署至任意静态服务器（如 Nginx）。

---

### 四、完整启动流程

```powershell
# 终端 1：启动 Ollama 服务
ollama serve

# 终端 2：启动后端服务
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py

# 终端 3：启动前端服务
cd frontend
npm install
npm run dev
```

启动完成后，访问 `http://localhost:5173` 即可使用系统。

---

## 开发命令速查 (Makefile & PowerShell)

为统一开发流程、减少团队协作中的命令差异,项目根目录提供 **Makefile**(类 Unix 系统)与 `scripts/dev.ps1`(Windows / PowerShell 跨平台)两套等价命令集。两者的命令名、行为和输出一致,可按操作系统习惯任选其一使用。

### 命令列表

| 命令 | 说明 |
|------|------|
| `help` | 以表格形式显示所有可用命令及其说明 |
| `install` | 安装后端 (pip) + 前端 (npm) 依赖 |
| `dev` | 并行启动后端 uvicorn 与前端 vite 开发服务器 |
| `test` | 运行后端 pytest 与前端 vitest 测试,生成覆盖率报告 |
| `lint` | ruff + mypy + eslint 三重代码检查 |
| `format` | ruff format + prettier 统一代码风格 |
| `build` | 生成 `requirements.lock` 并构建前端生产版本 |
| `docker` | `docker compose up -d` 启动全部容器(含健康检查) |
| `docker-down` | 停止并清理所有 Docker 容器、网络、卷 |
| `docker-logs` | 实时查看容器日志,可指定服务名 |
| `clean` | 清理 `__pycache__` / `.pytest_cache` / `.ruff_cache` / `node_modules` / `dist` 等 |
| `db-migrate` | 执行 `alembic upgrade head` 数据库迁移 |
| `db-reset` | 降级再升级,重置数据库(慎用) |
| `db-seed` | 运行 `seed_data.py` 填充种子数据 |
| `ci` | 按顺序执行 `lint` + `test`,模拟 CI 检查 |

### 一、类 Unix / macOS / Linux / WSL(GNU Make 4.0+)

```bash
# 查看帮助
make help

# 安装依赖
make install

# 启动开发服务
make dev

# 跑测试 + 检查
make test
make lint

# 启动 / 停止 Docker
make docker
make docker-logs        # 查看所有服务
make docker-logs s=api  # 仅查看 api 服务
make docker-down

# 数据库相关
make db-migrate
make db-reset
make db-seed

# 一键 CI 校验
make ci
```

### 二、Windows (PowerShell 5.1 / PowerShell Core 7+)

> 首次使用需在 PowerShell 中允许执行本地脚本(如未配置):
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

```powershell
# 查看帮助(支持 Tab 键自动补全)
.\scripts\dev.ps1 help

# 安装依赖
.\scripts\dev.ps1 install

# 启动开发服务
.\scripts\dev.ps1 dev

# 跑测试 + 检查
.\scripts\dev.ps1 test
.\scripts\dev.ps1 lint

# 启动 / 停止 Docker
.\scripts\dev.ps1 docker
.\scripts\dev.ps1 docker-logs             # 查看所有服务
.\scripts\dev.ps1 docker-logs -Service api # 仅查看 api 服务
.\scripts\dev.ps1 docker-down

# 数据库相关
.\scripts\dev.ps1 db-migrate
.\scripts\dev.ps1 db-reset
.\scripts\dev.ps1 db-seed

# 一键 CI 校验
.\scripts\dev.ps1 ci
```

### 三、注意事项

1. **虚拟环境**: `make install` / `make test` / `make lint` 等命令默认依赖项目根目录下的 `.venv/` 虚拟环境;若尚未创建,请先执行 `python -m venv .venv`。
2. **路径兼容**: Makefile 通过 `ifeq ($(OS),Windows_NT)` 自动切换 Windows/Unix 路径处理,PowerShell 脚本统一使用 `Join-Path` 构造路径。
3. **日志记录**: PowerShell 脚本会在 `logs/dev-YYYYMMDD.log` 中记录每次执行的命令与结果,便于排查问题。
4. **退出码语义**: `make ci` 与 `.\scripts\dev.ps1 ci` 会在任意子命令失败时立即返回非零退出码,可在 CI/CD 流水线中直接对接。
5. **新增命令**: 同步修改 `Makefile` 与 `scripts/dev.ps1` 中的 `switch` 分发,保持两套工具的命令集合一致。

---

## 项目结构

```
微信程序开发/
├── README.md                     # 项目文档（本文件）
├── INSTALLATION.md               # 详细安装部署指南
├── LICENSE                       # MIT 开源许可证
│
├── backend/                      # 后端服务（FastAPI）
│   ├── app/                      # 核心应用代码
│   │   ├── models/               # SQLAlchemy 数据模型
│   │   ├── routers/              # API 路由模块
│   │   ├── schemas/              # Pydantic 数据校验
│   │   ├── services/             # 业务逻辑层（含pipeline、prompts）
│   │   ├── utils/                # 工具函数（含cache、auth）
│   │   ├── config.py             # 配置管理
│   │   ├── database.py           # 数据库连接
│   │   └── main.py               # FastAPI 应用工厂
│   ├── alembic/                  # 数据库迁移
│   ├── tests/                    # 单元测试
│   ├── run.py                    # 推荐启动脚本
│   ├── requirements.txt          # Python 依赖清单
│   ├── .env.example              # 环境变量模板
│   └── logs/                     # 运行日志（自动生成）
│
├── frontend/                     # 前端应用（Vue 3）
│   ├── src/
│   │   ├── router/               # Vue Router 路由配置
│   │   ├── stores/               # Pinia 状态管理
│   │   ├── views/                # 页面组件
│   │   └── data/                 # 配置与示例数据
│   ├── vite.config.js            # Vite 构建配置
│   └── package.json              # 前端依赖清单
│
├── ml/                           # 机器学习相关代码
│   ├── finetune/                 # 模型微调代码（基于Unsloth）
│   │   ├── scripts/              # 训练、合并、测试脚本
│   │   ├── config/               # 微调配置文件
│   │   └── data/                 # 训练数据集
│   └── inference/                # 推理代理服务
│
├── scripts/                      # 运维与工具脚本
│   ├── train_lora.py             # LoRA微调入口
│   ├── evaluate_model.py         # 模型评估脚本
│   ├── download_model.py         # 模型下载工具
│   ├── generate_jwt_secret.py    # JWT密钥生成
│   └── ...                       # 其他工具脚本
│
├── data/                         # 示例案件数据
│   └── raw/                      # JSON 格式原始案例
│
├── .cache/                       # 统一缓存目录
│   └── unsloth_compiled_cache/   # Unsloth编译缓存
│
└── .venv/                        # Python 虚拟环境
```

### 核心模块说明

| 模块 | 文件/目录 | 功能描述 |
|------|-----------|----------|
| **API 路由** | `backend/app/routers/` | RESTful API 路由（案件分析、案件管理、知识图谱、报告生成等） |
| **业务逻辑** | `backend/app/services/` | 核心业务服务（分析服务、案件服务、知识图谱、相似案例、量刑建议、推理管线） |
| **数据模型** | `backend/app/models/` | SQLAlchemy ORM 模型（案件、分析记录、用户、日志等） |
| **数据校验** | `backend/app/schemas/` | Pydantic 请求/响应校验模型 |
| **配置管理** | `backend/app/config.py` | 环境变量加载与配置校验 |
| **应用工厂** | `backend/app/main.py` | FastAPI 应用创建、中间件注册、生命周期管理 |
| **启动脚本** | `backend/run.py` | 推荐的服务启动入口（含启动前检查） |
| **模型微调** | `ml/finetune/` | Unsloth LoRA微调，支持15种Trainer类型 |
| **推理服务** | `ml/inference/` | Ollama推理代理服务，监听8001端口 |
| **状态管理** | `frontend/src/stores/` | Pinia store，管理案件数据流与分析状态 |
| **视图组件** | `frontend/src/views/` | 核心页面组件（欢迎页、分析页、报告页等） |

---

## 前后端交互与数据流

### API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/health` | 健康检查，返回后端及 Ollama 连接状态 |
| POST | `/api/analyze` | 提交案件文本，获取三维度分析报告 |

### 请求数据格式

```json
{
  "case_text": "案件事实描述文本..."
}
```

### 响应数据格式

```json
{
  "behavior_assessment": {
    "score": 8.5,
    "reasoning": "行为分析推理过程...",
    "key_indicators": ["指标1", "指标2"]
  },
  "cognitive_assessment": {
    "score": 7.0,
    "reasoning": "认知匹配分析...",
    "pattern_match": "匹配的作案模式描述..."
  },
  "defense_assessment": {
    "score": 3.0,
    "reasoning": "辩解合理性分析...",
    "contradictions": ["矛盾点1", "矛盾点2"]
  },
  "overall_summary": "整体分析总结..."
}
```

### 数据流向

```
用户在 MainView.vue 输入案件事实
        │
        ▼
analysisStore.js 调用 POST /api/analyze
        │
        ▼
FastAPI (main.py) 接收请求，构建 Prompt
        │
        ▼
httpx 发送请求至 Ollama (deepseek-r1:7b)
        │
        ▼
解析 LLM 返回的 JSON，校验数据模型
        │
        ▼
返回 AnalyzeResponse 至前端
        │
        ▼
前端跳转至 ReportView.vue 展示报告
```

---

## 功能演示说明

### Demo 案例操作步骤

系统内置三个典型 Demo 案例，覆盖三种判断结果：

| 案例 ID | 案例名称 | 预期结论 | 文件路径 |
|---------|----------|----------|----------|
| `case_01` | 明显明知 - 低价大量收购 | 明显明知 | `frontend/src/data/demoCases.js` |
| `case_02` | 边缘情况 - 代购争议 | 边缘情况 | `frontend/src/data/demoCases.js` |
| `case_03` | 确实不明知 - 正常交易 | 确实不明知 | `frontend/src/data/demoCases.js` |

#### 操作流程

1. **启动系统**：确保 Ollama、后端、前端三个服务均已启动
2. **访问系统**：浏览器打开 `http://localhost:5173`
3. **选择案例**：在欢迎页面选择预设 Demo 案例，或在分析页面手动输入案件事实
4. **提交分析**：点击"开始分析"按钮，系统自动调用 AI 模型进行分析
5. **查看报告**：分析完成后自动跳转至报告页面，查看三维度分析结果
6. **返回重试**：可返回主页重新输入或选择其他案例

### 输入数据格式要求

- **输入类型**：纯文本
- **最小长度**：10 字符
- **最大长度**：50,000 字符
- **建议内容**：
  - 嫌疑人基本信息
  - 案件事实经过（时间、地点、行为）
  - 交易细节（价格、方式、频率）
  - 沟通记录（聊天内容、暗语使用）
  - 辩解内容（如有）
  - 相关证据线索

---

## 性能验收标准

| 指标 | 标准值 | 说明 |
|------|--------|------|
| **响应时间** | ≤ 1 分钟 | 从提交案件事实到输出完整分析报告的时间 |
| **分析准确率** | ≥ 70% | 三维度分析报告结论与专业检察官判断的一致性 |
| **稳定性** | 连续 10 个测试案例无崩溃 | 系统在处理批量案件时不应出现崩溃或异常退出 |

### 影响性能的因素

- **模型加载**：首次调用模型时需要加载至内存，响应时间可能较长
- **硬件配置**：建议至少 16GB RAM，推荐独立显卡（用于 GPU 加速推理）
- **Ollama 配置**：可通过 `OLLAMA_NUM_GPU_LAYERS` 环境变量调整 GPU 层数以优化性能

---

## 故障排查

| 问题 | 可能原因 | 解决方法 |
|------|----------|----------|
| `Cannot connect to Ollama` | Ollama 服务未启动 | 运行 `ollama serve` |
| `Model not found` | 模型未下载 | 运行 `ollama pull deepseek-r1:7b` |
| `Ollama request timed out` | 模型响应超时 | 检查硬件资源，或增大 `httpx.AsyncClient` 超时时间 |
| 前端无法获取数据 | 后端未启动或代理配置错误 | 检查后端是否在 `localhost:8000` 运行，确认 `vite.config.js` 代理配置 |
| JSON 解析失败 | LLM 输出格式异常 | 重试请求，或检查 `prompts.py` 中的 Prompt 模板 |

---

## 注意事项

1. **模型选择**：MVP 版本使用 `deepseek-r1:7b` 模型，可根据硬件条件升级至更大参数模型
2. **安全配置**：生产环境部署时，务必修改 CORS 配置，限制允许的来源域名
3. **日志管理**：日志文件按天轮转，保留 7 天，注意定期清理磁盘空间
4. **API 限流**：当前版本未实现请求限流，生产环境建议添加中间件保护

---

## 开源协议

本项目采用 **MIT 开源许可证**（MIT License）。

### 权利

- 授予任何获得本软件副本的人免费使用、复制、修改、合并、出版发行、散布、再授权及制做本软件的权利
- 上述权利可在遵守本协议前提下无限制行使

### 限制

- 本软件按"原样"提供，不提供任何形式的明示或暗示担保
- 在任何情况下，作者或版权持有人均不对因使用本软件而产生的任何索赔、损害或其他责任负责
- 软件仅供技术研究与学习用途，不构成任何法律意见或司法建议

### 免责声明

> **重要声明**：本系统仅为辅助分析工具，其输出结果不具有法律效力，不能替代专业法律判断。司法案件的分析与定罪量刑必须由具有法定资质的司法人员依据法定程序独立完成。使用本系统产生的任何后果由使用者自行承担。

完整许可证文本请参阅项目根目录下的 [LICENSE](file:///c:/Users/Lenovo/Desktop/微信程序开发/LICENSE) 文件（如存在）。

---

## 贡献者与鸣谢

### 主要贡献者

| 贡献者 | 贡献方向 |
|--------|----------|
| 项目核心团队 | 系统架构设计、三维度分析模型构建、核心代码开发 |
| AI 算法团队 | Prompt 工程设计、模型调优、分析结果验证 |
| 前端开发团队 | Vue 3 应用开发、可视化报告组件、用户体验优化 |
| 后端开发团队 | FastAPI 服务架构、数据库设计、API 接口开发 |
| 法律专家团队 | 帮信罪审查标准梳理、案例标注、分析框架验证 |

> 如需添加您的贡献者信息，请提交 Pull Request 修改此表格。

### 特别鸣谢

- **DeepSeek** — 提供 DeepSeek-R1 开源大语言模型
- **Ollama** — 提供便捷的本地 LLM 部署方案
- **FastAPI & Vue.js** — 优秀的全栈开发框架
- **Neo4j** — 提供图数据库支持

### 参与贡献

我们欢迎所有形式的贡献，包括但不限于：

1. **Fork 本仓库** → 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
2. **提交修改** → 提交您的代码 (`git commit -m 'Add some AmazingFeature'`)
3. **推送分支** → 推送到远程 (`git push origin feature/AmazingFeature`)
4. **发起 Pull Request** → 在 GitHub 上创建 PR 并描述您的改动

贡献前请确保：
- 代码符合项目的代码规范（使用 `ruff` 进行 Python 代码检查）
- 新增功能包含必要的测试
- 更新相关文档说明

---

## 联系方式与反馈渠道

### 项目维护

| 渠道 | 联系方式 |
|------|----------|
| 问题反馈 | 请通过 [GitHub Issues](../../issues) 提交 Bug 报告或功能请求 |
| 代码贡献 | 请通过 [Pull Requests](../../pulls) 提交代码改动 |
| 项目讨论 | 请通过 [GitHub Discussions](../../discussions) 参与技术讨论 |

### Issue 提交指引

提交 Issue 时，请包含以下信息：

1. **问题描述**：清晰描述您遇到的问题或建议的功能
2. **复现步骤**：提供详细的复现操作步骤
3. **环境信息**：操作系统、Python/Node.js 版本、浏览器类型等
4. **预期行为**：您期望的正确行为是什么
5. **截图/日志**：如有错误截图或日志文件，请一并提供

### 模板示例

```markdown
### 问题描述
[简要描述问题]

### 复现步骤
1. [步骤一]
2. [步骤二]
3. [步骤三]

### 预期行为
[期望的正确结果]

### 实际行为
[实际发生的结果]

### 环境信息
- 操作系统：
- Python 版本：
- Node.js 版本：
- 浏览器：
```

---

> 最后更新时间：2026-06-01
