#requires -version 3
<#
.SYNOPSIS
    一键环境配置脚本 - 自动化配置项目运行环境

.DESCRIPTION
    本脚本自动完成以下环境配置任务:
    1. 操作系统检测 - 识别当前运行环境的操作系统类型及版本
    2. Python环境检查 - 验证Python 3.8及以上版本是否已安装
    3. 后端依赖管理 - 自动安装requirements.txt中的依赖包
    4. 前端依赖管理 - 检测并使用npm/yarn安装前端依赖
    5. 环境变量配置 - 创建.env配置文件
    6. SQLite数据库初始化 - 创建数据库文件并建立初始结构
    7. 数据库迁移 - 执行alembic迁移脚本
    8. JWT密钥生成 - 生成安全的随机JWT密钥
    9. Ollama检查与提示 - 检测Ollama安装状态并提供安装指南

.NOTES
    作者: AI Assistant
    版本: 1.0.0
    最后更新: 2026-05-26
#>

# ============================================================================
# 全局配置
# ============================================================================
$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'

# 颜色定义
$ColorSuccess = 'Green'
$ColorInfo = 'Cyan'
$ColorWarning = 'Yellow'
$ColorError = 'Red'
$ColorHeader = 'Magenta'

# 状态文件路径(用于断点续执行)
$StateFile = Join-Path $PSScriptRoot '.setup_state.json'

# ============================================================================
# 辅助函数
# ============================================================================

function Write-StepHeader {
    param([string]$Message, [int]$StepNumber)
    Write-Host "`n$('=' * 60)" -ForegroundColor $ColorHeader
    Write-Host "步骤 $StepNumber`: $Message" -ForegroundColor $ColorHeader
    Write-Host "$('=' * 60)" -ForegroundColor $ColorHeader
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $ColorSuccess
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO]    $Message" -ForegroundColor $ColorInfo
}

function Write-WarningMsg {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $ColorWarning
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-Host "[ERROR]   $Message" -ForegroundColor $ColorError
}

# 保存执行状态
function Save-State {
    param([string]$StepName, [string]$Status)
    
    $state = @{}
    if (Test-Path $StateFile) {
        try {
            $state = Get-Content $StateFile -Raw | ConvertFrom-Json -AsHashtable
        } catch {
            $state = @{}
        }
    }
    
    $state[$StepName] = @{
        Status     = $Status
        Timestamp  = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    }
    
    $state | ConvertTo-Json | Set-Content $StateFile -Encoding UTF8
}

# 加载执行状态
function Load-State {
    if (Test-Path $StateFile) {
        try {
            return Get-Content $StateFile -Raw | ConvertFrom-Json -AsHashtable
        } catch {
            return @{}
        }
    }
    return @{}
}

# 检查是否需要执行某步骤
function Should-RunStep {
    param([string]$StepName, [switch]$Force)
    
    if ($Force.IsPresent) {
        return $true
    }
    
    $state = Load-State
    if ($state.ContainsKey($StepName) -and $state[$StepName].Status -eq 'completed') {
        Write-Info "步骤 '$StepName' 已完成,跳过(使用 -Force 重新执行)"
        return $false
    }
    return $true
}

