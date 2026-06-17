# =============================================================================
# 帮信罪"主观明知"智能分析系统 — 统一构建/开发工具
# =============================================================================
# 适用版本: GNU Make 4.0+
# 使用方法:
#   make help           # 查看所有可用命令
#   make install        # 安装后端与前端依赖
#   make dev            # 并行启动开发服务
#   make test           # 运行测试
#   make lint           # 代码检查
#   make format         # 代码格式化
#   make build          # 生产构建
#   make docker         # 启动 Docker 容器
#   make clean          # 清理缓存与构建产物
# =============================================================================

# ---------- 基础配置 ----------
SHELL := /bin/bash
.DEFAULT_GOAL := help

# 颜色定义 (ANSI 转义序列)
RESET   := \033[0m
BOLD    := \033[1m
RED     := \033[31m
GREEN   := \033[32m
YELLOW  := \033[33m
BLUE    := \033[34m
MAGENTA := \033[35m
CYAN    := \033[36m
GRAY    := \033[90m

# 目录与可执行命令
BACKEND_DIR   := backend
FRONTEND_DIR  := frontend
SCRIPTS_DIR   := scripts
VENV_DIR      := .venv
PYTHON        := python
PIP           := $(VENV_DIR)/Scripts/pip.exe
PIP_UNIX      := $(VENV_DIR)/bin/pip
PYTEST        := $(VENV_DIR)/Scripts/pytest.exe
PYTEST_UNIX   := $(VENV_DIR)/bin/pytest
RUFF          := $(VENV_DIR)/Scripts/ruff.exe
RUFF_UNIX     := $(VENV_DIR)/bin/ruff
MYPY          := $(VENV_DIR)/Scripts/mypy.exe
MYPY_UNIX     := $(VENV_DIR)/bin/mypy
NPM           := npm
ALEMBIC       := $(VENV_DIR)/Scripts/alembic.exe
ALEMBIC_UNIX  := $(VENV_DIR)/bin/alembic
DOCKER_COMPOSE := docker compose

# Windows / *nix 平台兼容
ifeq ($(OS),Windows_NT)
	VENV_BIN     := $(VENV_DIR)/Scripts
	RM_DIR       := rmdir /S /Q
	RM_FILE      := del /F /Q
	PATH_SEP     := \\
else
	VENV_BIN     := $(VENV_DIR)/bin
	RM_DIR       := rm -rf
	RM_FILE      := rm -f
	PATH_SEP     := /
endif

# 显式声明伪目标
.PHONY: help install dev test lint format build docker docker-down docker-logs \
        clean db-migrate db-reset db-seed ci

# =============================================================================
# help — 以表格形式展示所有可用命令
# =============================================================================
help:
	@echo ""
	@echo "$(BOLD)$(CYAN)=================================================================$(RESET)"
	@echo "$(BOLD)$(CYAN)  帮信罪主观明知智能分析系统 — 开发命令速查表$(RESET)"
	@echo "$(BOLD)$(CYAN)=================================================================$(RESET)"
	@echo ""
	@printf "  $(BOLD)$(GREEN)%-18s$(RESET) %s\n" "命令" "功能说明"
	@printf "  $(GRAY)%-18s$(RESET) %s\n" "----------------" "----------------------------------------"
	@printf "  $(BOLD)$(YELLOW)make help$(RESET)$(GRAY)%-9s$(RESET) %s\n" "" "显示本帮助信息"
	@printf "  $(BOLD)$(YELLOW)make install$(RESET)$(GRAY)%-6s$(RESET) %s\n" "" "安装后端与前端依赖"
	@printf "  $(BOLD)$(YELLOW)make dev$(RESET)$(GRAY)%-10s$(RESET) %s\n" "" "并行启动后端 + 前端开发服务"
	@printf "  $(BOLD)$(YELLOW)make test$(RESET)$(GRAY)%-9s$(RESET) %s\n" "" "执行后端 pytest + 前端 npm test"
	@printf "  $(BOLD)$(YELLOW)make lint$(RESET)$(GRAY)%-9s$(RESET) %s\n" "" "执行 ruff/mypy/eslint 检查"
	@printf "  $(BOLD)$(YELLOW)make format$(RESET)$(GRAY)%-7s$(RESET) %s\n" "" "ruff format + prettier 格式化"
	@printf "  $(BOLD)$(YELLOW)make build$(RESET)$(GRAY)%-8s$(RESET) %s\n" "" "生成依赖锁文件 + 前端生产构建"
	@printf "  $(BOLD)$(YELLOW)make docker$(RESET)$(GRAY)%-7s$(RESET) %s\n" "" "使用 docker-compose 启动所有服务"
	@printf "  $(BOLD)$(YELLOW)make docker-down$(RESET)$(GRAY)%-3s$(RESET) %s\n" "" "停止并移除所有 Docker 资源"
	@printf "  $(BOLD)$(YELLOW)make docker-logs$(RESET)$(GRAY)%-3s$(RESET) %s\n" "" "查看服务容器日志 (用法: make docker-logs s=api)"
	@printf "  $(BOLD)$(YELLOW)make clean$(RESET)$(GRAY)%-8s$(RESET) %s\n" "" "清理缓存与构建产物"
	@printf "  $(BOLD)$(YELLOW)make db-migrate$(RESET)$(GRAY)%-3s$(RESET) %s\n" "" "执行数据库迁移 (alembic upgrade head)"
	@printf "  $(BOLD)$(YELLOW)make db-reset$(RESET)$(GRAY)%-5s$(RESET) %s\n" "" "重置数据库 (删除并重新初始化)"
	@printf "  $(BOLD)$(YELLOW)make db-seed$(RESET)$(GRAY)%-6s$(RESET) %s\n" "" "填充数据库种子数据"
	@printf "  $(BOLD)$(YELLOW)make ci$(RESET)$(GRAY)%-10s$(RESET) %s\n" "" "按顺序执行 lint + test (CI 流程)"
	@echo ""
	@echo "$(BOLD)$(MAGENTA)提示:$(RESET) Windows 用户请使用 $(CYAN)./scripts/dev.ps1 <command>$(RESET) 获得等价体验"
	@echo ""

# =============================================================================
# install — 安装后端与前端依赖
# =============================================================================
install:
	@echo "$(BOLD)$(BLUE)[1/2]$(RESET) 安装后端 Python 依赖..."
	@$(PIP_UNIX) install -r $(BACKEND_DIR)/requirements.txt
	@echo "$(GREEN)✔ 后端依赖安装完成$(RESET)"
	@echo "$(BOLD)$(BLUE)[2/2]$(RESET) 安装前端 Node 依赖..."
	@cd $(FRONTEND_DIR) && $(NPM) install
	@echo "$(GREEN)✔ 前端依赖安装完成$(RESET)"

# =============================================================================
# dev — 并行启动后端 + 前端开发服务器
# =============================================================================
dev:
	@echo "$(BOLD)$(MAGENTA)启动开发环境 (后端 + 前端)...$(RESET)"
	@cd $(BACKEND_DIR) && $(VENV_BIN)/uvicorn run:app --reload --host 0.0.0.0 --port 8000 & \
	cd $(FRONTEND_DIR) && $(NPM) run dev

# =============================================================================
# test — 运行后端 pytest 与前端 vitest 测试
# =============================================================================
test:
	@echo "$(BOLD)$(BLUE)[1/2]$(RESET) 执行后端 pytest 测试..."
	@cd $(BACKEND_DIR) && $(PYTEST_UNIX) --cov=app --cov-report=term-missing --cov-report=html
	@echo "$(GREEN)✔ 后端测试完成$(RESET)"
	@echo "$(BOLD)$(BLUE)[2/2]$(RESET) 执行前端 vitest 测试..."
	@cd $(FRONTEND_DIR) && $(NPM) test
	@echo "$(GREEN)✔ 前端测试完成$(RESET)"

# =============================================================================
# lint — ruff + mypy + eslint
# =============================================================================
lint:
	@echo "$(BOLD)$(BLUE)[1/3]$(RESET) ruff 代码风格检查..."
	@cd $(BACKEND_DIR) && $(RUFF_UNIX) check .
	@echo "$(BOLD)$(BLUE)[2/3]$(RESET) mypy 静态类型检查..."
	@cd $(BACKEND_DIR) && $(MYPY_UNIX) app
	@echo "$(BOLD)$(BLUE)[3/3]$(RESET) eslint 前端代码检查..."
	@cd $(FRONTEND_DIR) && $(NPM) run lint
	@echo "$(GREEN)✔ 全部代码检查通过$(RESET)"

# =============================================================================
# format — ruff format + prettier
# =============================================================================
format:
	@echo "$(BOLD)$(BLUE)[1/2]$(RESET) ruff 格式化 Python 代码..."
	@cd $(BACKEND_DIR) && $(RUFF_UNIX) format .
	@echo "$(BOLD)$(BLUE)[2/2]$(RESET) prettier 格式化前端代码..."
	@cd $(FRONTEND_DIR) && $(NPM) run format
	@echo "$(GREEN)✔ 代码格式化完成$(RESET)"

# =============================================================================
# build — 生成依赖锁文件 + 前端生产构建
# =============================================================================
build:
	@echo "$(BOLD)$(BLUE)[1/2]$(RESET) 生成后端依赖锁文件..."
	@cd $(BACKEND_DIR) && $(PIP_UNIX) freeze > requirements.lock
	@echo "$(GREEN)✔ requirements.lock 已生成$(RESET)"
	@echo "$(BOLD)$(BLUE)[2/2]$(RESET) 构建前端生产版本..."
	@cd $(FRONTEND_DIR) && $(NPM) run build
	@echo "$(GREEN)✔ 前端构建完成 (输出至 dist/)$(RESET)"

# =============================================================================
# docker — docker-compose 启动服务
# =============================================================================
docker:
	@echo "$(BOLD)$(MAGENTA)启动 Docker 服务 (含健康检查)...$(RESET)"
	@$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✔ 容器已启动,等待健康检查通过...$(RESET)"
	@$(DOCKER_COMPOSE) ps

# =============================================================================
# docker-down — 优雅停止并移除所有容器/网络/卷
# =============================================================================
docker-down:
	@echo "$(BOLD)$(YELLOW)停止并清理 Docker 资源...$(RESET)"
	@$(DOCKER_COMPOSE) down -v --remove-orphans
	@echo "$(GREEN)✔ Docker 资源已清理$(RESET)"

# =============================================================================
# docker-logs — 实时查看容器日志
#   用法: make docker-logs          # 查看所有服务
#         make docker-logs s=api    # 仅查看 api 服务
# =============================================================================
docker-logs:
ifeq ($(s),)
	@$(DOCKER_COMPOSE) logs -f --tail=200
else
	@$(DOCKER_COMPOSE) logs -f --tail=200 $(s)
endif

# =============================================================================
# clean — 清理缓存与构建产物
# =============================================================================
clean:
	@echo "$(BOLD)$(YELLOW)清理项目缓存与构建产物...$(RESET)"
ifeq ($(OS),Windows_NT)
	@powershell -NoProfile -Command "Get-ChildItem -Path . -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force; Get-ChildItem -Path . -Recurse -Directory -Filter '.pytest_cache' -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force; Get-ChildItem -Path . -Recurse -Directory -Filter '.ruff_cache' -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force; Get-ChildItem -Path . -Recurse -Directory -Filter '.mypy_cache' -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force; if (Test-Path '$(FRONTEND_DIR)/node_modules') { Remove-Item -Recurse -Force '$(FRONTEND_DIR)/node_modules' }; if (Test-Path '$(FRONTEND_DIR)/dist') { Remove-Item -Recurse -Force '$(FRONTEND_DIR)/dist' }"
else
	@find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	@find . -type d -name '.pytest_cache' -prune -exec rm -rf {} +
	@find . -type d -name '.ruff_cache' -prune -exec rm -rf {} +
	@find . -type d -name '.mypy_cache' -prune -exec rm -rf {} +
	@$(RM_DIR) $(FRONTEND_DIR)/node_modules
	@$(RM_DIR) $(FRONTEND_DIR)/dist
endif
	@echo "$(GREEN)✔ 清理完成$(RESET)"

# =============================================================================
# db-migrate — 执行数据库迁移
# =============================================================================
db-migrate:
	@echo "$(BOLD)$(BLUE)执行 Alembic 数据库迁移...$(RESET)"
	@cd $(BACKEND_DIR) && $(ALEMBIC_UNIX) upgrade head
	@echo "$(GREEN)✔ 数据库迁移完成$(RESET)"

# =============================================================================
# db-reset — 重置数据库
# =============================================================================
db-reset:
	@echo "$(BOLD)$(RED)!! 警告: 将删除并重新初始化数据库 !!$(RESET)"
	@cd $(BACKEND_DIR) && $(ALEMBIC_UNIX) downgrade base
	@cd $(BACKEND_DIR) && $(ALEMBIC_UNIX) upgrade head
	@echo "$(GREEN)✔ 数据库重置完成$(RESET)"

# =============================================================================
# db-seed — 填充种子数据
# =============================================================================
db-seed:
	@echo "$(BOLD)$(BLUE)填充数据库种子数据...$(RESET)"
	@cd $(BACKEND_DIR) && $(PYTHON) seed_data.py
	@echo "$(GREEN)✔ 种子数据已写入$(RESET)"

# =============================================================================
# ci — CI 流程: lint + test
# =============================================================================
ci: lint test
	@echo "$(BOLD)$(GREEN)✔ CI 检查全部通过$(RESET)"
