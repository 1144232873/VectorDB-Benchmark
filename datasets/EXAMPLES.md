# 数据集管理使用示例

本文档提供常见场景的完整使用示例。

## 📚 目录

1. [快速开始（10分钟）](#快速开始)
2. [生成测试数据](#生成测试数据)
3. [从 Hugging Face 下载](#从-hugging-face-下载)
4. [转换本地数据](#转换本地数据)
5. [切换数据集测试](#切换数据集测试)
6. [完整测试流程](#完整测试流程)

---

## 快速开始

**目标**：快速生成测试数据并验证流程

```bash
# 在服务器上执行
ssh -p 2222 root@192.168.1.51
cd ~/VectorDB-Benchmark/datasets/scripts

# 一键快速开始（生成10万条测试数据）
chmod +x quick_start.sh
./quick_start.sh 100000

# 按提示运行测试
cd ~/VectorDB-Benchmark/phase1_embedding
python run_phase1.py --config ../config/phase1_config.yaml
```

**预计时间**：
- 生成数据：1-2 分钟
- 运行测试：1-2 小时（10万条数据）

---

## 生成测试数据

### 场景 1：快速验证流程（10万条）

```bash
cd ~/VectorDB-Benchmark/datasets/scripts

python3 generate_test_data.py \
  ../processed/test-100k.tsv \
  -n 100000 \
  -l zh

./prepare_dataset.sh test-100k.tsv
```

### 场景 2：中等规模测试（100万条）

```bash
python3 generate_test_data.py \
  ../processed/test-1m.tsv \
  -n 1000000 \
  -l zh

./prepare_dataset.sh test-1m.tsv
```

### 场景 3：完整规模测试（300万条）

```bash
python3 generate_test_data.py \
  ../processed/test-3m.tsv \
  -n 3000000 \
  -l zh

./prepare_dataset.sh test-3m.tsv
```

### 场景 4：英文测试数据

```bash
python3 generate_test_data.py \
  ../processed/test-en-100k.tsv \
  -n 100000 \
  -l en \
  --min-length 30 \
  --max-length 150
```

---

## 从 Hugging Face 下载

### 场景 1：中文维基百科（约130万条）

```bash
cd ~/VectorDB-Benchmark/datasets/scripts

# 方法 A：使用转换脚本（推荐）
python3 convert_to_tsv.py \
  --format huggingface \
  "wikipedia" \
  ../processed/wikipedia-zh.tsv \
  --text-field text \
  --max-samples 1500000 \
  --max-length 512 \
  --min-length 10

# 校验
python3 validate_tsv.py ../processed/wikipedia-zh.tsv

# 准备测试
./prepare_dataset.sh wikipedia-zh.tsv
```

**注意**：下载可能需要代理或较长时间

### 场景 2：CLUECorpus2020（取300万条）

```bash
cd ~/VectorDB-Benchmark/datasets/scripts

python3 convert_to_tsv.py \
  --format huggingface \
  "CLUEbenchmark/CLUECorpus2020" \
  ../processed/clue-3m.tsv \
  --text-field content \
  --max-samples 3000000 \
  --max-length 512 \
  --min-length 10

python3 validate_tsv.py ../processed/clue-3m.tsv
./prepare_dataset.sh clue-3m.tsv
```

### 场景 3：本地已有 Hugging Face 数据集

```bash
# 如果已经用 datasets 下载到本地
from datasets import load_from_disk

dataset = load_from_disk("~/datasets/wikipedia-zh")
# 然后转换...
```

---

## 转换本地数据

### 场景 1：JSON Lines 格式

假设你有文件 `data.jsonl`：
```json
{"text": "第一条文本内容"}
{"text": "第二条文本内容"}
```

转换命令：
```bash
cd ~/VectorDB-Benchmark/datasets

# 1. 放置原始文件
mkdir -p raw/my-dataset
cp /path/to/data.jsonl raw/my-dataset/

# 2. 转换
cd scripts
python3 convert_to_tsv.py \
  --format json \
  ../raw/my-dataset/data.jsonl \
  ../processed/my-dataset.tsv \
  --text-field text

# 3. 校验
python3 validate_tsv.py ../processed/my-dataset.tsv

# 4. 使用
./prepare_dataset.sh my-dataset.tsv
```

### 场景 2：Parquet 格式

```bash
cd ~/VectorDB-Benchmark/datasets/scripts

python3 convert_to_tsv.py \
  --format parquet \
  ../raw/my-dataset/data.parquet \
  ../processed/my-dataset.tsv \
  --text-field content \
  --max-samples 1000000

python3 validate_tsv.py ../processed/my-dataset.tsv
./prepare_dataset.sh my-dataset.tsv
```

### 场景 3：CSV 转 TSV（手动）

```bash
# 如果有 CSV 文件，先转换为 TSV
cd ~/VectorDB-Benchmark/datasets/raw/my-dataset

# 提取 id 和 text 列，转为 TSV
awk -F',' 'NR>1 {print $1 "\t" $2}' data.csv > ../../processed/my-dataset.tsv

# 校验
cd ../../scripts
python3 validate_tsv.py ../processed/my-dataset.tsv
```

---

## 切换数据集测试

### 场景 1：对比不同数据集性能

```bash
cd ~/VectorDB-Benchmark/datasets/scripts

# 测试 1：生成数据（10万条）
python3 generate_test_data.py ../processed/test-100k.tsv -n 100000
./prepare_dataset.sh test-100k.tsv

cd ~/VectorDB-Benchmark/phase1_embedding
python run_phase1.py --config ../config/phase1_config.yaml

# 备份结果
mv phase1_results phase1_results_test-100k

# 测试 2：维基百科（130万条）
cd ~/VectorDB-Benchmark/datasets/scripts
./prepare_dataset.sh wikipedia-zh.tsv

cd ~/VectorDB-Benchmark/phase1_embedding
python run_phase1.py --config ../config/phase1_config.yaml

# 备份结果
mv phase1_results phase1_results_wikipedia

# 对比结果
diff phase1_results_test-100k/benchmark_results.json \
     phase1_results_wikipedia/benchmark_results.json
```

### 场景 2：不同文本长度对比

```bash
# 短文本（50-100字符）
python3 generate_test_data.py \
  ../processed/short-text.tsv \
  -n 500000 \
  --min-length 50 \
  --max-length 100

# 中等长度（100-300字符）
python3 generate_test_data.py \
  ../processed/medium-text.tsv \
  -n 500000 \
  --min-length 100 \
  --max-length 300

# 长文本（300-512字符）
python3 generate_test_data.py \
  ../processed/long-text.tsv \
  -n 500000 \
  --min-length 300 \
  --max-length 512

# 依次测试
for dataset in short medium long; do
  ./prepare_dataset.sh ${dataset}-text.tsv
  cd ~/VectorDB-Benchmark/phase1_embedding
  python run_phase1.py --config ../config/phase1_config.yaml
  mv phase1_results phase1_results_${dataset}
  cd ~/VectorDB-Benchmark/datasets/scripts
done
```

---

## 完整测试流程

### 完整示例：从零开始到获得报告

```bash
# ========================================
# 第一步：连接服务器
# ========================================
ssh -p 2222 root@192.168.1.51

# ========================================
# 第二步：准备数据集（选择一种方式）
# ========================================

cd ~/VectorDB-Benchmark/datasets/scripts

# 方式 A：快速测试（10万条，约1-2小时）
python3 generate_test_data.py ../processed/test-100k.tsv -n 100000 -l zh
./prepare_dataset.sh test-100k.tsv

# 方式 B：中等规模（100万条，约10-15小时）
python3 generate_test_data.py ../processed/test-1m.tsv -n 1000000 -l zh
./prepare_dataset.sh test-1m.tsv

# 方式 C：完整测试（300万条，约20-30小时）
python3 convert_to_tsv.py \
  --format huggingface \
  "CLUEbenchmark/CLUECorpus2020" \
  ../processed/clue-3m.tsv \
  --max-samples 3000000
./prepare_dataset.sh clue-3m.tsv

# ========================================
# 第三步：验证数据集
# ========================================

# 检查文件
ls -lh ~/VectorDB-Benchmark/phase1_embedding/data/ms_marco/collection.tsv

# 查看示例
head -n 5 ~/VectorDB-Benchmark/phase1_embedding/data/ms_marco/collection.tsv

# 统计信息
wc -l ~/VectorDB-Benchmark/phase1_embedding/data/ms_marco/collection.tsv

# ========================================
# 第四步：配置测试参数（可选）
# ========================================

cd ~/VectorDB-Benchmark
vim config/phase1_config.yaml

# 调整 sample_size（如果数据集很大）
# dataset:
#   sample_size: 1000000  # 实际测试数量

# ========================================
# 第五步：运行测试
# ========================================

cd ~/VectorDB-Benchmark/phase1_embedding

# 前台运行（可以看到实时输出）
python run_phase1.py --config ../config/phase1_config.yaml

# 或后台运行（推荐，可以关闭 SSH）
nohup python run_phase1.py --config ../config/phase1_config.yaml > ../logs/phase1.log 2>&1 &

# 查看进度
tail -f ../logs/phase1.log

# 另开一个终端监控 GPU
ssh -p 2222 root@192.168.1.51
watch -n 1 nvidia-smi

# ========================================
# 第六步：查看结果
# ========================================

# 等待测试完成后

# 查看结果文件
ls -lh ~/VectorDB-Benchmark/phase1_results/

# 下载报告到本地
# 在本地电脑执行：
scp -P 2222 root@192.168.1.51:~/VectorDB-Benchmark/phase1_results/*.html ./

# 或使用端口转发在浏览器查看
# 在本地电脑执行：
ssh -p 2222 -L 8080:localhost:8080 root@192.168.1.51
# 在服务器上执行：
cd ~/VectorDB-Benchmark/phase1_results
python3 -m http.server 8080
# 浏览器访问：http://localhost:8080/

# ========================================
# 第七步：切换数据集重复测试（可选）
# ========================================

cd ~/VectorDB-Benchmark/datasets/scripts

# 备份当前结果
mv ~/VectorDB-Benchmark/phase1_results \
   ~/VectorDB-Benchmark/phase1_results_backup_$(date +%Y%m%d)

# 切换数据集
./prepare_dataset.sh another-dataset.tsv

# 重新运行测试
cd ~/VectorDB-Benchmark/phase1_embedding
nohup python run_phase1.py --config ../config/phase1_config.yaml > ../logs/phase1_new.log 2>&1 &
```

---

## 常见问题

### Q1: 如何知道当前使用的是哪个数据集？

```bash
ls -l ~/VectorDB-Benchmark/phase1_embedding/data/ms_marco/collection.tsv
# 如果是软链接，会显示指向的原始文件
```

### Q2: 如何清理旧的备份数据集？

```bash
# 查看备份
ls ~/VectorDB-Benchmark/phase1_embedding/data/ms_marco/collection.backup.*

# 删除旧备份（保留最近3个）
cd ~/VectorDB-Benchmark/phase1_embedding/data/ms_marco/
ls -t collection.backup.* | tail -n +4 | xargs rm -f
```

### Q3: 磁盘空间不足怎么办？

```bash
# 检查空间
df -h

# 清理方式1：删除原始数据（保留processed）
rm -rf ~/VectorDB-Benchmark/datasets/raw/*

# 清理方式2：压缩旧数据集
gzip ~/VectorDB-Benchmark/datasets/processed/old-dataset.tsv

# 清理方式3：移到其他存储
mv ~/VectorDB-Benchmark/datasets/raw/* /mnt/external-drive/
```

### Q4: 如何并行生成多个数据集？

```bash
# 使用后台任务
cd ~/VectorDB-Benchmark/datasets/scripts

python3 generate_test_data.py ../processed/test-1.tsv -n 1000000 &
python3 generate_test_data.py ../processed/test-2.tsv -n 1000000 &
python3 generate_test_data.py ../processed/test-3.tsv -n 1000000 &

# 等待完成
wait
```

---

## 性能建议

### 测试规模选择

| 目的 | 数据量 | 预计时间 | 推荐 |
|------|--------|----------|------|
| 快速验证流程 | 10万 | 1-2小时 | ✅ 生成数据 |
| 初步性能评估 | 50-100万 | 10-15小时 | ✅ 生成数据或真实数据 |
| 完整基准测试 | 300万 | 20-30小时 | ✅ 真实数据（Wikipedia/CLUE） |
| 大规模验证 | 500-1000万 | 50-100小时 | 真实数据 |

### 数据集质量

| 类型 | 生成数据 | 真实数据 |
|------|----------|----------|
| 速度 | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| 真实性 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 多样性 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 可控性 | ⭐⭐⭐⭐⭐ | ⭐⭐ |

**建议**：
- 流程验证：使用生成数据
- 正式测试：使用真实数据
- 对比测试：两者结合