# ============================================================================
# 步骤 1: 操作系统检测
# ============================================================================
function Invoke-DetectOS {
    param([switch]$Force)
    if (-not (Should-RunStep 'DetectOS' -Force:$Force)) { return $true }
    
    Write-StepHeader '操作系统检测' 1
    
    try {
        $osInfo = @{
            Type    = ''
            Name    = ''
            Version = ''
            Arch    = ''
        }
        
        # Windows 检测
        if ($IsWindows -or $PSVersionTable.OS -match 'Windows') {
            $osInfo.Type = 'Windows'
            $osInfo.Name = (Get-CimInstance Win32_OperatingSystem).Caption
            $osInfo.Version = (Get-CimInstance Win32_OperatingSystem).Version
            $osInfo.Arch = $ENV:PROCESSOR_ARCHITECTURE
        }
        # macOS 检测
        elseif ($IsMacOS) {
            $osInfo.Type = 'macOS'
            $osInfo.Name = 'macOS'
            $osInfo.Version = sw_vers -productVersion
            $osInfo.Arch = uname -m
        }
        # Linux 检测
        elseif ($IsLinux) {
            $osInfo.Type = 'Linux'
            if (Test-Path /etc/os-release) {
                $osInfo.Name = (Get-Content /etc/os-release | Select-String 'PRETTY_NAME' | ForEach-Object { $_.ToString().Split('=')[1].Trim('"') })
            } else {
                $osInfo.Name = uname -o
            }
            $osInfo.Version = uname -r
            $osInfo.Arch = uname -m
        }
        else {
            throw '无法识别的操作系统类型'
        }
        
        Write-Info "操作系统类型: $($osInfo.Type)"
        Write-Info "操作系统名称: $($osInfo.Name)"
        Write-Info "操作系统版本: $($osInfo.Version)"
        Write-Info "系统架构:     $($osInfo.Arch)"
        
        Save-State 'DetectOS' 'completed'
        Write-Success '操作系统检测完成'
        return $true
    }
    catch {
        Write-ErrorMsg "操作系统检测失败: $_"
        Write-Info '恢复建议: 请手动确认操作系统信息并重试'
        Save-State 'DetectOS' 'failed'
        return $false
    }
}

# ============================================================================
# 步骤 2: Python环境检查
# ============================================================================
function Invoke-CheckPython {
    param([switch]$Force)
    if (-not (Should-RunStep 'CheckPython' -Force:$Force)) { return $true }
    
    Write-StepHeader 'Python环境检查' 2
    
    try {
        # 检查Python是否已安装
        $pythonCmd = $null
        foreach ($cmd in @('python', 'python3', 'py')) {
            if (Get-Command $cmd -ErrorAction SilentlyContinue) {
                $pythonCmd = $cmd
                break
            }
        }
        
        if (-not $pythonCmd) {
            Write-WarningMsg 'Python未安装!'
            Write-Info '请按照以下步骤安装Python:'
            Write-Info ''
            Write-Info 'Windows:'
            Write-Info '  1. 访问 https://www.python.org/downloads/'
            Write-Info '  2. 下载Python 3.8或更高版本'
            Write-Info '  3. 运行安装程序,务必勾选 "Add Python to PATH"'
            Write-Info '  4. 完成安装后重新运行此脚本'
            Write-Info ''
            Write-Info 'macOS:'
            Write-Info '  1. 使用Homebrew: brew install python@3.11'
            Write-Info '  2. 或从官网下载安装: https://www.python.org/downloads/'
            Write-Info ''
            Write-Info 'Linux (Ubuntu/Debian):'
            Write-Info '  1. sudo apt update'
            Write-Info '  2. sudo apt install python3 python3-pip python3-venv'
            Write-Info ''
            Write-Info 'Linux (CentOS/RHEL):'
            Write-Info '  1. sudo dnf install python3 python3-pip'
            
            Save-State 'CheckPython' 'failed'
            return $false
        }
        
        # 获取Python版本
        $versionOutput = & $pythonCmd --version 2>&1
        $versionMatch = [regex]::Match($versionOutput, '(\d+)\.(\d+)\.(\d+)')
        
        if ($versionMatch.Success) {
            $major = [int]$versionMatch.Groups[1].Value
            $minor = [int]$versionMatch.Groups[2].Value
            $patch = [int]$versionMatch.Groups[3].Value
            
            Write-Info "检测到Python版本: $major.$minor.$patch"
            
            if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 8)) {
                Write-WarningMsg "Python版本过低 (当前: $major.$minor.$patch, 要求: >= 3.8)"
                Write-Info '请升级Python至3.8或更高版本'
                Save-State 'CheckPython' 'failed'
                return $false
            }
            
            Write-Success "Python版本满足要求 (>= 3.8)"
            $script:PythonCommand = $pythonCmd
        }
        else {
            throw "无法解析Python版本信息: $versionOutput"
        }
        
        # 检查pip
        $pipCmd = $null
        foreach ($cmd in @('pip', 'pip3')) {
            if (Get-Command $cmd -ErrorAction SilentlyContinue) {
                $pipCmd = $cmd
                break
            }
        }
        
        if (-not $pipCmd) {
            Write-WarningMsg 'pip未安装,尝试安装...'
            & $pythonCmd -m ensurepip --default-pip 2>&1 | Out-Null
            if (Get-Command pip -ErrorAction SilentlyContinue) {
                $pipCmd = 'pip'
                Write-Success 'pip安装成功'
            }
            else {
                Write-WarningMsg 'pip安装失败,请手动安装'
            }
        }
        else {
            Write-Info "检测到包管理器: $pipCmd"
        }
        
        $script:PipCommand = $pipCmd
        
        Save-State 'CheckPython' 'completed'
        Write-Success 'Python环境检查完成'
        return $true
    }
    catch {
        Write-ErrorMsg "Python环境检查失败: $_"
        Write-Info '恢复建议: 检查Python是否正确安装并添加到PATH环境变量'
        Save-State 'CheckPython' 'failed'
        return $false
    }
}

