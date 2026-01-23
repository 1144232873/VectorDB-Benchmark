# 快速开始指南

## 🎯 项目状态

### ✅ 已完成 (Phase 1 核心完整)

**阶段一：向量生成性能测试** - **100% 完成**
- [x] 项目结构
- [x] 配置文件
- [x] Xinference客户端
- [x] MS MARCO数据集加载器
- [x] GPU监控模块
- [x] 向量缓存管理（HDF5）
- [x] 推理性能基准测试
- [x] 主程序 (run_phase1.py)

**阶段二：向量搜索性能测试** - **30% 完成**
- [x] 项目结构
- [x] 配置文件
- [x] Docker Compose（4个数据库部署）
- [ ] 数据库客户端实现
- [ ] 性能测试模块
- [ ] 主程序

## 🚀 立即可用：Phase 1 测试

### 1. 准备远程环境 (5分钟)

```bash
# 本地：配置SSH
# 编辑 C:\Users\11442\.ssh\config
Host benchmark
    HostName 192.168.1.51
    Port 2222
    User root

# 测试连接
ssh benchmark "echo 'Connected!'"
```

### 2. 同步代码到远程 (2分钟)

```bash
# 在项目目录执行
cd D:\CodeWorkSpace\Temp\VectorDB-Benchmark

# 同步到远程
rsync -avz -e "ssh -p 2222" --exclude '__pycache__' --exclude '.git' --exclude 'venv' --exclude 'logs' --exclude 'vector_cache' ./ root@192.168.1.51:~/VectorDB-Benchmark/
```

### 3. 远程环境初始化 (2分钟)

```bash
ssh benchmark
cd ~/VectorDB-Benchmark

# 安装uv (如果还没安装)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# 使用uv创建虚拟环境并安装依赖 (Phase 1)
cd phase1_embedding
uv venv
source .venv/bin/activate
uv pip install -e .

# 验证Xinference
curl http://localhost:9997/v1/models
```

### 4. 运行Phase 1测试 (9小时)

```bash
# 在终端窗口中运行
cd ~/VectorDB-Benchmark/phase1_embedding
source .venv/bin/activate

# 运行完整测试（5个模型）
python run_phase1.py --config ../config/phase1_config.yaml

# 或测试单个模型（快速验证）
python run_phase1.py --config ../config/phase1_config.yaml --models bge-base-zh-v1.5

# 可选：后台运行（可以关闭SSH连接）
nohup python run_phase1.py --config ../config/phase1_config.yaml > ../logs/phase1.log 2>&1 &
```

### 5. 监控进度

```bash
# 在新的终端窗口中查看日志
tail -f ~/VectorDB-Benchmark/logs/phase1.log

# 在另一个窗口中查看GPU
watch -n 1 nvidia-smi

# 查看运行中的任务
ps aux | grep python

# 查看生成的向量缓存
ls -lh ~/VectorDB-Benchmark/vector_cache/
du -sh ~/VectorDB-Benchmark/vector_cache/
```

### 6. 查看结果

```bash
# 方式1：端口转发
ssh -p 2222 -L 8080:localhost:8080 root@192.168.1.51
cd ~/VectorDB-Benchmark/phase1_results
python3 -m http.server 8080
# 访问: http://localhost:8080/

# 方式2：下载到本地
scp -P 2222 root@192.168.1.51:~/VectorDB-Benchmark/phase1_results/benchmark_results.json ./
```

## 📊 预期输出

### Phase 1 完成后你会得到：

1. **性能测试结果** (`phase1_results/benchmark_results.json`)
   - 5个模型的单样本延迟
   - 批处理吞吐量（不同batch size）
   - GPU显存使用峰值
   - 亿级向量生成时间推算

2. **向量缓存** (`vector_cache/`)
   - `bge-base-zh-v1.5.h5` (~9GB)
   - `bge-m3.h5` (~12GB)
   - `qwen2.5-0.6b.h5` (~12GB)
   - `qwen2.5-4b.h5` (~30GB)
   - `qwen2.5-8b.h5` (~48GB)
   - **总计约110GB**

3. **详细日志** (`logs/phase1.log`)

## 🎯 Phase 2 实施路线图

### 待实现的核心模块 (优先级顺序)

#### 1. 数据库客户端 (关键优先级)
- `phase2_search/clients/elasticsearch_client.py`
- `phase2_search/clients/milvus_client.py`
- `phase2_search/clients/qdrant_client.py`

#### 2. 性能测试模块
- `phase2_search/benchmarks/insert_benchmark.py`
- `phase2_search/benchmarks/search_latency.py`
- `phase2_search/benchmarks/throughput_benchmark.py`
- `phase2_search/benchmarks/resource_monitor.py`

#### 3. 主程序
- `phase2_search/run_phase2a.py`
- `phase2_search/run_phase2b.py`

#### 4. 报告生成
- `phase1_embedding/report_generator.py`
- `phase2_search/report_generator.py`

## 🔧 故障排查

### Xinference连接失败
```bash
ssh benchmark
curl http://localhost:9997/v1/models

# 如果失败，检查Xinference是否运行
ps aux | grep xinference
```

### GPU不可用
```bash
nvidia-smi
# 确保显示RTX 4090
```

### 磁盘空间不足
```bash
df -h
# 确保有 >200GB 可用空间
```

### 依赖安装失败
```bash
# 使用uv重新安装
cd ~/VectorDB-Benchmark/phase1_embedding
uv pip install -e . --reinstall

# 或单独安装问题依赖
uv pip install pynvml h5py openai
```

## 💡 优化建议

### 加速测试（开发阶段）
```bash
# 只测试1个模型
python run_phase1.py --models bge-base-zh-v1.5

# 使用小数据集测试
# 编辑 config/phase1_config.yaml:
# dataset:
#   sample_size: 10000  # 改为1万
```

### 生产环境配置
```bash
# 编辑 config/phase1_config.yaml
# 调整batch_size以优化显存使用
# 调整compression_level以平衡速度和空间
```

## 📖 相关文档

- [远程环境设置详细指南](SETUP_REMOTE.md)
- [Phase 1 配置说明](config/phase1_config.yaml)
- [Phase 2A 配置说明](config/phase2a_config.yaml)
- [Phase 2B 配置说明](config/phase2b_config.yaml)
- [实施进度报告](IMPLEMENTATION_PROGRESS.md)

## 🆘 获取帮助

### 查看模块文档
```bash
# Xinference客户端
python -m phase1_embedding.models.xinference_client

# MS MARCO加载器
python -m phase1_embedding.data.ms_marco_loader

# GPU监控
python -m phase1_embedding.benchmarks.gpu_monitor

# 向量缓存
python -m phase1_embedding.cache.vector_cache
```

### 常见问题

**Q: 测试需要多长时间？**
A: 完整5个模型测试约9小时。单个模型测试约30分钟-5小时不等（取决于模型大小）。

**Q: 可以中断后继续吗？**
A: 当前版本不支持断点续传。建议使用 nohup 在后台运行，避免网络中断。

**Q: 如何只测试特定模型？**
A: 使用 `--models` 参数，如：`python run_phase1.py --models qwen2.5-0.6b qwen2.5-4b`

**Q: 向量缓存可以删除吗？**
A: Phase 1完成后，向量缓存用于Phase 2测试。如果只关心Phase 1的性能数据，可以删除以节省空间。

---

**🎉 恭喜！Phase 1 核心框架已完整实现，可以立即开始测试！**
