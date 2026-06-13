@echo off
REM LoRA模型微调环境配置脚本
REM 设置统一的Unsloth编译缓存目录
set UNSLOTH_COMPILE_LOCATION=.cache\unsloth_compiled_cache

echo ================================
echo 配置LoRA微调环境
echo Unsloth缓存: %UNSLOTH_COMPILE_LOCATION%
echo ================================

echo.
echo [1/3] 检查Python版本...
python --version
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请先安装Python 3.10+
    pause
    exit /b 1
)

echo.
echo [2/3] 安装基础依赖...
pip install -r requirements.txt

echo.
echo [3/3] 安装PyTorch (CUDA 12.1版本)...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

echo.
echo ================================
echo 环境配置完成!
echo ================================
echo.
echo 运行验证脚本:
echo python scripts/test_model_load.py
echo.
echo 开始训练:
echo python scripts/train.py
echo.
pause