# ============================================================================
# 步骤 3: 后端依赖管理
# ============================================================================
function Invoke-InstallBackendDeps {
    param([switch]$Force)
    if (-not (Should-RunStep 'InstallBackendDeps' -Force:$Force)) { return $true }
    
    Write-StepHeader '后端依赖管理' 3
    
    try {
        $requirementsFile = Join-Path $PSScriptRoot 'backend\requirements.txt'
        
        if (-not (Test-Path $requirementsFile)) {
            Write-WarningMsg '未找到 requirements.txt 文件,跳过后端依赖安装'
            Save-State 'InstallBackendDeps' 'skipped'
            return $true
        }
        
        Write-Info "Requirements文件: $requirementsFile"
        Write-Info '正在安装Python依赖包...'
        
        # 优先使用虚拟环境
        $venvPath = Join-Path $PSScriptRoot '.venv'
        $venvPython = Join-Path $venvPath 'Scripts\python.exe'
        $venvPip = Join-Path $venvPath 'Scripts\pip.exe'
        
        if (Test-Path $venvPython) {
            Write-Info '使用现有虚拟环境'
            $pipToUse = $venvPip
        }
        else {
            Write-Info '创建Python虚拟环境...'
            & $script:PythonCommand -m venv $venvPath
            $pipToUse = $venvPip
            Write-Success '虚拟环境创建成功'
        }
        
        # 安装依赖
        $process = Start-Process -FilePath $pipToUse -ArgumentList "install", "-r", $requirementsFile, "--no-cache-dir" -NoNewWindow -Wait -PassThru -RedirectStandardOutput (Join-Path $PSScriptRoot 'pip_install.log')
        
        if ($process.ExitCode -eq 0) {
            Write-Success '后端依赖安装成功'
            Save-State 'InstallBackendDeps' 'completed'
            return $true
        }
        else {
            throw "pip安装失败,退出码: $($process.ExitCode)。详情请查看: $(Join-Path $PSScriptRoot 'pip_install.log')"
        }
    }
    catch {
        Write-ErrorMsg "后端依赖安装失败: $_"
        Write-Info '恢复建议:'
        Write-Info '  1. 检查网络连接是否正常'
        Write-Info '  2. 尝试使用国内镜像源: pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple'
        Write-Info '  3. 检查requirements.txt文件格式是否正确'
        Save-State 'InstallBackendDeps' 'failed'
        return $false
    }
}

