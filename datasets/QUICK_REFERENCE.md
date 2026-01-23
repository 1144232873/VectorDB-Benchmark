# 快速参考

## 一键开始
```bash
cd ~/VectorDB-Benchmark/datasets/scripts
./quick_start.sh 100000
```

## 常用命令

### 生成数据
```bash
python3 generate_test_data.py ../processed/test.tsv -n 100000 -l zh
```

### 从 HuggingFace 下载
```bash
python3 convert_to_tsv.py \
  --format huggingface "CLUEbenchmark/CLUECorpus2020" \
  ../processed/clue.tsv --max-samples 3000000
```

### 校验数据
```bash
python3 validate_tsv.py ../processed/test.tsv
```

### 切换数据集
```bash
./prepare_dataset.sh test.tsv
```

### 运行测试
```bash
cd ~/VectorDB-Benchmark/phase1_embedding
python run_phase1.py --config ../config/phase1_config.yaml
```

## 数据格式

```tsv
0	文本内容
1	文本内容
```

- 编码: UTF-8
- 分隔符: TAB (`\t`)
- 长度: 10-512 字符

## 路径

- 数据集: `phase1_embedding/data/dataset/collection.tsv`
- 原始数据: `datasets/raw/`
- 处理后: `datasets/processed/`
