# 数据集管理

本目录用于管理所有用于基准测试的数据集。

## 📁 目录结构

```
datasets/
├── raw/                    # 原始下载的数据
│   ├── wikipedia-zh/
│   ├── clue-corpus/
│   └── dureader/
│
├── processed/              # 转换后的 TSV 格式
│   ├── wikipedia-zh.tsv
│   ├── clue-corpus.tsv
│   └── test-small.tsv
│
├── scripts/                # 数据处理脚本
│   ├── convert_to_tsv.py
│   ├── validate_tsv.py
│   └── prepare_dataset.sh
│
└── README.md              # 本文件
```

## 🚀 快速开始

### 1. 准备数据集

#### 方式 A：从 Hugging Face 直接下载并转换

```bash
cd ~/VectorDB-Benchmark/datasets/scripts

# 下载 Wikipedia 中文（约130万条）
python3 convert_to_tsv.py \
  --format huggingface \
  "wikipedia" \
  ../processed/wikipedia-zh.tsv \
  --text-field text \
  --max-samples 1500000

# 下载 CLUECorpus2020（约1400万条，取300万）
python3 convert_to_tsv.py \
  --format huggingface \
  "CLUEbenchmark/CLUECorpus2020" \
  ../processed/clue-corpus.tsv \
  --text-field content \
  --max-samples 3000000
```

#### 方式 B：转换本地文件

```bash
# JSON 格式
python3 convert_to_tsv.py \
  --format json \
  ../raw/my-dataset/data.json \
  ../processed/my-dataset.tsv \
  --text-field text

# Parquet 格式
python3 convert_to_tsv.py \
  --format parquet \
  ../raw/my-dataset/data.parquet \
  ../processed/my-dataset.tsv \
  --text-field text
```

### 2. 校验数据集

```bash
cd ~/VectorDB-Benchmark/datasets/scripts

# 校验格式
python3 validate_tsv.py ../processed/wikipedia-zh.tsv

# 校验更多行（默认只检查前1000行）
python3 validate_tsv.py ../processed/wikipedia-zh.tsv --check-lines 10000
```

### 3. 切换测试数据集

```bash
cd ~/VectorDB-Benchmark/datasets/scripts

# 方式1：使用脚本（推荐）
chmod +x prepare_dataset.sh

# 列出可用数据集
./prepare_dataset.sh

# 切换到 Wikipedia 中文数据集
./prepare_dataset.sh wikipedia-zh.tsv

# 切换到 CLUE 数据集
./prepare_dataset.sh clue-corpus.tsv

# 方式2：手动创建软链接
ln -sf ~/VectorDB-Benchmark/datasets/processed/wikipedia-zh.tsv \
       ~/VectorDB-Benchmark/phase1_embedding/data/ms_marco/collection.tsv
```

### 4. 运行测试

```bash
cd ~/VectorDB-Benchmark/phase1_embedding
python run_phase1.py --config ../config/phase1_config.yaml
```

## 📋 数据集要求

### 格式要求

- **文件格式**: TSV (Tab-Separated Values)
- **编码**: UTF-8
- **每行格式**: `<文档ID>\t<文档内容>`
- **文档ID**: 唯一标识符（数字或字符串）
- **文档内容**: 纯文本，不包含换行符和制表符

### 内容要求

- **文本长度**: 建议 10-512 字符（可在转换时指定）
- **数据量**: 根据测试需求，建议 10万-500万条
- **语言**: 中文或英文
- **质量**: 真实文本，避免大量重复

### 示例

```tsv
0	人工智能是计算机科学的一个分支，致力于创建能够执行需要人类智能的任务的系统。
1	机器学习是人工智能的一个子集，使计算机能够从数据中学习而无需显式编程。
2	深度学习使用神经网络来处理复杂的模式识别任务。
```

## 🔄 数据集管理工作流

### 完整流程

