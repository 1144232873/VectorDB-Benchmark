#!/bin/bash
#
# 检查数据集状态并提供修复建议
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROCESSED_DIR="$SCRIPT_DIR/../processed"
COLLECTION_FILE="$PROCESSED_DIR/collection.tsv"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "  数据集状态检查"
echo "=========================================="
echo ""

# 检查 processed 目录
if [ ! -d "$PROCESSED_DIR" ]; then
    echo -e "${RED}✗ 目录不存在: $PROCESSED_DIR${NC}"
    echo ""
    echo "创建目录："
    echo "  mkdir -p $PROCESSED_DIR"
    exit 1
fi

echo -e "${GREEN}✓ 目录存在: $PROCESSED_DIR${NC}"

# 检查 collection.tsv
if [ -f "$COLLECTION_FILE" ]; then
    echo -e "${GREEN}✓ 数据文件存在: collection.tsv${NC}"
    
    # 统计信息
    lines=$(wc -l < "$COLLECTION_FILE" | tr -d ' ')
    size=$(du -h "$COLLECTION_FILE" | cut -f1)
    
    echo ""
    echo "文件信息："
    echo "  路径: $COLLECTION_FILE"
    echo "  行数: $lines"
    echo "  大小: $size"
    
    # 显示前3行
    echo ""
    echo "数据预览（前3行）："
    head -n 3 "$COLLECTION_FILE" | while IFS=$'\t' read -r id text; do
        # 截断文本显示
        text_preview="${text:0:60}"
        if [ ${#text} -gt 60 ]; then
            text_preview="${text_preview}..."
        fi
        echo "  [$id] $text_preview"
    done
    
    echo ""
    echo -e "${GREEN}✓ 数据集准备就绪！${NC}"
    echo ""
    echo "可以运行测试："
    echo "  cd $SCRIPT_DIR/../../phase1_embedding"
    echo "  python test_async_performance.py --mode both --num-docs 1000"
    
else
    echo -e "${RED}✗ 数据文件不存在: collection.tsv${NC}"
    echo ""
    
    # 检查是否有其他文件
    echo "检查 processed 目录中的其他文件..."
    tsv_files=$(find "$PROCESSED_DIR" -maxdepth 1 -name "*.tsv" 2>/dev/null || true)
    
    if [ -n "$tsv_files" ]; then
        echo ""
        echo -e "${YELLOW}发现以下 TSV 文件：${NC}"
        for file in $tsv_files; do
            filename=$(basename "$file")
            lines=$(wc -l < "$file" | tr -d ' ')
            size=$(du -h "$file" | cut -f1)
            echo "  • $filename ($lines 行, $size)"
        done
        
        echo ""
        echo "修复方法："
        echo "1. 如果有 quick-test.tsv，重命名为 collection.tsv："
        echo "   cd $PROCESSED_DIR"
        echo "   mv quick-test.tsv collection.tsv"
        echo ""
        echo "2. 或者重新生成数据："
        echo "   cd $SCRIPT_DIR"
        echo "   ./quick_start.sh 100000"
    else
        echo -e "${YELLOW}未找到任何 TSV 文件${NC}"
        echo ""
        echo "生成数据："
        echo "  cd $SCRIPT_DIR"
        echo "  ./quick_start.sh 100000"
    fi
    
    exit 1
fi

echo "=========================================="
