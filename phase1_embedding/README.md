# Phase 1: 向量生成性能基准测试

## 快速开始

```bash
# 1. 安装依赖
uv venv && source .venv/bin/activate
uv add 'httpx[http2]'
uv sync

# 2. 运行基准测试（异步极限性能）
python benchmark.py --batch 1

# 3. 查看可用批次
python benchmark.py --list-batches

# 4. 测试指定模型
python benchmark.py --models bge-m3 qwen3-0.6b
```

## 性能特点

- **GPU 利用率**: 80-95%（异步并发16 + 大批次2048）
- **吞吐量提升**: 6-10倍
- **自动调优**: 自动寻找最优batch size
- **日志优化**: WARNING级别，减少刷屏

## 结果输出

```
phase1_embedding/
└── results/                  # 统一结果目录
    ├── benchmark_results.json  # 测试结果
    ├── *.html                  # HTML报告
    └── cache/                  # 向量缓存
```

## 配置文件

[`../config/phase1_config.yaml`](../config/phase1_config.yaml) - 主配置文件