# ============================================================================
# 步骤 4: 前端依赖管理
# ============================================================================
function Invoke-InstallFrontendDeps {
    param([switch]$Force)
    if (-not (Should-RunStep 'InstallFrontendDeps' -Force:$Force)) { return $true }
    
    Write-StepHeader '前端依赖管理' 4
    
    try {
        # 查找package.json
        $packageFile = Join-Path $PSScriptRoot 'frontend\package.json'
        $packageFile2 = Join-Path $PSScriptRoot 'package.json'
        
        $found = $false
        if (Test-Path $packageFile) {
            $workDir = Join-Path $PSScriptRoot 'frontend'
            $found = $true
        }
        elseif (Test-Path $packageFile2) {
            $workDir = $PSScriptRoot
            $found = $true
        }
        
        if (-not $found) {
            Write-Info '未找到package.json文件,项目可能不包含前端部分,跳过前端依赖安装'
            Save-State 'InstallFrontendDeps' 'skipped'
            return $true
        }
        
        Write-Info "Package文件: $(Join-Path $workDir 'package.json')"
        
        # 检测包管理器
        $packageManager = $null
        $yarnLock = Join-Path $workDir 'yarn.lock'
        $npmLock = Join-Path $workDir 'package-lock.json'
        
        if (Test-Path $yarnLock) {
            $packageManager = 'yarn'
        }
        elseif (Test-Path $npmLock) {
            $packageManager = 'npm'
        }
        else {
            # 默认检测可用的包管理器
            if (Get-Command yarn -ErrorAction SilentlyContinue) {
                $packageManager = 'yarn'
            }
            elseif (Get-Command npm -ErrorAction SilentlyContinue) {
                $packageManager = 'npm'
            }
        }
        
        if (-not $packageManager) {
            Write-WarningMsg '未检测到npm或yarn包管理器'
            Write-Info '请安装Node.js(包含npm)或yarn:'
            Write-Info '  Windows: 访问 https://nodejs.org/ 下载安装'
            Write-Info '  macOS:   brew install node  或  brew install yarn'
            Write-Info '  Linux:   sudo apt install nodejs npm'
            Save-State 'InstallFrontendDeps' 'failed'
            return $false
        }
        
        Write-Info "使用包管理器: $packageManager"
        Write-Info '正在安装前端依赖...'
        
        Push-Location $workDir
        try {
            if ($packageManager -eq 'yarn') {
                & yarn install
            }
            else {
                & npm install
            }
            
            if ($LASTEXITCODE -eq 0) {
                Write-Success '前端依赖安装成功'
                Save-State 'InstallFrontendDeps' 'completed'
                return $true
            }
            else {
                throw "$packageManager 安装失败,退出码: $LASTEXITCODE"
            }
        }
        finally {
            Pop-Location
        }
    }
    catch {
        Write-ErrorMsg "前端依赖安装失败: $_"
        Write-Info '恢复建议:'
        Write-Info '  1. 检查Node.js是否正确安装: node --version'
        Write-Info '  2. 检查网络连接是否正常'
        Write-Info '  3. 尝试清除缓存后重新安装'
        Save-State 'InstallFrontendDeps' 'failed'
        return $false
    }
}

# ============================================================================
# 步骤 5: 环境变量配置
# ============================================================================
function Invoke-ConfigureEnv {
    param([switch]$Force)
    if (-not (Should-RunStep 'ConfigureEnv' -Force:$Force)) { return $true }
    
    Write-StepHeader '环境变量配置' 5
    
    try {
        $envFile = Join-Path $PSScriptRoot 'backend\.env'
        $envExampleFile = Join-Path $PSScriptRoot 'backend\.env.example'
        
        if (Test-Path $envFile) {
            Write-Info '.env文件已存在,如需重新生成请先删除现有文件'
            Write-Success '环境变量配置文件已存在'
            Save-State 'ConfigureEnv' 'completed'
            return $true
        }
        
        if (Test-Path $envExampleFile) {
            Write-Info '从.env.example复制配置模板...'
            Copy-Item $envExampleFile $envFile
            Write-Success '已基于.env.example创建.env文件'
        }
        else {
            Write-Info '未找到.env.example,创建默认.env文件...'
            
            # 创建默认.env文件
            $defaultEnvContent = @"
# 服务器配置
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG=true
APP_ENV=development

# 数据库配置
DATABASE_URL=sqlite:///./app.db

# JWT配置(稍后自动生成)
JWT_SECRET_KEY=
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# 默认管理员账号
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=admin123

# CORS配置
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOW_HEADERS=Authorization,Content-Type,Accept,X-Requested-With

# Ollama配置
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:7b

# 日志配置
LOG_LEVEL=DEBUG

# 推理服务器配置
INFERENCE_HOST=0.0.0.0
INFERENCE_PORT=8001
"@
            Set-Content -Path $envFile -Value $defaultEnvContent -Encoding UTF8
            Write-Success '已创建默认.env文件'
        }
        
        Write-Info "配置文件已创建: $envFile"
        Write-WarningMsg '请检查.env文件中的配置是否符合您的环境要求'
        
        Save-State 'ConfigureEnv' 'completed'
        Write-Success '环境变量配置完成'
        return $true
    }
    catch {
        Write-ErrorMsg "环境变量配置失败: $_"
        Write-Info '恢复建议: 手动创建.env文件并填写必要配置'
        Save-State 'ConfigureEnv' 'failed'
        return $false
    }
}

