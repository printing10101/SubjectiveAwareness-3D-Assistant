@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

:: ============================================================
:: Cross-Platform System Startup Script - Windows Version
:: Services: Ollama -> FastAPI Backend -> Vite Frontend
:: ============================================================

:: Configuration
set "OLLAMA_URL=http://localhost:11434"
set "BACKEND_URL=http://localhost:8000"
set "FRONTEND_URL=http://localhost:3000"
set "LOG_DIR=%~dp0logs"
set "TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TIMESTAMP=%TIMESTAMP: =0%"

:: Create logs directory
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: Color output helper
call :print_header "System Startup Script - Windows"

:: ============================================================
:: 1. Detect Environment
:: ============================================================
call :print_info "Detecting environment..."

where ollama >nul 2>&1
if %errorlevel% neq 0 (
    call :print_warn "ollama not found in PATH, checking default install location..."
    if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
        set "PATH=%LOCALAPPDATA%\Programs\Ollama;%PATH%"
        call :print_ok "Found ollama at default location"
    ) else (
        call :print_error "ollama is not installed. Please install from https://ollama.com"
        goto :end
    )
) else (
    call :print_ok "ollama found in PATH"
)

where python >nul 2>&1
if %errorlevel% neq 0 (
    call :print_error "Python is not installed or not in PATH"
    goto :end
)

where node >nul 2>&1
if %errorlevel% neq 0 (
    call :print_error "Node.js is not installed or not in PATH"
    goto :end
)

:: ============================================================
:: 2. Health Check Mode
:: ============================================================
if /i "%~1"=="--health" goto :health_check

:: ============================================================
:: 3. Start Ollama Service
:: ============================================================
call :print_header "Starting Ollama Service"

:: Check if Ollama is already running
call :check_port 11434
if %errorlevel% equ 0 (
    call :print_ok "Ollama is already running on port 11434"
) else (
    call :print_info "Starting Ollama service..."
    start /b ollama serve >"%LOG_DIR%\ollama_%TIMESTAMP%.log" 2>&1
    call :wait_for_service "%OLLAMA_URL%/api/tags" "Ollama" 30
    if %errorlevel% neq 0 (
        call :print_error "Ollama failed to start within 30 seconds"
        call :print_info "Troubleshooting: Check logs at %LOG_DIR%\ollama_%TIMESTAMP%.log"
        goto :end
    )
    call :print_ok "Ollama service started"
)
call :print_info "  Access: %OLLAMA_URL%"

:: ============================================================
:: 4. Start FastAPI Backend
:: ============================================================
call :print_header "Starting FastAPI Backend"

call :check_port 8000
if %errorlevel% equ 0 (
    call :print_ok "Backend is already running on port 8000"
) else (
    call :print_info "Starting FastAPI backend..."
    set "BACKEND_DIR=%~dp0backend"
    cd /d "%BACKEND_DIR%"
    start /b cmd /c "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info" >"%LOG_DIR%\backend_%TIMESTAMP%.log" 2>&1
    cd /d "%~dp0"
    call :wait_for_service "%BACKEND_URL%/health" "FastAPI Backend" 30
    if %errorlevel% neq 0 (
        call :print_error "FastAPI Backend failed to start within 30 seconds"
        call :print_info "Troubleshooting: Check logs at %LOG_DIR%\backend_%TIMESTAMP%.log"
        goto :end
    )
    call :print_ok "FastAPI Backend started"
)
call :print_info "  Access: %BACKEND_URL%"
call :print_info "  Health: %BACKEND_URL%/health"

:: ============================================================
:: 5. Start Vite Frontend
:: ============================================================
call :print_header "Starting Vite Frontend"

call :check_port 3000
if %errorlevel% equ 0 (
    call :print_ok "Frontend is already running on port 3000"
) else (
    call :print_info "Starting Vite dev server..."
    set "FRONTEND_DIR=%~dp0frontend"
    cd /d "%FRONTEND_DIR%"
    if not exist "node_modules" (
        call :print_info "Installing npm dependencies..."
        call npm install >"%LOG_DIR%\npm_install_%TIMESTAMP%.log" 2>&1
    )
    start /b cmd /c "npx vite --port 3000" >"%LOG_DIR%\frontend_%TIMESTAMP%.log" 2>&1
    cd /d "%~dp0"
    call :wait_for_service "%FRONTEND_URL%" "Vite Frontend" 30
    if %errorlevel% neq 0 (
        call :print_error "Vite Frontend failed to start within 30 seconds"
        call :print_info "Troubleshooting: Check logs at %LOG_DIR%\frontend_%TIMESTAMP%.log"
        goto :end
    )
    call :print_ok "Vite Frontend started"
)
call :print_info "  Access: %FRONTEND_URL%"

:: ============================================================
:: 6. Service Monitor
:: ============================================================
call :print_header "All Services Started - Monitoring"
call :print_info "Press Ctrl+C to stop monitoring and exit"
call :print_info "Services:"
call :print_info "  [Ollama]         %OLLAMA_URL%"
call :print_info "  [FastAPI]        %BACKEND_URL%"
call :print_info "  [Vite Frontend]  %FRONTEND_URL%"

:monitor_loop
timeout /t 10 /nobreak >nul 2>&1

call :check_service "%OLLAMA_URL%/api/tags" "Ollama"
call :check_service "%BACKEND_URL%/health" "FastAPI"
call :check_service "%FRONTEND_URL%" "Frontend"

goto :monitor_loop

:: ============================================================
:: Health Check Mode
:: ============================================================
:health_check
call :print_header "Health Check"

call :print_info "Checking Ollama..."
call :check_service "%OLLAMA_URL%/api/tags" "Ollama"

call :print_info "Checking FastAPI Backend..."
call :check_service "%BACKEND_URL%/health" "FastAPI"

call :print_info "Checking Vite Frontend..."
call :check_service "%FRONTEND_URL%" "Frontend"

call :print_header "Health Check Complete"
goto :end

:: ============================================================
:: Helper Functions
:: ============================================================

:check_port
:: Check if a port is in use, returns 0 if in use, 1 if free
netstat -an | findstr ":%1 " | findstr "LISTENING" >nul 2>&1
exit /b

:wait_for_service
:: Wait for a service to become available (max %2 seconds)
set "url=%~1"
set "name=%~2"
set "max_wait=%~3"
set "elapsed=0"

:wait_loop
if %elapsed% geq %max_wait% exit /b 1

powershell -Command "try { $r = Invoke-WebRequest -Uri '%url%' -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% equ 0 exit /b 0

timeout /t 2 /nobreak >nul 2>&1
set /a elapsed+=2
call :print_info "  Waiting for %name%... (%elapsed%s/%max_wait%s)"
goto :wait_loop

:check_service
:: Check a single service and print status
set "url=%~1"
set "name=%~2"

powershell -Command "try { $r = Invoke-WebRequest -Uri '%url%' -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop; Write-Host '  [OK] %name%' } catch { Write-Host '  [FAIL] %name%' }"
exit /b

:print_header
echo.
echo ========================================
echo  %~1
echo ========================================
exit /b

:print_ok
echo  [OK] %~1
exit /b

:print_info
echo  [INFO] %~1
exit /b

:print_warn
echo  [WARN] %~1
exit /b

:print_error
echo  [ERROR] %~1
exit /b

:end
echo.
echo Press any key to exit...
pause >nul
