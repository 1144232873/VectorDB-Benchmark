#!/usr/bin/env python3
"""
数据集格式转换工具
支持多种格式转换为标准 TSV 格式
"""

import json
import argparse
import sys
from pathlib import Path
from typing import Iterator, Dict
from tqdm import tqdm


def convert_json_to_tsv(input_file: Path, output_file: Path, text_field: str = "text", max_length: int = 512, min_length: int = 10):
    """JSON 格式转 TSV"""
    print(f"转换 JSON → TSV: {input_file.name}")
    
    count = 0
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        
        for line in tqdm(f_in, desc="转换中"):
            try:
                item = json.loads(line.strip())
                text = item.get(text_field, "")
                
                # 清理文本
                text = text.replace('\n', ' ').replace('\t', ' ').strip()
                
                # 过滤长度
                if min_length <= len(text) <= max_length:
                    f_out.write(f"{count}\t{text}\n")
                    count += 1
                    
            except Exception as e:
                continue
    
    print(f"✓ 完成！生成 {count:,} 条数据")
    return count


def convert_parquet_to_tsv(input_file: Path, output_file: Path, text_field: str = "text", max_length: int = 512, min_length: int = 10):
    """Parquet 格式转 TSV（需要 pandas）"""
    try:
        import pandas as pd
    except ImportError:
        print("❌ 需要安装 pandas: pip install pandas pyarrow")
        sys.exit(1)
    
    print(f"转换 Parquet → TSV: {input_file.name}")
    
    df = pd.read_parquet(input_file)
    
    count = 0
    with open(output_file, 'w', encoding='utf-8') as f_out:
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="转换中"):
            text = str(row.get(text_field, ""))
            
            # 清理文本
            text = text.replace('\n', ' ').replace('\t', ' ').strip()
            
            # 过滤长度
            if min_length <= len(text) <= max_length:
                f_out.write(f"{count}\t{text}\n")
                count += 1
    
    print(f"✓ 完成！生成 {count:,} 条数据")
    return count


def convert_huggingface_to_tsv(dataset_name: str, output_file: Path, text_field: str = "text", max_samples: int = None, max_length: int = 512, min_length: int = 10):
    """直接从 Hugging Face 加载并转换"""
    try:
        from datasets import load_dataset
    except ImportError:
        print("❌ 需要安装 datasets: pip install datasets")
        sys.exit(1)
    
    print(f"从 Hugging Face 加载: {dataset_name}")
    
    try:
        dataset = load_dataset(dataset_name, split="train")
    except Exception as e:
        print(f"❌ 加载失败: {e}")
        sys.exit(1)
    
    count = 0
    with open(output_file, 'w', encoding='utf-8') as f_out:
        for item in tqdm(dataset, desc="转换中"):
            if max_samples and count >= max_samples:
                break
                
            text = item.get(text_field, item.get('content', ''))
            
            # 清理文本
            text = text.replace('\n', ' ').replace('\t', ' ').strip()
            
            # 过滤长度
            if min_length <= len(text) <= max_length:
                f_out.write(f"{count}\t{text}\n")
                count += 1
    
    print(f"✓ 完成！生成 {count:,} 条数据")
    return count


def main():
    parser = argparse.ArgumentParser(description="数据集格式转换工具")
    parser.add_argument("input", type=str, help="输入文件路径或 Hugging Face 数据集名称")
    parser.add_argument("output", type=str, help="输出 TSV 文件路径")
    parser.add_argument("--format", choices=["json", "parquet", "huggingface"], default="json", help="输入格式")
    parser.add_argument("--text-field", default="text", help="文本字段名称（默认: text）")
    parser.add_argument("--max-samples", type=int, help="最大样本数")
    parser.add_argument("--max-length", type=int, default=512, help="最大文本长度（默认: 512）")
    parser.add_argument("--min-length", type=int, default=10, help="最小文本长度（默认: 10）")
    
    args = parser.parse_args()
    
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    if args.format == "huggingface":
        convert_huggingface_to_tsv(
            args.input, 
            output_file, 
            args.text_field, 
            args.max_samples,
            args.max_length,
            args.min_length
        )
    else:
        input_file = Path(args.input)
        if not input_file.exists():
            print(f"❌ 文件不存在: {input_file}")
            sys.exit(1)
        
        if args.format == "json":
            convert_json_to_tsv(input_file, output_file, args.text_field, args.max_length, args.min_length)
        elif args.format == "parquet":
            convert_parquet_to_tsv(input_file, output_file, args.text_field, args.max_length, args.min_length)


if __name__ == "__main__":
    main()