# ============================================================================
# 步骤 6: JWT密钥生成
# ============================================================================
function Invoke-GenerateJWTSecret {
    param([switch]$Force)
    if (-not (Should-RunStep 'GenerateJWTSecret' -Force:$Force)) { return $true }
    
    Write-StepHeader 'JWT密钥生成' 6
    
    try {
        $envFile = Join-Path $PSScriptRoot 'backend\.env'
        
        if (-not (Test-Path $envFile)) {
            Write-WarningMsg '.env文件不存在,JWT密钥将保存在临时配置中'
            $envFile = $null
        }
        
        # 生成安全的随机密钥(32字节 = 256位)
        $secureBytes = New-Object byte[] 32
        $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        $rng.GetBytes($secureBytes)
        $jwtSecret = [System.Convert]::ToBase64String($secureBytes)
        
        Write-Info '已生成256位安全随机密钥'
        
        if ($envFile) {
            # 读取.env文件内容
            $envContent = Get-Content $envFile -Raw -Encoding UTF8
            
            # 替换JWT_SECRET_KEY
            if ($envContent -match 'JWT_SECRET_KEY=') {
                $envContent = $envContent -replace 'JWT_SECRET_KEY=.*', "JWT_SECRET_KEY=$jwtSecret"
                Set-Content -Path $envFile -Value $envContent -Encoding UTF8
                Write-Success 'JWT密钥已写入.env文件'
            }
            else {
                # 追加到文件末尾
                Add-Content -Path $envFile -Value "`nJWT_SECRET_KEY=$jwtSecret" -Encoding UTF8
                Write-Success 'JWT密钥已追加到.env文件'
            }
        }
        
        Write-Info 'JWT密钥生成完成'
        Write-WarningMsg '请妥善保管JWT_SECRET_KEY,不要将其提交到版本控制系统'
        
        Save-State 'GenerateJWTSecret' 'completed'
        Write-Success 'JWT密钥生成完成'
        return $true
    }
    catch {
        Write-ErrorMsg "JWT密钥生成失败: $_"
        Write-Info '恢复建议: 手动生成密钥并添加到.env文件的JWT_SECRET_KEY配置项'
        Write-Info '生成命令: python -c "import secrets; print(secrets.token_urlsafe(32))"'
        Save-State 'GenerateJWTSecret' 'failed'
        return $false
    }
}

# ============================================================================
# 步骤 7: SQLite数据库初始化
# ============================================================================
function Invoke-InitDatabase {
    param([switch]$Force)
    if (-not (Should-RunStep 'InitDatabase' -Force:$Force)) { return $true }
    
    Write-StepHeader 'SQLite数据库初始化' 7
    
    try {
        $dbFile = Join-Path $PSScriptRoot 'backend\app.db'
        
        # 检查数据库文件是否存在
        if (Test-Path $dbFile) {
            Write-Info 'SQLite数据库文件已存在'
        }
        else {
            Write-Info '创建新的SQLite数据库文件...'
            # 创建空文件,Alembic迁移会处理结构
            New-Item -Path $dbFile -ItemType File -Force | Out-Null
            Write-Success '数据库文件创建成功'
        }
        
        # 验证数据库可访问性
        $venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
        if (Test-Path $venvPython) {
            $pythonToUse = $venvPython
        }
        else {
            $pythonToUse = $script:PythonCommand
        }
        
        $testScript = @"
import sqlite3
import sys
db_path = sys.argv[1]
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT sqlite_version();')
    version = cursor.fetchone()[0]
    conn.close()
    print(f'SQLite版本: {version}')
    sys.exit(0)
except Exception as e:
    print(f'数据库测试失败: {e}')
    sys.exit(1)
"@
        
        $tempScript = Join-Path $PSScriptRoot 'temp_db_test.py'
        Set-Content -Path $tempScript -Value $testScript -Encoding UTF8
        
        try {
            $result = & $pythonToUse $tempScript $dbFile 2>&1
            Write-Info $result
        }
        finally {
            Remove-Item $tempScript -Force -ErrorAction SilentlyContinue
        }
        
        Save-State 'InitDatabase' 'completed'
        Write-Success 'SQLite数据库初始化完成'
        return $true
    }
    catch {
        Write-ErrorMsg "SQLite数据库初始化失败: $_"
        Write-Info '恢复建议:'
        Write-Info '  1. 检查backend目录是否有写入权限'
        Write-Info '  2. 检查磁盘空间是否充足'
        Write-Info '  3. 手动创建app.db文件: New-Item backend\app.db -ItemType File'
        Save-State 'InitDatabase' 'failed'
        return $false
    }
}