```bash
# 1. 下载原始数据到 raw/
cd ~/VectorDB-Benchmark/datasets/raw
# ... 下载数据 ...

# 2. 转换为 TSV 格式
cd ~/VectorDB-Benchmark/datasets/scripts
python3 convert_to_tsv.py \
  --format json \
  ../raw/my-dataset/data.json \
  ../processed/my-dataset.tsv

# 3. 校验格式
python3 validate_tsv.py ../processed/my-dataset.tsv

# 4. 准备测试
./prepare_dataset.sh my-dataset.tsv

# 5. 运行测试
cd ~/VectorDB-Benchmark/phase1_embedding
python run_phase1.py --config ../config/phase1_config.yaml

# 6. 切换数据集重复测试
cd ~/VectorDB-Benchmark/datasets/scripts
./prepare_dataset.sh another-dataset.tsv
cd ~/VectorDB-Benchmark/phase1_embedding
python run_phase1.py --config ../config/phase1_config.yaml
```

## 📊 推荐数据集

### 中文数据集

| 数据集 | 规模 | 来源 | 推荐度 | 下载方式 |
|--------|------|------|--------|----------|
| Wikipedia-zh | 130万 | 维基百科 | ⭐⭐⭐⭐⭐ | Hugging Face |
| CLUECorpus2020 | 1400万+ | 新闻/百科 | ⭐⭐⭐⭐⭐ | Hugging Face |
| DuReader | 90万 | 百度搜索 | ⭐⭐⭐⭐ | Hugging Face |

### 英文数据集

| 数据集 | 规模 | 来源 | 推荐度 | 下载方式 |
|--------|------|------|--------|----------|
| MS MARCO | 880万 | 微软搜索 | ⭐⭐⭐⭐⭐ | 官方/Hugging Face |
| Wikipedia-en | 600万+ | 维基百科 | ⭐⭐⭐⭐⭐ | Hugging Face |

## 🛠️ 高级用法

### 创建测试子集

```bash
# 从大数据集创建小测试集
head -n 100000 ../processed/clue-corpus.tsv > ../processed/test-100k.tsv

# 或使用转换脚本限制行数
python3 convert_to_tsv.py \
  --format huggingface \
  "CLUEbenchmark/CLUECorpus2020" \
  ../processed/test-small.tsv \
  --max-samples 100000
```

### 合并多个数据集

```bash
# 合并多个数据集
cat ../processed/wikipedia-zh.tsv \
    ../processed/dureader.tsv \
    > ../processed/combined.tsv

# 重新编号ID
awk -F'\t' '{print NR-1 "\t" $2}' ../processed/combined.tsv \
    > ../processed/combined-reindex.tsv
```

### 数据集统计

```bash
# 统计行数
wc -l ../processed/*.tsv

# 统计文件大小
du -h ../processed/*.tsv

# 抽样查看
head -n 10 ../processed/wikipedia-zh.tsv
tail -n 10 ../processed/wikipedia-zh.tsv
```

## 🔍 故障排查

### 转换失败

```bash
# 检查 Python 依赖
pip install datasets pandas pyarrow tqdm

# 检查磁盘空间
df -h

# 检查内存
free -h
```

### 校验失败

```bash
# 检查文件编码
file ../processed/my-dataset.tsv

# 检查文件格式
head -n 5 ../processed/my-dataset.tsv | cat -A

# 手动修复（去除换行符和制表符）
sed 's/\t/ /g; s/\n/ /g' input.tsv > output.tsv
```

### 软链接问题

```bash
# 检查软链接
ls -l ~/VectorDB-Benchmark/phase1_embedding/data/ms_marco/collection.tsv

# 删除损坏的软链接
rm ~/VectorDB-Benchmark/phase1_embedding/data/ms_marco/collection.tsv

# 重新创建
./prepare_dataset.sh wikipedia-zh.tsv
```

## 📝 注意事项

1. **磁盘空间**: 确保有足够空间存储原始数据和转换后的 TSV 文件
2. **备份**: 重要数据集建议备份到多个位置
3. **版本管理**: 记录数据集版本和来源，方便复现结果
4. **清理**: 定期清理不需要的数据集和备份文件

## 🆘 获取帮助

```bash
# 查看脚本帮助
python3 convert_to_tsv.py --help
python3 validate_tsv.py --help
./prepare_dataset.sh
```
