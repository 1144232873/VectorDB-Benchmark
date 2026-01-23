# 数据集管理 - 快速参考

## 🚀 一分钟快速开始

```bash
ssh -p 2222 root@192.168.1.51
cd ~/VectorDB-Benchmark/datasets/scripts
chmod +x quick_start.sh
./quick_start.sh 100000
```

---

## 📋 常用命令

### 生成测试数据
```bash
# 10万条（快速测试）
python3 generate_test_data.py ../processed/test.tsv -n 100000 -l zh

# 100万条（正式测试）
python3 generate_test_data.py ../processed/test.tsv -n 1000000 -l zh
```

### 从 Hugging Face 下载
```bash
# Wikipedia 中文
python3 convert_to_tsv.py \
  --format huggingface "wikipedia" \
  ../processed/wiki-zh.tsv \
  --max-samples 1500000

# CLUE Corpus
python3 convert_to_tsv.py \
  --format huggingface "CLUEbenchmark/CLUECorpus2020" \
  ../processed/clue.tsv \
  --text-field content \
  --max-samples 3000000
```

### 校验数据集
```bash
python3 validate_tsv.py ../processed/your-dataset.tsv
```

### 切换数据集
```bash
# 列出可用数据集
./prepare_dataset.sh

# 切换到指定数据集
./prepare_dataset.sh your-dataset.tsv
```

### 运行测试
```bash
cd ~/VectorDB-Benchmark/phase1_embedding

# 前台运行
python run_phase1.py --config ../config/phase1_config.yaml

# 后台运行
nohup python run_phase1.py --config ../config/phase1_config.yaml > ../logs/phase1.log 2>&1 &
tail -f ../logs/phase1.log
```

---

## 📝 数据集格式

### 要求
- **格式**：TSV（制表符分隔）
- **编码**：UTF-8
- **结构**：`<ID>\t<文本>`
- **长度**：10-512 字符

### 示例
```tsv
0	这是第一条文本内容
1	这是第二条文本内容
2	这是第三条文本内容
```

---

## 🔧 故障排查

### 检查当前数据集
```bash
ls -l ~/VectorDB-Benchmark/phase1_embedding/data/ms_marco/collection.tsv
```

### 查看数据样例
```bash
head -n 5 ~/VectorDB-Benchmark/phase1_embedding/data/ms_marco/collection.tsv
```

### 统计行数
```bash
wc -l ~/VectorDB-Benchmark/phase1_embedding/data/ms_marco/collection.tsv
```

### 重新准备数据集
```bash
cd ~/VectorDB-Benchmark/datasets/scripts
./prepare_dataset.sh your-dataset.tsv
```

---

## 📊 推荐配置

| 目的 | 数据量 | 数据来源 | 预计时间 |
|------|--------|----------|----------|
| 快速验证 | 10万 | 生成 | 1-2小时 |
| 性能评估 | 100万 | 生成/真实 | 10-15小时 |
| 完整测试 | 300万 | 真实数据 | 20-30小时 |

---

## 🔗 详细文档

- [README.md](README.md) - 完整使用说明
- [EXAMPLES.md](EXAMPLES.md) - 详细示例
- [项目主 README](../README.md) - 项目总览