# ============================================================================
# 步骤 8: 数据库迁移
# ============================================================================
function Invoke-RunMigrations {
    param([switch]$Force)
    if (-not (Should-RunStep 'RunMigrations' -Force:$Force)) { return $true }
    
    Write-StepHeader '数据库迁移' 8
    
    try {
        $backendDir = Join-Path $PSScriptRoot 'backend'
        $alembicIni = Join-Path $backendDir 'alembic.ini'
        
        if (-not (Test-Path $alembicIni)) {
            Write-WarningMsg '未找到alembic.ini,项目可能不使用Alembic进行数据库迁移'
            Save-State 'RunMigrations' 'skipped'
            return $true
        }
        
        Write-Info '检测到Alembic配置,执行数据库迁移...'
        
        # 确定Python路径
        $venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
        if (Test-Path $venvPython) {
            $pythonToUse = $venvPython
        }
        else {
            $pythonToUse = $script:PythonCommand
        }
        
        # 检查迁移目录
        $migrationsDir = Join-Path $backendDir 'alembic\versions'
        if (Test-Path $migrationsDir) {
            $migrationFiles = Get-ChildItem $migrationsDir -Filter '*.py' | Where-Object { $_.Name -ne '__init__.py' }
            if ($migrationFiles.Count -eq 0) {
                Write-Info '未发现迁移文件,执行初始迁移...'
                Push-Location $backendDir
                try {
                    & $pythonToUse -m alembic revision --autogenerate -m "initial migration" 2>&1
                    & $pythonToUse -m alembic upgrade head 2>&1
                }
                finally {
                    Pop-Location
                }
            }
            else {
                Write-Info "发现 $($migrationFiles.Count) 个迁移文件,执行升级..."
                Push-Location $backendDir
                try {
                    & $pythonToUse -m alembic upgrade head 2>&1
                }
                finally {
                    Pop-Location
                }
            }
        }
        else {
            Write-Info '迁移目录不存在,尝试初始化Alembic...'
            Push-Location $backendDir
            try {
                & $pythonToUse -m alembic init alembic 2>&1
                & $pythonToUse -m alembic revision --autogenerate -m "initial migration" 2>&1
                & $pythonToUse -m alembic upgrade head 2>&1
            }
            finally {
                Pop-Location
            }
        }
        
        Write-Success '数据库迁移执行成功'
        Save-State 'RunMigrations' 'completed'
        return $true
    }
    catch {
        Write-ErrorMsg "数据库迁移失败: $_"
        Write-Info '恢复建议:'
        Write-Info '  1. 检查alembic.ini中的数据库URL配置是否正确'
        Write-Info '  2. 手动执行迁移: cd backend && python -m alembic upgrade head'
        Write-Info '  3. 检查迁移脚本是否有语法错误'
        Save-State 'RunMigrations' 'failed'
        return $false
    }
}

