<#
.SYNOPSIS
    帮信罪"主观明知"智能分析系统 — 跨平台开发命令管理脚本 (Windows PowerShell 5.1+ / PowerShell Core)

.DESCRIPTION
    提供与项目根目录 Makefile 完全一致的功能集合,适用于 Windows 平台。
    支持参数自动补全(Register-ArgumentCompleter)、统一错误处理与日志记录。

.PARAMETER Command
    要执行的命令名称 (help / install / dev / test / lint / format / build /
    docker / docker-down / docker-logs / clean / db-migrate / db-reset /
    db-seed / ci)

.PARAMETER Service
    docker-logs 命令的可选参数,用于指定查看哪个服务的日志 (如: api / db / redis)

.EXAMPLE
    .\scripts\dev.ps1 help
    显示所有可用命令

.EXAMPLE
    .\scripts\dev.ps1 install
    安装后端与前端依赖

.EXAMPLE
    .\scripts\dev.ps1 docker-logs -Service api
    查看 api 容器实时日志

.NOTES
    Author : DevOps Team
    Compat : PowerShell 5.1 / PowerShell Core (7.x)
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet(
        'help', 'install', 'dev', 'test', 'lint', 'format', 'build',
        'docker', 'docker-down', 'docker-logs', 'clean',
        'db-migrate', 'db-reset', 'db-seed', 'ci'
    )]
    [string]$Command = 'help',

    [Parameter()]
    [string]$Service
)

# -----------------------------------------------------------------------------
# 路径与可执行命令配置
# -----------------------------------------------------------------------------
$Script:ProjectRoot  = Resolve-Path (Join-Path $PSScriptRoot '..')
$Script:BackendDir   = Join-Path $Script:ProjectRoot 'backend'
$Script:FrontendDir  = Join-Path $Script:ProjectRoot 'frontend'
$Script:VenvBin      = Join-Path $Script:ProjectRoot '.venv\Scripts'
$Script:Python       = Join-Path $Script:VenvBin 'python.exe'
$Script:Pip          = Join-Path $Script:VenvBin 'pip.exe'
$Script:Pytest       = Join-Path $Script:VenvBin 'pytest.exe'
$Script:Ruff         = Join-Path $Script:VenvBin 'ruff.exe'
$Script:Mypy         = Join-Path $Script:VenvBin 'mypy.exe'
$Script:Alembic      = Join-Path $Script:VenvBin 'alembic.exe'
$Script:LogDir       = Join-Path $Script:ProjectRoot 'logs'
$Script:LogFile      = Join-Path $Script:LogDir ("dev-{0:yyyyMMdd}.log" -f (Get-Date))

# -----------------------------------------------------------------------------
# 参数自动补全 (PowerShell 5.1+)
# -----------------------------------------------------------------------------
if ($Host.Version.Major -ge 5) {
    try {
        Register-ArgumentCompleter -Native -CommandName 'dev.ps1' -ScriptBlock {
            param($wordToComplete, $ast, $context)
            $commands = @(
                'help', 'install', 'dev', 'test', 'lint', 'format', 'build',
                'docker', 'docker-down', 'docker-logs', 'clean',
                'db-migrate', 'db-reset', 'db-seed', 'ci'
            )
            $commands | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
            }
        }
    } catch {
        # 某些环境不支持原生补全,静默忽略
    }
}

# -----------------------------------------------------------------------------
# 日志函数
# -----------------------------------------------------------------------------
function Initialize-Logger {
    if (-not (Test-Path $Script:LogDir)) {
        New-Item -ItemType Directory -Path $Script:LogDir -Force | Out-Null
    }
}

function Write-Log {
    param(
        [Parameter(Mandatory)] [string]$Message,
        [ValidateSet('INFO', 'WARN', 'ERROR', 'SUCCESS', 'STEP')] [string]$Level = 'INFO'
    )
    $timestamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    $entry     = "[$timestamp] [$Level] $Message"
    Add-Content -Path $Script:LogFile -Value $entry -Encoding UTF8
}

function Write-Step {
    param([int]$Current, [int]$Total, [string]$Message)
    $color = 'Cyan'
    Write-Host "[$Current/$Total] " -Foreground $color -NoNewline
    Write-Host $Message
    Write-Log -Message "[$Current/$Total] $Message" -Level STEP
}

