# 向量数据库基准测试 (2026版)

> 为数据湖知识库场景选择最优向量数据库方案

## 🎯 项目目标

测试对比 **Elasticsearch 9.1、Milvus 2.5 (CPU/GPU)、Qdrant 1.12**，为包含**数据湖(亿级)、团队库(百万级)、个人库(万级)**的知识管理系统选择最优方案。

## 🔐 远程机器连接

```bash
# 连接信息
ssh -p 2222 root@192.168.1.51

# 建议配置 ~/.ssh/config 简化操作：
Host benchmark
    HostName 192.168.1.51
    Port 2222
    User root

# 配置后简化为：
ssh benchmark
```

## 🚀 快速开始

### 1. 部署代码到远程

```bash
# 使用 rsync（推荐）
rsync -avz -e "ssh -p 2222" \
  --exclude '__pycache__' --exclude '.git' \
  VectorDB-Benchmark/ root@192.168.1.51:~/VectorDB-Benchmark/

# 或配置 SSH Config 后简化为：
rsync -avz --exclude '__pycache__' \
  VectorDB-Benchmark/ benchmark:~/VectorDB-Benchmark/
```

### 2. 运行阶段一：向量生成测试 (17-26小时)

```bash
# 在终端窗口1中运行
ssh -p 2222 root@192.168.1.51
cd ~/VectorDB-Benchmark/phase1_embedding

# 环境配置（首次，使用uv快速安装）
uv venv
source .venv/bin/activate
uv pip install -e .

# 运行测试
python run_phase1.py --config ../config/phase1_config.yaml

# 可选：后台运行（可以关闭SSH连接）
nohup python run_phase1.py --config ../config/phase1_config.yaml > ../logs/phase1.log 2>&1 &

# 在新窗口中监控进度
tail -f ~/VectorDB-Benchmark/logs/phase1.log
watch -n 1 nvidia-smi
```

### 3. 运行阶段二：向量搜索测试 (6-8小时)

```bash
# 在新的终端窗口中运行
cd ~/VectorDB-Benchmark/phase2_search

# 启动数据库
docker-compose up -d

# 安装依赖（首次）
uv venv
source .venv/bin/activate
uv pip install -e .

# 运行测试
python run_phase2.py --config ../config/phase2_config.yaml

# 可选：后台运行
nohup python run_phase2.py --config ../config/phase2_config.yaml > ../logs/phase2.log 2>&1 &
```

### 4. 查看报告

```bash
# 方式1：端口转发
ssh -p 2222 -L 8080:localhost:8080 root@192.168.1.51
cd ~/VectorDB-Benchmark/phase1_results
python3 -m http.server 8080
# 浏览器访问: http://localhost:8080/embedding_benchmark_report.html

# 方式2：下载报告
scp -P 2222 root@192.168.1.51:~/VectorDB-Benchmark/phase1_results/*.html ./reports/
```

## 📊 测试内容

### 阶段一：向量生成测试
- 测试5个嵌入模型：BGE-base-zh-v1.5、BGE-M3、Qwen2.5-Embedding (0.6B/4B/8B)
- 评估推理速度、显存占用、向量质量
- 输出：模型对比报告 + 向量缓存(~300GB)

### 阶段二：向量搜索测试
- 测试4个数据库：Elasticsearch 9.1 (BBQ)、Milvus 2.5 CPU/GPU (GPU-CAGRA)、Qdrant 1.12
- 评估搜索延迟、吞吐量、召回率、资源占用
- 测试业务场景：数据湖、团队库、个人库
- 输出：最终选型报告

## 💡 预期结论

**推荐：Elasticsearch 9.1+**
- ✅ BBQ量化：性能提升2-5倍，内存节省90%
- ✅ ILM自动分层：热(7天)→温(30天)→冷(90天+)
- ✅ 混合搜索：BM25+向量+标量过滤一次完成
- ✅ 统计聚合：领导看板、热点分析开箱即用
- ✅ 成本合理：$6-7k/月

**备选：Milvus GPU** (极致性能场景)
- QPS > 500，延迟 < 20ms
- 成本高3倍 ($15k+/月)

## 🔧 常用命令

```bash
# 连接（在多个终端窗口中打开）
ssh -p 2222 root@192.168.1.51

# 查看日志
tail -f ~/VectorDB-Benchmark/logs/phase1.log

# 查看 GPU
nvidia-smi

# 查看运行中的任务
ps aux | grep python

# 停止后台任务
kill <PID>

# 下载报告
scp -P 2222 root@192.168.1.51:~/VectorDB-Benchmark/phase1_results/*.html ./
```

## 📁 项目结构

```
VectorDB-Benchmark/
├── config/                      # 配置文件
│   ├── phase1_config.yaml       # 阶段一配置
│   ├── phase2a_config.yaml      # 阶段二A配置
│   └── phase2b_config.yaml      # 阶段二B配置
│
├── datasets/                    # 数据集管理（新增）
│   ├── raw/                     # 原始数据存储
│   ├── processed/               # 转换后的TSV数据
│   ├── scripts/                 # 数据处理工具
│   │   ├── convert_to_tsv.py   # 格式转换
│   │   ├── validate_tsv.py     # 格式校验
│   │   ├── prepare_dataset.sh  # 一键准备
│   │   ├── generate_test_data.py # 快速生成测试数据
│   │   └── quick_start.sh      # 快速开始
│   ├── README.md                # 使用说明
│   └── EXAMPLES.md              # 使用示例
│
├── phase1_embedding/            # 阶段一：向量生成
│   ├── models/                  # 模型客户端
│   │   └── xinference_client.py
│   ├── data/                    # 数据加载
│   │   └── ms_marco_loader.py
│   ├── benchmarks/              # 性能测试
│   │   ├── gpu_monitor.py
│   │   └── inference_benchmark.py
│   ├── cache/                   # 向量缓存
│   │   └── vector_cache.py
│   ├── pyproject.toml          # uv依赖配置
│   ├── report_generator.py     # 报告生成
│   └── run_phase1.py           # 主入口
│
├── phase2_search/               # 阶段二：向量搜索
│   ├── clients/                 # 数据库客户端
│   ├── benchmarks/              # 性能测试
│   ├── scenarios/               # 场景测试
│   ├── tools/                   # 手动工具
│   ├── docker-compose.yml      # 数据库部署
│   └── pyproject.toml          # uv依赖配置
│
├── logs/                        # 日志目录
├── vector_cache/                # 向量缓存存储
├── phase1_results/              # 阶段一结果
├── phase2_results/              # 阶段二结果
│
├── README.md                    # 项目主文档
├── QUICK_START.md              # 快速开始指南
├── SETUP_REMOTE.md             # 远程部署配置
├── UV_SETUP_GUIDE.md           # UV详细使用指南
├── .gitignore                  # Git忽略配置
└── .python-version             # Python版本
```

## 🆘 故障排查

```bash
# 连接失败
ping 192.168.1.51
telnet 192.168.1.51 2222

# Xinference 检查
ssh -p 2222 root@192.168.1.51 "curl http://localhost:9997/v1/models"

# Docker 问题
docker-compose logs elasticsearch
docker-compose restart
docker system prune -f

# 查看运行中的任务
ps aux | grep python
ps aux | grep run_phase
```

## 📖 详细文档

完整技术方案请查看：**[向量库选型与基准性能测试.md](向量库选型与基准性能测试.md)**

---

**时间线**: 准备10分钟 + 阶段一17-26小时 + 阶段二6-8小时 = 约3天  
**重要**: 所有测试在远程机器 192.168.1.51 执行，本地仅用于连接和查看结果
