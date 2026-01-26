@echo off
REM 快速性能测试脚本 (Windows)

echo 🚀 Phase 1 快速性能测试
echo.

REM 检查依赖
python -c "import httpx" 2>nul
if %errorlevel% neq 0 (
    echo ⚠  安装依赖...
    pip install httpx aiofiles tqdm
)

REM 运行测试（默认：仅异步模式）
set MODE=%1
if "%MODE%"=="" set MODE=async

echo 测试模式: %MODE%
echo.

python test_async_performance.py --mode %MODE%

echo.
echo ✓ 完成！查看结果: python compare_results.py
echo.
pause
