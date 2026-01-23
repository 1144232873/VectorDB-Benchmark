#!/bin/bash
#
# 一键准备测试数据集
# 用法: ./prepare_dataset.sh <dataset_name>
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DATASETS_DIR="$PROJECT_ROOT/datasets"
TARGET_DIR="$PROJECT_ROOT/phase1_embedding/data/dataset"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印函数
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 列出可用数据集
list_datasets() {
    echo "可用的数据集:"
    echo ""
    
    if [ -d "$DATASETS_DIR/processed" ]; then
        for file in "$DATASETS_DIR/processed"/*.tsv; do
            if [ -f "$file" ]; then
                filename=$(basename "$file")
                lines=$(wc -l < "$file" | tr -d ' ')
                size=$(du -h "$file" | cut -f1)
                echo "  • $filename"
                echo "    行数: $lines | 大小: $size"
                echo ""
            fi
        done
    else
        warn "未找到 processed 目录，请先转换数据集"
    fi
}

# 校验数据集
validate_dataset() {
    local dataset_file=$1
    
    info "校验数据集: $(basename $dataset_file)"
    
    if [ ! -f "$dataset_file" ]; then
        error "文件不存在: $dataset_file"
        exit 1
    fi
    
    python3 "$SCRIPT_DIR/validate_tsv.py" "$dataset_file"
    
    if [ $? -ne 0 ]; then
        error "数据集校验失败"
        exit 1
    fi
}

# 准备数据集
prepare_dataset() {
    local dataset_name=$1
    local source_file="$DATASETS_DIR/processed/$dataset_name"
    local target_file="$TARGET_DIR/collection.tsv"
    
    # 检查源文件
    if [ ! -f "$source_file" ]; then
        error "数据集不存在: $source_file"
        echo ""
        list_datasets
        exit 1
    fi
    
    # 创建目标目录
    mkdir -p "$TARGET_DIR"
    
    # 备份当前数据集（如果存在）
    if [ -f "$target_file" ]; then
        backup_file="$TARGET_DIR/collection.backup.$(date +%Y%m%d_%H%M%S).tsv"
        info "备份当前数据集到: $(basename $backup_file)"
        mv "$target_file" "$backup_file"
    fi
    
    # 校验数据集
    validate_dataset "$source_file"
    
    # 复制或创建软链接
    info "准备数据集: $dataset_name"
    
    # 使用软链接（节省空间）
    ln -s "$source_file" "$target_file"
    info "已创建软链接: $target_file -> $source_file"
    
    # 或者使用复制（更安全）
    # cp "$source_file" "$target_file"
    # info "已复制文件到: $target_file"
    
    # 显示统计
    lines=$(wc -l < "$target_file" | tr -d ' ')
    size=$(du -h "$target_file" | cut -f1)
    
    echo ""
    echo "✓ 数据集准备完成！"
    echo "  位置: $target_file"
    echo "  行数: $lines"
    echo "  大小: $size"
    echo ""
    echo "现在可以运行测试:"
    echo "  cd $PROJECT_ROOT/phase1_embedding"
    echo "  python run_phase1.py --config ../config/phase1_config.yaml"
}

# 主函数
main() {
    echo "========================================"
    echo "  数据集准备工具"
    echo "========================================"
    echo ""
    
    if [ $# -eq 0 ]; then
        list_datasets
        echo "用法: $0 <dataset_name.tsv>"
        echo "示例: $0 wikipedia-zh.tsv"
        exit 0
    fi
    
    local dataset_name=$1
    
    # 如果没有 .tsv 后缀，自动添加
    if [[ ! "$dataset_name" =~ \.tsv$ ]]; then
        dataset_name="${dataset_name}.tsv"
    fi
    
    prepare_dataset "$dataset_name"
}

main "$@"
