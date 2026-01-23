#!/usr/bin/env python3
"""
TSV 数据集校验工具
检查格式是否符合要求
"""

import argparse
import sys
from pathlib import Path
from collections import Counter


def validate_tsv(file_path: Path, check_lines: int = 1000):
    """校验 TSV 文件格式"""
    
    print(f"校验文件: {file_path}")
    print("=" * 60)
    
    if not file_path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    errors = []
    warnings = []
    stats = {
        'total_lines': 0,
        'valid_lines': 0,
        'empty_lines': 0,
        'malformed_lines': 0,
        'text_lengths': [],
        'ids': set()
    }
    
    # 检查文件编码
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline()
    except UnicodeDecodeError:
        errors.append("❌ 文件编码不是 UTF-8")
        print("\n".join(errors))
        return False
    
    print("✓ 编码: UTF-8")
    
    # 逐行检查
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            stats['total_lines'] += 1
            
            # 空行检查
            if not line.strip():
                stats['empty_lines'] += 1
                continue
            
            # 格式检查
            parts = line.strip().split('\t')
            if len(parts) != 2:
                stats['malformed_lines'] += 1
                if stats['malformed_lines'] <= 5:  # 只显示前5个错误
                    errors.append(f"❌ 第 {line_num} 行格式错误（应包含1个制表符）")
                continue
            
            doc_id, text = parts
            
            # ID 检查
            if doc_id in stats['ids']:
                warnings.append(f"⚠️  第 {line_num} 行: ID 重复 ({doc_id})")
            stats['ids'].add(doc_id)
            
            # 文本检查
            if not text.strip():
                warnings.append(f"⚠️  第 {line_num} 行: 文本为空")
                continue
            
            stats['valid_lines'] += 1
            stats['text_lengths'].append(len(text))
            
            # 限制检查行数（加速）
            if check_lines and line_num >= check_lines:
                print(f"（已检查前 {check_lines} 行，跳过剩余行快速扫描...）")
                # 继续统计总行数
                for remaining_line in f:
                    stats['total_lines'] += 1
                break
    
    # 统计信息
    print("\n统计信息:")
    print(f"  总行数: {stats['total_lines']:,}")
    print(f"  有效行数: {stats['valid_lines']:,}")
    print(f"  空行数: {stats['empty_lines']:,}")
    print(f"  格式错误行数: {stats['malformed_lines']:,}")
    print(f"  唯一ID数: {len(stats['ids']):,}")
    
    if stats['text_lengths']:
        avg_length = sum(stats['text_lengths']) / len(stats['text_lengths'])
        print(f"\n文本长度:")
        print(f"  平均: {avg_length:.1f} 字符")
        print(f"  最短: {min(stats['text_lengths'])} 字符")
        print(f"  最长: {max(stats['text_lengths'])} 字符")
    
    # 文件大小
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    print(f"\n文件大小: {file_size_mb:.2f} MB")
    
    # 显示错误和警告
    if errors:
        print("\n错误:")
        for error in errors[:10]:  # 最多显示10个
            print(f"  {error}")
        if len(errors) > 10:
            print(f"  ... 还有 {len(errors) - 10} 个错误")
    
    if warnings:
        print("\n警告:")
        for warning in warnings[:10]:  # 最多显示10个
            print(f"  {warning}")
        if len(warnings) > 10:
            print(f"  ... 还有 {len(warnings) - 10} 个警告")
    
    # 示例数据
    print("\n示例数据（前3行）:")
    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= 3:
                break
            parts = line.strip().split('\t')
            if len(parts) == 2:
                doc_id, text = parts
                preview = text[:80] + "..." if len(text) > 80 else text
                print(f"  {doc_id}\t{preview}")
    
    print("\n" + "=" * 60)
    
    # 判断结果
    if errors:
        print("❌ 校验失败！存在格式错误")
        return False
    elif stats['valid_lines'] == 0:
        print("❌ 校验失败！没有有效数据")
        return False
    else:
        print("✓ 校验通过！格式正确")
        if warnings:
            print(f"⚠️  存在 {len(warnings)} 个警告")
        return True


def main():
    parser = argparse.ArgumentParser(description="TSV 数据集校验工具")
    parser.add_argument("file", type=str, help="TSV 文件路径")
    parser.add_argument("--check-lines", type=int, default=1000, help="检查前N行（0=全部）")
    
    args = parser.parse_args()
    
    file_path = Path(args.file)
    success = validate_tsv(file_path, args.check_lines)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
