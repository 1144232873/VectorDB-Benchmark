#!/bin/bash
#
# 快速开始：生成测试数据并运行第一次基准测试
# 用法: ./quick_start.sh [数量]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 默认生成 10 万条数据（快速测试）
NUM_SAMPLES=${1:-100000}

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "  VectorDB Benchmark - 快速开始"
echo "=========================================="
echo ""
echo "本脚本将："
echo "  1. 生成 ${NUM_SAMPLES} 条中文测试数据"
echo "  2. 校验数据格式"
echo "  3. 准备测试环境"
echo "  4. 显示下一步操作指南"
echo ""
read -p "按 Enter 继续，Ctrl+C 取消..."

# 1. 生成测试数据
echo ""
echo -e "${GREEN}[1/4] 生成测试数据...${NC}"
python3 "$SCRIPT_DIR/generate_test_data.py" \
  "$SCRIPT_DIR/../processed/quick-test.tsv" \
  -n ${NUM_SAMPLES} \
  -l zh \
  --min-length 50 \
  --max-length 200

# 2. 校验数据
echo ""
echo -e "${GREEN}[2/4] 校验数据格式...${NC}"
python3 "$SCRIPT_DIR/validate_tsv.py" \
  "$SCRIPT_DIR/../processed/quick-test.tsv" \
  --check-lines 1000

# 3. 准备测试
echo ""
echo -e "${GREEN}[3/4] 准备测试环境...${NC}"
bash "$SCRIPT_DIR/prepare_dataset.sh" quick-test.tsv

# 4. 显示指南
echo ""
echo -e "${GREEN}[4/4] 准备完成！${NC}"
echo ""
echo "=========================================="
echo "  下一步操作"
echo "=========================================="
echo ""
echo "1. 检查数据集："
echo "   ls -lh $PROJECT_ROOT/phase1_embedding/data/ms_marco/collection.tsv"
echo ""
echo "2. 查看数据样例："
echo "   head -n 5 $PROJECT_ROOT/phase1_embedding/data/ms_marco/collection.tsv"
echo ""
echo "3. 运行基准测试："
echo "   cd $PROJECT_ROOT/phase1_embedding"
echo "   python run_phase1.py --config ../config/phase1_config.yaml"
echo ""
echo "4. 或后台运行（推荐）："
echo "   cd $PROJECT_ROOT/phase1_embedding"
echo "   nohup python run_phase1.py --config ../config/phase1_config.yaml > ../logs/phase1.log 2>&1 &"
echo "   tail -f ../logs/phase1.log"
echo ""
echo -e "${YELLOW}提示：当前使用 ${NUM_SAMPLES} 条数据进行测试${NC}"
echo "      完整测试建议使用 100 万或 300 万条数据"
echo "      可以重新运行: ./quick_start.sh 1000000"
echo ""
echo "=========================================="
