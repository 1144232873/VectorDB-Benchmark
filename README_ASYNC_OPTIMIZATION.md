# Phase 1 异步优化指南

## 一句话总结
通过**异步并发 + 大批次**，将 GPU 利用率从 20-50% 提升到 80-95%，吞吐量提升 **6-10 倍**。

## 问题根源
- ❌ 串行处理 → GPU 等待网络响应时空闲
- ❌ 批次太小（50） → GPU 并行算力未满载
- ❌ 网络延迟 → 每次请求都浪费 RTT 时间

## 优化方案
- ✅ 异步并发（8 个请求同时发送）
- ✅ 大批次（128-1024 个向量）
- ✅ 自动调优（找到最优配置）

**效果：GPU 稳定满载，吞吐量 6-10x ↑**

---

## 快速开始

### 1. 安装依赖
```bash
# 异步优化所需的依赖已集成到 pyproject.toml 中
# 如果已经安装过环境，无需额外操作
# 如果是首次安装，请按照 README.md 的说明执行：
uv venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .
```

### 2. 快速验证（2分钟）

```bash
cd phase1_embedding

# 一键测试（默认：仅异步）
./quick_async_test.sh        # Linux/Mac
quick_async_test.bat          # Windows

# 或手动指定模式
python test_async_performance.py --mode async   # 仅异步
python test_async_performance.py --mode sync    # 仅同步
python test_async_performance.py --mode both    # 对比
```

结果自动保存到 `quick_test_results/`。

### 3. 完整测试

```bash
# 推荐配置（默认 8 并发）
python run_phase1.py --async --batch 1

# 极限性能（16 并发）
python run_phase1.py --async --async-preset aggressive --batch 1

# 同步模式（对比用）
python run_phase1.py --batch 1
```

---

## 配置参数

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| concurrent_requests | 8 | 并发请求数（4=保守, 8=推荐, 16=激进） |
| batch_size | auto | 自动调优（或 128-1024） |
| max_batch_size | 2048 | 最大批次限制 |

配置文件：`config/phase1_config.yaml` → `async_inference` 区块

---

## 监控与结果

### GPU 监控
```bash
watch -n 1 nvidia-smi  # Linux
```
观察 GPU-Util 应稳定在 **80-95%**

### 查看历史结果
```bash
python compare_results.py  # 汇总生成 HTML 报告
```

结果保存在 `quick_test_results/`：
- `sync_*.json` - 同步测试
- `async_*.json` - 异步测试  
- `comparison_*.json` - 对比结果
- `comparison_report.html` - 可视化报告

---

## 常见问题

**缺少 httpx？** → `pip install httpx`  
**GPU 利用率低？** → 增大 `concurrent_requests` 到 16  
**Out of Memory？** → 降低并发数和批次大小  
**回退同步？** → 去掉 `--async` 参数

---

## 多次测试示例

```bash
# 测试不同并发数
python test_async_performance.py --mode async --concurrent 4
python test_async_performance.py --mode async --concurrent 8
python test_async_performance.py --mode async --concurrent 16

# 汇总对比
python compare_results.py
```

## 命令速查

```bash
# 快速测试
./quick_async_test.sh [sync|async|both]     # 默认 async

# 手动测试
python test_async_performance.py --mode async
python test_async_performance.py --mode sync
python test_async_performance.py --mode both

# 完整测试
python run_phase1.py --async --batch 1

# 查看结果
python compare_results.py
```