function Write-Success { param([string]$Message) Write-Host "✔ $Message" -ForegroundColor Green; Write-Log -Message $Message -Level SUCCESS }
function Write-Warn2   { param([string]$Message) Write-Host "!! $Message" -ForegroundColor Yellow; Write-Log -Message $Message -Level WARN }
function Write-Err2    { param([string]$Message) Write-Host "✘ $Message" -ForegroundColor Red; Write-Log -Message $Message -Level ERROR }

function Invoke-Step {
    param(
        [Parameter(Mandatory)] [string]$Executable,
        [Parameter(Mandatory)] [string[]]$Arguments,
        [Parameter(Mandatory)] [string]$WorkingDirectory,
        [string]$Description
    )
    Write-Log -Message "RUN: $Executable $($Arguments -join ' ') (cwd=$WorkingDirectory)"
    Push-Location $WorkingDirectory
    try {
        $output = & $Executable @Arguments 2>&1
        $exit   = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($exit -ne 0) {
        Write-Err2 "$Description 失败 (退出码: $exit)"
        Write-Log -Message "FAIL: $Description exit=$exit" -Level ERROR
        exit $exit
    }
    Write-Log -Message "OK: $Description" -Level SUCCESS
}

# -----------------------------------------------------------------------------
# 命令实现
# -----------------------------------------------------------------------------

# ---- help -------------------------------------------------------------------
function Invoke-Help {
    $border = '=' * 65
    Write-Host ''
    Write-Host $border -ForegroundColor Cyan
    Write-Host '  帮信罪主观明知智能分析系统 — 开发命令速查表 (PowerShell)' -ForegroundColor Cyan
    Write-Host $border -ForegroundColor Cyan
    Write-Host ''
    Write-Host ('  {0,-18} {1}' -f '命令', '功能说明') -ForegroundColor Green
    Write-Host ('  {0,-18} {1}' -f '----------------', '----------------------------------------') -ForegroundColor Gray
    $rows = @(
        @('help',         '显示本帮助信息'),
        @('install',      '安装后端与前端依赖'),
        @('dev',          '并行启动后端 + 前端开发服务'),
        @('test',         '执行后端 pytest + 前端 npm test'),
        @('lint',         '执行 ruff/mypy/eslint 检查'),
        @('format',       'ruff format + prettier 格式化'),
        @('build',        '生成依赖锁文件 + 前端生产构建'),
        @('docker',       '使用 docker-compose 启动所有服务'),
        @('docker-down',  '停止并移除所有 Docker 资源'),
        @('docker-logs',  '查看服务容器日志 (用 -Service 指定服务)'),
        @('clean',        '清理缓存与构建产物'),
        @('db-migrate',   '执行数据库迁移 (alembic upgrade head)'),
        @('db-reset',     '重置数据库 (删除并重新初始化)'),
        @('db-seed',      '填充数据库种子数据'),
        @('ci',           '按顺序执行 lint + test (CI 流程)')
    )
    foreach ($r in $rows) {
        Write-Host ('  {0,-18} {1}' -f $r[0], $r[1]) -ForegroundColor Yellow
    }
    Write-Host ''
    Write-Host '提示: 类 Unix 用户请使用 make <command> 获得等价体验' -ForegroundColor Magenta
    Write-Host ''
}

# ---- install ----------------------------------------------------------------
function Invoke-Install {
    Write-Step -Current 1 -Total 2 -Message '安装后端 Python 依赖...'
    Invoke-Step -Executable $Script:Pip -Arguments @('install', '-r', 'requirements.txt') `
                -WorkingDirectory $Script:BackendDir -Description '后端依赖安装'
    Write-Success '后端依赖安装完成'

    Write-Step -Current 2 -Total 2 -Message '安装前端 Node 依赖...'
    Invoke-Step -Executable 'npm' -Arguments @('install') `
                -WorkingDirectory $Script:FrontendDir -Description '前端依赖安装'
    Write-Success '前端依赖安装完成'
}

# ---- dev --------------------------------------------------------------------
function Invoke-Dev {
    Write-Host '启动开发环境 (后端 + 前端)...' -ForegroundColor Magenta
    Push-Location $Script:BackendDir
    $backendJob = Start-Job -ScriptBlock {
        Set-Location $using:Script:BackendDir
        & $using:Script:VenvBin\uvicorn.exe run:app --reload --host 0.0.0.0 --port 8000
    }
    Pop-Location
    Write-Host "后端 Job ID: $($backendJob.Id)" -ForegroundColor DarkGray

    Push-Location $Script:FrontendDir
    $frontendJob = Start-Job -ScriptBlock {
        Set-Location $using:Script:FrontendDir
        & npm run dev
    }
    Pop-Location
    Write-Host "前端 Job ID: $($frontendJob.Id)" -ForegroundColor DarkGray

    Write-Host '按 Ctrl+C 停止服务...' -ForegroundColor Yellow
    try {
        while ($true) {
            Start-Sleep -Seconds 1
            if ((Get-Process -Id $PID -ErrorAction SilentlyContinue) -eq $null) { break }
        }
    } finally {
        Stop-Job $backendJob  -ErrorAction SilentlyContinue
        Stop-Job $frontendJob -ErrorAction SilentlyContinue
        Remove-Job $backendJob  -Force -ErrorAction SilentlyContinue
        Remove-Job $frontendJob -Force -ErrorAction SilentlyContinue
    }
}

# ---- test -------------------------------------------------------------------
function Invoke-Test {
    Write-Step -Current 1 -Total 2 -Message '执行后端 pytest 测试...'
    Invoke-Step -Executable $Script:Pytest -Arguments @('--cov=app', '--cov-report=term-missing', '--cov-report=html') `
                -WorkingDirectory $Script:BackendDir -Description '后端 pytest'
    Write-Success '后端测试完成'

    Write-Step -Current 2 -Total 2 -Message '执行前端 vitest 测试...'
    Invoke-Step -Executable 'npm' -Arguments @('test') `
                -WorkingDirectory $Script:FrontendDir -Description '前端 vitest'
    Write-Success '前端测试完成'
}

# ---- lint -------------------------------------------------------------------
function Invoke-Lint {
    Write-Step -Current 1 -Total 3 -Message 'ruff 代码风格检查...'
    Invoke-Step -Executable $Script:Ruff -Arguments @('check', '.') `
                -WorkingDirectory $Script:BackendDir -Description 'ruff check'
    Write-Success 'ruff 检查通过'

    Write-Step -Current 2 -Total 3 -Message 'mypy 静态类型检查...'
    Invoke-Step -Executable $Script:Mypy -Arguments @('app') `
                -WorkingDirectory $Script:BackendDir -Description 'mypy'
    Write-Success 'mypy 检查通过'

    Write-Step -Current 3 -Total 3 -Message 'eslint 前端代码检查...'
    Invoke-Step -Executable 'npm' -Arguments @('run', 'lint') `
                -WorkingDirectory $Script:FrontendDir -Description 'eslint'
    Write-Success '全部代码检查通过'
}

# ---- format -----------------------------------------------------------------
function Invoke-Format {
    Write-Step -Current 1 -Total 2 -Message 'ruff 格式化 Python 代码...'
    Invoke-Step -Executable $Script:Ruff -Arguments @('format', '.') `
                -WorkingDirectory $Script:BackendDir -Description 'ruff format'
    Write-Success 'ruff 格式化完成'

    Write-Step -Current 2 -Total 2 -Message 'prettier 格式化前端代码...'
    Invoke-Step -Executable 'npm' -Arguments @('run', 'format') `
                -WorkingDirectory $Script:FrontendDir -Description 'prettier'
    Write-Success '代码格式化完成'
}

# ---- build ------------------------------------------------------------------
function Invoke-Build {
    Write-Step -Current 1 -Total 2 -Message '生成后端依赖锁文件...'
    $lockFile = Join-Path $Script:BackendDir 'requirements.lock'
    & $Script:Pip freeze | Out-File -FilePath $lockFile -Encoding UTF8
    Write-Success "requirements.lock 已生成 ($lockFile)"

    Write-Step -Current 2 -Total 2 -Message '构建前端生产版本...'
    Invoke-Step -Executable 'npm' -Arguments @('run', 'build') `
                -WorkingDirectory $Script:FrontendDir -Description '前端 npm run build'
    Write-Success '前端构建完成 (输出至 dist/)'
}

# ---- docker -----------------------------------------------------------------
function Invoke-DockerUp {
    Write-Host '启动 Docker 服务 (含健康检查)...' -ForegroundColor Magenta
    & docker compose up -d
    if ($LASTEXITCODE -ne 0) { Write-Err2 'docker compose up 失败'; exit $LASTEXITCODE }
    Write-Success '容器已启动,等待健康检查通过...'
    & docker compose ps
}

function Invoke-DockerDown {
    Write-Warn2 '停止并清理 Docker 资源...'
    & docker compose down -v --remove-orphans
    if ($LASTEXITCODE -ne 0) { Write-Err2 'docker compose down 失败'; exit $LASTEXITCODE }
    Write-Success 'Docker 资源已清理'
}

function Invoke-DockerLogs {
    if ([string]::IsNullOrWhiteSpace($Service)) {
        & docker compose logs -f --tail=200
    } else {
        & docker compose logs -f --tail=200 $Service
    }
    if ($LASTEXITCODE -ne 0) { Write-Err2 'docker compose logs 失败'; exit $LASTEXITCODE }
}

# ---- clean ------------------------------------------------------------------
function Invoke-Clean {
    Write-Warn2 '清理项目缓存与构建产物...'
    $targets = @('__pycache__', '.pytest_cache', '.ruff_cache', '.mypy_cache', 'node_modules', 'dist', '.coverage', 'htmlcov')
    foreach ($name in $targets) {
        Get-ChildItem -Path $Script:ProjectRoot -Recurse -Force -ErrorAction SilentlyContinue |
            Where-Object {
                if ($_.PSIsContainer) { $_.Name -ieq $name } else { $false }
            } | ForEach-Object {
                try {
                    Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction Stop
                    Write-Host "  已删除: $($_.FullName)" -ForegroundColor DarkGray
                } catch {
                    Write-Warn2 "无法删除: $($_.FullName) ($($_.Exception.Message))"
                }
            }
    }
    Write-Success '清理完成'
}

# ---- db ---------------------------------------------------------------------
function Invoke-DbMigrate {
    Write-Step -Current 1 -Total 1 -Message '执行 Alembic 数据库迁移...'
    Invoke-Step -Executable $Script:Alembic -Arguments @('upgrade', 'head') `
                -WorkingDirectory $Script:BackendDir -Description 'alembic upgrade head'
    Write-Success '数据库迁移完成'
}

function Invoke-DbReset {
    Write-Warn2 '!! 警告: 将删除并重新初始化数据库 !!'
    Invoke-Step -Executable $Script:Alembic -Arguments @('downgrade', 'base') `
                -WorkingDirectory $Script:BackendDir -Description 'alembic downgrade base'
    Invoke-Step -Executable $Script:Alembic -Arguments @('upgrade', 'head') `
                -WorkingDirectory $Script:BackendDir -Description 'alembic upgrade head'
    Write-Success '数据库重置完成'
}

function Invoke-DbSeed {
    Write-Step -Current 1 -Total 1 -Message '填充数据库种子数据...'
    Invoke-Step -Executable $Script:Python -Arguments @('seed_data.py') `
                -WorkingDirectory $Script:BackendDir -Description 'seed_data.py'
    Write-Success '种子数据已写入'
}

# ---- ci ---------------------------------------------------------------------
function Invoke-CI {
    Write-Host '开始 CI 流程 (lint + test)...' -ForegroundColor Magenta
    Invoke-Lint
    Invoke-Test
    Write-Success 'CI 检查全部通过'
}

# -----------------------------------------------------------------------------
# 命令分发
# -----------------------------------------------------------------------------
Initialize-Logger
Write-Log -Message "EXEC: dev.ps1 $Command" -Level INFO

try {
    switch ($Command) {
        'help'         { Invoke-Help }
        'install'      { Invoke-Install }
        'dev'          { Invoke-Dev }
        'test'         { Invoke-Test }
        'lint'         { Invoke-Lint }
        'format'       { Invoke-Format }
        'build'        { Invoke-Build }
        'docker'       { Invoke-DockerUp }
        'docker-down'  { Invoke-DockerDown }
        'docker-logs'  { Invoke-DockerLogs }
        'clean'        { Invoke-Clean }
        'db-migrate'   { Invoke-DbMigrate }
        'db-reset'     { Invoke-DbReset }
        'db-seed'      { Invoke-DbSeed }
        'ci'           { Invoke-CI }
        default {
            Write-Err2 "未知命令: $Command"
            Invoke-Help
            exit 1
        }
    }
} catch {
    Write-Err2 "脚本执行异常: $($_.Exception.Message)"
    Write-Log -Message "EXCEPTION: $($_.Exception.Message)" -Level ERROR
    exit 1
}

Write-Log -Message "DONE: $Command" -Level SUCCESS
