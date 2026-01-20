# 远程环境设置指南

## 1. SSH 配置

### Windows 配置

在 `C:\Users\11442\.ssh\config` 添加以下内容：

```
Host benchmark
    HostName 192.168.1.51
    Port 2222
    User root
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

### 测试连接

```bash
ssh benchmark "echo 'Connection successful!'"
```

## 2. 同步代码到远程

### 使用 rsync (推荐)

```bash
# 在项目根目录执行
cd D:\CodeWorkSpace\Temp\VectorDB-Benchmark

# 同步到远程
rsync -avz --exclude '__pycache__' --exclude '.git' --exclude '*.pyc' --exclude 'venv' --exclude 'vector_cache' --exclude 'logs' -e "ssh -p 2222" ./ root@192.168.1.51:~/VectorDB-Benchmark/
```

### 使用 scp (备选)

```bash
scp -P 2222 -r D:\CodeWorkSpace\Temp\VectorDB-Benchmark root@192.168.1.51:~/
```

## 3. 远程环境验证

```bash
ssh benchmark

# 验证 Xinference
curl http://localhost:9997/v1/models

# 验证 Docker
docker ps
docker --version

# 验证 NVIDIA
nvidia-smi

# 验证 Python
python3.11 --version

# 验证磁盘空间
df -h
```

## 4. 初始化远程环境

```bash
ssh benchmark
cd ~/VectorDB-Benchmark

# 创建目录
mkdir -p logs vector_cache phase1_results phase2_results data

# 安装uv (如果还没安装)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# 验证uv安装
uv --version
```

## 5. 快速检查清单

- [ ] SSH配置完成，可以通过 `ssh benchmark` 连接
- [ ] 代码已同步到远程 `~/VectorDB-Benchmark/`
- [ ] uv 已安装 (uv --version)
- [ ] Xinference 在端口 9997 运行
- [ ] Docker 正常运行
- [ ] GPU 可用 (nvidia-smi 显示 RTX 4090)
- [ ] 磁盘有 1TB 可用空间
- [ ] Python 3.11 可用

## 6. 常用命令

### 查看运行中的任务

```bash
screen -ls
screen -r phase1
screen -r phase2a
screen -r phase2b
```

### 查看日志

```bash
tail -f ~/VectorDB-Benchmark/logs/phase1.log
tail -f ~/VectorDB-Benchmark/logs/phase2a.log
```

### 监控资源

```bash
watch -n 1 nvidia-smi
htop
df -h
```

### 下载结果到本地

```bash
# 下载报告
scp -P 2222 root@192.168.1.51:~/VectorDB-Benchmark/phase1_results/*.html ./reports/

# 或使用端口转发查看
ssh -p 2222 -L 8080:localhost:8080 root@192.168.1.51
# 然后在远程执行: cd ~/VectorDB-Benchmark/phase1_results && python3 -m http.server 8080
# 本地浏览器访问: http://localhost:8080
```