# ============================================================================
# 步骤 9: Ollama检查与提示
# ============================================================================
function Invoke-CheckOllama {
    param([switch]$Force)
    if (-not (Should-RunStep 'CheckOllama' -Force:$Force)) { return $true }
    
    Write-StepHeader 'Ollama检查与提示' 9
    
    try {
        $ollamaInstalled = $false
        
        # 检查Ollama是否已安装
        if (Get-Command ollama -ErrorAction SilentlyContinue) {
            $ollamaInstalled = $true
            $version = & ollama --version 2>&1
            Write-Info "Ollama已安装: $version"
        }
        else {
            Write-WarningMsg 'Ollama未安装'
        }
        
        # 检查Ollama服务是否运行
        $serviceRunning = $false
        if ($ollamaInstalled) {
            try {
                $response = Invoke-WebRequest -Uri 'http://localhost:11434' -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
                if ($response.StatusCode -eq 200) {
                    $serviceRunning = $true
                    Write-Info 'Ollama服务正在运行 (http://localhost:11434)'
                }
            }
            catch {
                Write-WarningMsg 'Ollama服务未启动'
            }
        }
        
        # 如果未安装,提供安装指南
        if (-not $ollamaInstalled) {
            Write-Host "`n" -NoNewline
            Write-Host "╔══════════════════════════════════════════════════════════════════╗" -ForegroundColor $ColorInfo
            Write-Host "║                    Ollama 安装指南                               ║" -ForegroundColor $ColorInfo
            Write-Host "╠══════════════════════════════════════════════════════════════════╣" -ForegroundColor $ColorInfo
            Write-Host "║                                                                  ║" -ForegroundColor $ColorInfo
            Write-Host "║  Windows:                                                        ║" -ForegroundColor $ColorInfo
            Write-Host "║    1. 访问 https://ollama.com/download                             ║" -ForegroundColor $ColorInfo
            Write-Host "║    2. 下载Windows安装程序                                        ║" -ForegroundColor $ColorInfo
            Write-Host "║    3. 运行安装程序完成安装                                       ║" -ForegroundColor $ColorInfo
            Write-Host "║                                                                  ║" -ForegroundColor $ColorInfo
            Write-Host "║  macOS:                                                          ║" -ForegroundColor $ColorInfo
            Write-Host "║    1. 访问 https://ollama.com/download                             ║" -ForegroundColor $ColorInfo
            Write-Host "║    2. 下载macOS版本并安装                                        ║" -ForegroundColor $ColorInfo
            Write-Host "║    或使用Homebrew: brew install ollama                           ║" -ForegroundColor $ColorInfo
            Write-Host "║                                                                  ║" -ForegroundColor $ColorInfo
            Write-Host "║  Linux:                                                          ║" -ForegroundColor $ColorInfo
            Write-Host "║    curl -fsSL https://ollama.com/install.sh | sh                 ║" -ForegroundColor $ColorInfo
            Write-Host "║                                                                  ║" -ForegroundColor $ColorInfo
            Write-Host "║  安装后启动服务:                                                 ║" -ForegroundColor $ColorInfo
            Write-Host "║    ollama serve                                                  ║" -ForegroundColor $ColorInfo
            Write-Host "║                                                                  ║" -ForegroundColor $ColorInfo
            Write-Host "║  下载模型(示例):                                                 ║" -ForegroundColor $ColorInfo
            Write-Host "║    ollama pull deepseek-r1:7b                                    ║" -ForegroundColor $ColorInfo
            Write-Host "║                                                                  ║" -ForegroundColor $ColorInfo
            Write-Host "╚══════════════════════════════════════════════════════════════════╝" -ForegroundColor $ColorInfo
        }
        
        # 服务未运行时的提示
        if ($ollamaInstalled -and -not $serviceRunning) {
            Write-WarningMsg 'Ollama已安装但服务未运行,请执行: ollama serve'
        }
        
        Save-State 'CheckOllama' 'completed'
        Write-Success 'Ollama检查完成'
        return $true
    }
    catch {
        Write-ErrorMsg "Ollama检查失败: $_"
        Save-State 'CheckOllama' 'failed'
        return $false
    }
}

