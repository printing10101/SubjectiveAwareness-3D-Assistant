# 开发环境初始化脚本
# 用法: .\scripts\setup_dev_env.ps1

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  开发环境初始化脚本" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 检查Python版本
Write-Host "[1/6] 检查Python版本..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($pythonVersion -match "Python 3\.(1[1-9]|[2-9][0-9])") {
    Write-Host "  ✓ Python版本符合要求: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "  ✗ 需要Python 3.11或更高版本" -ForegroundColor Red
    exit 1
}

# 检查Node.js
Write-Host "[2/6] 检查Node.js..." -ForegroundColor Yellow
$nodeVersion = node --version 2>&1
if ($nodeVersion -match "v(1[8-9]|[2-9][0-9])") {
    Write-Host "  ✓ Node.js版本符合要求: $nodeVersion" -ForegroundColor Green
} else {
    Write-Host "  ✗ 需要Node.js 18或更高版本" -ForegroundColor Red
    exit 1
}

# 安装Python依赖
Write-Host "[3/6] 安装Python开发依赖..." -ForegroundColor Yellow
pip install --upgrade pip
pip install pre-commit ruff mypy bandit
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Python开发依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "  ✗ Python依赖安装失败" -ForegroundColor Red
    exit 1
}

# 配置pre-commit
Write-Host "[4/6] 配置pre-commit钩子..." -ForegroundColor Yellow
pre-commit install
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ pre-commit钩子安装完成" -ForegroundColor Green
} else {
    Write-Host "  ✗ pre-commit配置失败" -ForegroundColor Red
    exit 1
}

# 安装前端依赖
Write-Host "[5/6] 安装前端开发依赖..." -ForegroundColor Yellow
Set-Location frontend
npm install -D eslint@^8.56.0 prettier@^3.2.5 eslint-plugin-vue@^9.21.1 eslint-plugin-import@^2.29.1 eslint-plugin-unused-imports@^3.1.0 eslint-config-prettier@^9.1.0 eslint-import-resolver-alias@^1.1.2
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ 前端开发依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "  ✗ 前端依赖安装失败" -ForegroundColor Red
    Set-Location ..
    exit 1
}
Set-Location ..

# 安装commitizen
Write-Host "[6/6] 安装Commitizen..." -ForegroundColor Yellow
pip install commitizen
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Commitizen安装完成" -ForegroundColor Green
} else {
    Write-Host "  ✗ Commitizen安装失败" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  开发环境初始化完成!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "可用命令:" -ForegroundColor Yellow
Write-Host "  pre-commit run --all-files    运行所有代码检查"
Write-Host "  ruff format backend/          格式化Python代码"
Write-Host "  ruff check --fix backend/     检查并修复Python代码"
Write-Host "  cd frontend && npm run lint   检查前端代码"
Write-Host "  cd frontend && npm run format 格式化前端代码"
Write-Host "  cz commit                     使用规范提交信息"
Write-Host ""
