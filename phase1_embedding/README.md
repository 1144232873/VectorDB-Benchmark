# Phase 1: 向量生成性能测试

## 快速使用

### 1. 安装依赖
```bash
pip install httpx aiofiles tqdm
```

### 2. 快速测试（推荐）
```bash
# 一键测试脚本
./quick_async_test.sh          # Linux/Mac  
quick_async_test.bat            # Windows

# 或手动指定模式
./quick_async_test.sh async     # 仅异步
./quick_async_test.sh sync      # 仅同步
./quick_async_test.sh both      # 对比
```

### 3. 完整基准测试
```bash
# 🚀 异步高性能模式（推荐）
python run_phase1.py --async --batch 1

# 标准同步模式
python run_phase1.py --batch 1

# 查看所有批次
python run_phase1.py --list-batches
```

### 4. 查看结果
```bash
# 汇总历史测试结果
python compare_results.py

# 查看 HTML 报告
open quick_test_results/comparison_report.html
```

## 核心文件

| 文件 | 说明 |
|------|------|
| `run_phase1.py` | 主程序（支持 --async） |
| `test_async_performance.py` | 快速测试工具 |
| `compare_results.py` | 结果汇总工具 |
| `quick_async_test.sh/.bat` | 一键测试脚本 |

## 性能对比

| 模式 | GPU 利用率 | 吞吐量 |
|------|-----------|--------|
| 同步 | 20-50% | 1x（基准） |
| 异步 | 80-95% | **6-10x** |

## 详细文档

- **完整指南**：[README_ASYNC_OPTIMIZATION.md](../README_ASYNC_OPTIMIZATION.md)
- **配置文件**：[phase1_config.yaml](../config/phase1_config.yaml)

## 命令参考

```bash
# 测试命令
python test_async_performance.py --mode async
python test_async_performance.py --mode sync  
python test_async_performance.py --mode both

# 完整测试
python run_phase1.py --async --batch 1
python run_phase1.py --async --async-preset aggressive

# 结果管理
python compare_results.py
```
