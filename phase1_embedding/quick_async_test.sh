#!/bin/bash
# 快速性能测试脚本

set -e

echo "🚀 Phase 1 快速性能测试"
echo ""

# 检查依赖
if ! python -c "import httpx" 2>/dev/null; then
    echo "⚠  安装依赖..."
    pip install httpx aiofiles tqdm
fi

# 运行测试（默认：仅异步模式）
MODE="${1:-async}"
echo "测试模式: $MODE"
echo ""

python test_async_performance.py --mode $MODE

echo ""
echo "✓ 完成！查看结果: python compare_results.py"
