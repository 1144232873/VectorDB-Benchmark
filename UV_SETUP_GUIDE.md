# UV 环境管理指南

本项目使用 [uv](https://github.com/astral-sh/uv) 作为Python包管理器，替代传统的 pip + venv。

## 为什么使用 uv？

- **极快速度**: 比 pip 快 10-100 倍
- **可靠性**: 确保依赖解析的一致性
- **简单**: 统一的工具链，无需 pip + venv + pip-tools
- **兼容性**: 完全兼容 pip，可以无缝迁移

## 安装 uv

### Linux / macOS (远程服务器)

```bash
# 使用官方安装脚本
curl -LsSf https://astral.sh/uv/install.sh | sh

# 加载环境变量
source $HOME/.cargo/env

# 验证安装
uv --version
```

### Windows (本地开发)

```powershell
# 使用 PowerShell
irm https://astral.sh/uv/install.ps1 | iex

# 验证安装
uv --version
```

### 使用 pip 安装 (备选)

```bash
pip install uv
```

## Phase 1: 向量生成测试环境

### 快速开始

```bash
cd ~/VectorDB-Benchmark/phase1_embedding

# 创建虚拟环境
uv venv

# 激活虚拟环境
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate  # Windows

# 安装项目及依赖
uv pip install -e .

# 验证安装
python -c "import openai; import h5py; print('✓ Dependencies OK')"
```

### 只安装运行时依赖

```bash
# 如果不需要开发工具，只安装运行时依赖
uv pip install -e . --no-dev
```

### 更新依赖

```bash
# 更新所有依赖到最新版本
uv pip install -e . --upgrade

# 更新特定包
uv pip install --upgrade openai h5py
```

## Phase 2: 向量搜索测试环境

```bash
cd ~/VectorDB-Benchmark/phase2_search

# 创建虚拟环境并安装依赖
uv venv
source .venv/bin/activate
uv pip install -e .

# 验证安装
python -c "import elasticsearch; import pymilvus; import qdrant_client; print('✓ DB clients OK')"
```

## 常用命令

### 创建虚拟环境

```bash
uv venv              # 创建 .venv 目录
uv venv myenv        # 创建自定义名称的环境
uv venv --python 3.11  # 指定Python版本
```

### 安装包

```bash
uv pip install package_name          # 安装单个包
uv pip install package1 package2     # 安装多个包
uv pip install "package>=1.0.0"      # 指定版本
uv pip install -e .                  # 安装当前项目（可编辑模式）
uv pip install -r requirements.txt   # 从requirements.txt安装
```

### 卸载包

```bash
uv pip uninstall package_name
```

### 列出已安装的包

```bash
uv pip list
uv pip list --format json
```

### 显示包信息

```bash
uv pip show package_name
```

### 冻结依赖

```bash
uv pip freeze > requirements.txt
```

## 完整工作流程

### 本地开发 (Windows)

```powershell
# 1. 克隆项目
cd D:\CodeWorkSpace\Temp\VectorDB-Benchmark

# 2. 创建Phase 1环境
cd phase1_embedding
uv venv
.venv\Scripts\activate
uv pip install -e .

# 3. 测试代码
python -m phase1_embedding.models.xinference_client
```

### 远程部署 (Linux)

```bash
# 1. SSH到远程
ssh -p 2222 root@192.168.1.51

# 2. 同步代码（在本地执行）
rsync -avz -e "ssh -p 2222" \
  --exclude '__pycache__' --exclude '.git' --exclude '.venv' \
  VectorDB-Benchmark/ root@192.168.1.51:~/VectorDB-Benchmark/

# 3. 远程设置环境
cd ~/VectorDB-Benchmark/phase1_embedding
uv venv
source .venv/bin/activate
uv pip install -e .

# 4. 运行测试
python run_phase1.py --config ../config/phase1_config.yaml
```

## 性能对比

### pip vs uv 安装速度

```bash
# pip (传统方式)
time pip install -r requirements.txt
# 约 60-120 秒

# uv (新方式)
time uv pip install -e .
# 约 5-10 秒 ⚡
```

### 依赖解析

uv 使用先进的依赖解析算法，确保：
- 快速解决依赖冲突
- 确定性的安装结果
- 更小的虚拟环境体积

## 故障排查

### uv 命令不存在

```bash
# 确保已加载环境变量
source $HOME/.cargo/env

# 或添加到 .bashrc
echo 'source $HOME/.cargo/env' >> ~/.bashrc
```

### Python版本问题

```bash
# 指定Python版本
uv venv --python 3.11

# 或使用系统Python
uv venv --python python3.11
```

### 依赖冲突

```bash
# 清除缓存重新安装
uv cache clean
uv pip install -e . --reinstall
```

### 网络问题

```bash
# 使用国内镜像（如果需要）
uv pip install -e . --index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

## 与 pip 对比

| 特性 | pip | uv |
|------|-----|-----|
| 安装速度 | 1x | 10-100x ⚡ |
| 依赖解析 | 慢 | 快 |
| 虚拟环境 | 需要 venv | 内置 |
| 缓存 | 基础 | 智能 |
| 并行下载 | 否 | 是 |
| 锁文件 | 需要额外工具 | 原生支持 |

## 迁移指南

### 从 pip 迁移到 uv

如果你之前使用 pip + requirements.txt：

```bash
# 1. 删除旧的虚拟环境
rm -rf venv/

# 2. 使用uv创建新环境
uv venv

# 3. 激活环境
source .venv/bin/activate

# 4. 安装依赖
uv pip install -e .  # 从 pyproject.toml
# 或
uv pip install -r requirements.txt  # 从旧的 requirements.txt
```

## 高级用法

### 锁定依赖版本

```bash
# 生成 uv.lock 文件
uv lock

# 从锁文件安装
uv sync
```

### 多Python版本管理

```bash
# Python 3.11
uv venv --python 3.11

# Python 3.12
uv venv venv312 --python 3.12
```

### CI/CD 集成

```yaml
# GitHub Actions 示例
- name: Install uv
  run: curl -LsSf https://astral.sh/uv/install.sh | sh

- name: Setup environment
  run: |
    source $HOME/.cargo/env
    uv venv
    source .venv/bin/activate
    uv pip install -e .
```

## 参考资源

- [uv 官方文档](https://github.com/astral-sh/uv)
- [pyproject.toml 规范](https://packaging.python.org/en/latest/specifications/pyproject-toml/)
- [Python 打包指南](https://packaging.python.org/)

---

**💡 提示**: uv 正在快速发展，建议定期更新到最新版本：
```bash
uv self update
```
