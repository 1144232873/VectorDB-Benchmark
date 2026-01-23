#!/usr/bin/env python3
"""
快速生成测试数据
用于验证流程或快速测试
"""

import argparse
import random
from pathlib import Path


# 中文测试文本模板
CHINESE_TEMPLATES = [
    "人工智能是{}的重要分支，致力于创建能够执行需要人类智能的任务的系统。",
    "机器学习使计算机能够从{}中学习而无需显式编程。",
    "深度学习使用{}来处理复杂的模式识别任务。",
    "自然语言处理是{}领域的重要应用方向。",
    "计算机视觉技术在{}中有广泛应用。",
    "知识图谱是{}领域的重要基础设施。",
    "向量数据库用于高效存储和检索{}。",
    "嵌入模型将文本转换为{}表示。",
    "语义搜索基于{}的相似度匹配。",
    "大语言模型在{}任务上表现出色。",
]

CHINESE_WORDS = [
    "计算机科学", "数据分析", "神经网络", "人工智能", "信息检索",
    "模式识别", "知识管理", "高维向量", "文本语义", "多模态学习",
    "医疗诊断", "金融分析", "自动驾驶", "智能客服", "推荐系统",
]

# 英文测试文本模板
ENGLISH_TEMPLATES = [
    "Artificial intelligence is a branch of {} that aims to create systems capable of performing tasks requiring human intelligence.",
    "Machine learning enables computers to learn from {} without explicit programming.",
    "Deep learning uses {} to handle complex pattern recognition tasks.",
    "Natural language processing is an important application in the field of {}.",
    "Computer vision technology has wide applications in {}.",
    "Knowledge graphs are important infrastructure in the field of {}.",
    "Vector databases are used for efficient storage and retrieval of {}.",
    "Embedding models convert text into {} representations.",
    "Semantic search is based on similarity matching of {}.",
    "Large language models perform excellently on {} tasks.",
]

ENGLISH_WORDS = [
    "computer science", "data analysis", "neural networks", "artificial intelligence", "information retrieval",
    "pattern recognition", "knowledge management", "high-dimensional vectors", "text semantics", "multimodal learning",
    "medical diagnosis", "financial analysis", "autonomous driving", "intelligent customer service", "recommendation systems",
]


def generate_text(template, words, min_length=50, max_length=200):
    """生成随机文本"""
    text = template.format(random.choice(words))
    
    # 如果太短，添加更多内容
    while len(text) < min_length:
        text += " " + template.format(random.choice(words))
    
    # 如果太长，截断
    if len(text) > max_length:
        text = text[:max_length]
    
    return text.strip()


def generate_dataset(output_file: Path, num_samples: int, language: str = "zh", min_length: int = 50, max_length: int = 200):
    """生成测试数据集"""
    
    print(f"生成测试数据集...")
    print(f"  数量: {num_samples:,}")
    print(f"  语言: {language}")
    print(f"  长度: {min_length}-{max_length} 字符")
    print(f"  输出: {output_file}")
    
    templates = CHINESE_TEMPLATES if language == "zh" else ENGLISH_TEMPLATES
    words = CHINESE_WORDS if language == "zh" else ENGLISH_WORDS
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for i in range(num_samples):
            text = generate_text(templates[i % len(templates)], words, min_length, max_length)
            f.write(f"{i}\t{text}\n")
            
            if (i + 1) % 10000 == 0:
                print(f"  已生成: {i + 1:,}/{num_samples:,}")
    
    # 统计
    file_size_mb = output_file.stat().st_size / (1024 * 1024)
    
    print(f"\n✓ 完成！")
    print(f"  文件: {output_file}")
    print(f"  行数: {num_samples:,}")
    print(f"  大小: {file_size_mb:.2f} MB")


def main():
    parser = argparse.ArgumentParser(description="快速生成测试数据")
    parser.add_argument("output", type=str, help="输出文件路径")
    parser.add_argument("-n", "--num-samples", type=int, default=100000, help="生成数量（默认: 100000）")
    parser.add_argument("-l", "--language", choices=["zh", "en"], default="zh", help="语言（默认: zh）")
    parser.add_argument("--min-length", type=int, default=50, help="最小文本长度（默认: 50）")
    parser.add_argument("--max-length", type=int, default=200, help="最大文本长度（默认: 200）")
    
    args = parser.parse_args()
    
    output_file = Path(args.output)
    
    generate_dataset(
        output_file, 
        args.num_samples, 
        args.language,
        args.min_length,
        args.max_length
    )


if __name__ == "__main__":
    main()
