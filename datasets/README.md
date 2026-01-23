# 数据集管理

## 🚀 快速开始

```bash
cd ~/VectorDB-Benchmark/datasets/scripts

# 一键生成测试数据并运行
chmod +x quick_start.sh
./quick_start.sh 100000  # 生成10万条中文测试数据
```

## 📋 数据格式要求

**文件位置**: `~/VectorDB-Benchmark/phase1_embedding/data/dataset/collection.tsv`

**文件格式**: TSV (制表符分隔)
```tsv
<ID>\t<文本内容>
<ID>\t<文本内容>
```

**示例**:
```tsv
0	人工智能是计算机科学的一个分支，致力于创建能够执行需要人类智能的任务的系统。
1	机器学习是人工智能的一个子集，使计算机能够从数据中学习而无需显式编程。
```

**要求**:
- 编码: UTF-8
- 每行一条数据
- ID 和文本用 TAB 分隔
- 文本长度: 10-512 字符

## 🛠️ 工具使用

### 1. 生成测试数据
```bash
python3 generate_test_data.py ../processed/test.tsv -n 100000 -l zh
```

### 2. 从 Hugging Face 下载
```bash
python3 convert_to_tsv.py \
  --format huggingface \
  "CLUEbenchmark/CLUECorpus2020" \
  ../processed/clue.tsv \
  --text-field content \
  --max-samples 3000000
```

### 3. 转换本地文件
```bash
# JSON 格式
python3 convert_to_tsv.py --format json input.json ../processed/output.tsv

# Parquet 格式
python3 convert_to_tsv.py --format parquet input.parquet ../processed/output.tsv
```

### 4. 校验数据
```bash
python3 validate_tsv.py ../processed/your-dataset.tsv
```

### 5. 切换数据集
```bash
# 列出可用数据集
./prepare_dataset.sh

# 切换到指定数据集
./prepare_dataset.sh your-dataset.tsv
```

## 📊 推荐数据集

| 数据集 | 规模 | 语言 | 下载方式 |
|--------|------|------|----------|
| CLUECorpus2020 | 1400万+ | 中文 | Hugging Face |
| Wikipedia-zh | 130万 | 中文 | Hugging Face |
| 生成数据 | 任意 | 中英文 | generate_test_data.py |

## 🔍 常用命令

```bash
# 检查当前数据集
ls -l ~/VectorDB-Benchmark/phase1_embedding/data/dataset/collection.tsv

# 查看数据样例
head -n 5 ~/VectorDB-Benchmark/phase1_embedding/data/dataset/collection.tsv

# 统计行数
wc -l ~/VectorDB-Benchmark/phase1_embedding/data/dataset/collection.tsv
```

## 📖 更多帮助

```bash
python3 convert_to_tsv.py --help
python3 validate_tsv.py --help
python3 generate_test_data.py --help
```