# ============================================================================
# 主函数
# ============================================================================
function Main {
    param(
        [switch]$Force,
        [switch]$Resume,
        [int]$StartFromStep = 0
    )
    
    # 欢迎信息
    Write-Host @"

 ███████╗██╗   ██╗███████╗███╗   ██╗████████╗███████╗██████╗ 
 ██╔════╝╚██╗ ██╔╝██╔════╝████╗  ██║╚══██╔══╝██╔════╝██╔══██╗
 ███████╗ ╚████╔╝ █████╗  ██╔██╗ ██║   ██║   █████╗  ██████╔╝
 ╚════██║  ╚██╔╝  ██╔══╝  ██║╚██╗██║   ██║   ██╔══╝  ██╔══██╗
 ███████║   ██║   ███████╗██║ ╚████║   ██║   ███████╗██║  ██║
 ╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
                        环境配置脚本 v1.0.0

"@ -ForegroundColor $ColorHeader
    
    Write-Host "工作目录: $PSScriptRoot" -ForegroundColor $ColorInfo
    Write-Host "执行时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor $ColorInfo
    if ($Force.IsPresent) { Write-Host "模式: 强制重新执行所有步骤" -ForegroundColor $ColorWarning }
    elseif ($Resume.IsPresent) { Write-Host "模式: 断点续执行" -ForegroundColor $ColorInfo }
    Write-Host ""
    
    # 步骤列表
    $steps = @(
        @{ Name = 'DetectOS';            Function = { Invoke-DetectOS -Force:$Force }; Description = '操作系统检测' },
        @{ Name = 'CheckPython';         Function = { Invoke-CheckPython -Force:$Force }; Description = 'Python环境检查' },
        @{ Name = 'InstallBackendDeps';  Function = { Invoke-InstallBackendDeps -Force:$Force }; Description = '后端依赖管理' },
        @{ Name = 'InstallFrontendDeps'; Function = { Invoke-InstallFrontendDeps -Force:$Force }; Description = '前端依赖管理' },
        @{ Name = 'ConfigureEnv';        Function = { Invoke-ConfigureEnv -Force:$Force }; Description = '环境变量配置' },
        @{ Name = 'GenerateJWTSecret';   Function = { Invoke-GenerateJWTSecret -Force:$Force }; Description = 'JWT密钥生成' },
        @{ Name = 'InitDatabase';        Function = { Invoke-InitDatabase -Force:$Force }; Description = 'SQLite数据库初始化' },
        @{ Name = 'RunMigrations';       Function = { Invoke-RunMigrations -Force:$Force }; Description = '数据库迁移' },
        @{ Name = 'CheckOllama';         Function = { Invoke-CheckOllama -Force:$Force }; Description = 'Ollama检查与提示' }
    )
    
    $successCount = 0
    $failCount = 0
    $skipCount = 0
    $failedSteps = @()
    
    # 执行所有步骤
    for ($i = 0; $i -lt $steps.Count; $i++) {
        $step = $steps[$i]
        $stepNum = $i + 1
        
        # 检查是否从指定步骤开始
        if ($StartFromStep -gt 0 -and $stepNum -lt $StartFromStep) {
            continue
        }
        
        try {
            $result = & $step.Function
            
            if ($result -eq $true) {
                $successCount++
            }
            else {
                $failCount++
                $failedSteps += $step.Description
            }
        }
        catch {
            Write-ErrorMsg "步骤 '$($step.Description)' 发生未捕获异常: $_"
            $failCount++
            $failedSteps += $step.Description
        }
    }
    
    # 执行摘要
    Write-Host "`n$('=' * 60)" -ForegroundColor $ColorHeader
    Write-Host '                    执行摘要' -ForegroundColor $ColorHeader
    Write-Host "$('=' * 60)" -ForegroundColor $Header
    
    if ($failCount -eq 0) {
        Write-Success '所有步骤执行成功!'
    }
    else {
        Write-WarningMsg "有 $failCount 个步骤执行失败:"
        foreach ($failStep in $failedSteps) {
            Write-WarningMsg "  - $failStep"
        }
        Write-Info ''
        Write-Info '使用以下命令重新执行:'
        Write-Info "  .\setup.ps1 -Force                  # 强制重新执行所有步骤"
        Write-Info "  .\setup.ps1 -Resume                # 仅执行失败的步骤(断点续执行)"
    }
    
    Write-Host "`n成功: $successCount | 失败: $failCount | 跳过: $skipCount" -ForegroundColor $(
        if ($failCount -eq 0) { $ColorSuccess } else { $ColorWarning }
    )
    
    # 清理状态文件(如果全部成功)
    if ($failCount -eq 0 -and -not $Force.IsPresent) {
        if (Test-Path $StateFile) {
            Remove-Item $StateFile -Force
        }
    }
    
    Write-Host "`n"
}

# 脚本入口
Main @args
