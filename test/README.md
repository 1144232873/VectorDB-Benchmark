# PDF向量化测试脚本

在test目录下运行的PDF向量化测试工具，支持将PDF文档向量化并导出为Elasticsearch格式。

## 功能特性

- ✅ PDF文本提取（支持批量处理）
- ✅ 数据扩展（重复/模糊处理，扩展到10万级别）
- ✅ Token统计（支持tiktoken和transformers）
- ✅ 异步向量化（使用项目最佳性能策略：16并发、自动batch调优）
- ✅ ES格式导出（Bulk API格式，可直接导入）
- ✅ HTML性能报告（包含测试速度和token评估）

## 快速开始

### 1. 安装依赖

**方式一：使用 uv（推荐）**

```bash
cd test

# 创建虚拟环境并安装依赖（一步到位）
uv venv
uv sync

# 激活环境后运行（Windows PowerShell）
.venv\Scripts\Activate.ps1
# 或 Windows CMD
.venv\Scripts\activate.bat
# 或 Linux/macOS
source .venv/bin/activate

python pdf_vectorize.py --config config.yaml
```

**方式二：仅用 uv 安装依赖到当前环境**

```bash
cd test
uv pip install -r requirements.txt
```

**方式三：传统 pip**

```bash
cd test
pip install -r requirements.txt
```

### 2. 配置

编辑 `config.yaml`，设置：
- Xinference服务地址和端口
- Elasticsearch连接信息（如果需要导入）
- 目标文档数量（默认10万）
- 其他参数

### 3. 运行

```bash
python pdf_vectorize.py --config config.yaml
```

### 4. 查看结果

- 向量文件：`results/vectors/bulk_import.json`
- HTML报告：`results/report.html`

## 配置文件说明

### Xinference配置
```yaml
xinference:
  host: "192.168.1.51"  # Xinference服务器地址
  port: 9997            # Xinference服务器端口
  timeout: 300
```

### 模型配置
```yaml
model:
  name: "qwen3-0.6b"
  model_name: "Qwen3-Embedding-0.6B"  # Xinference中的实际模型ID
  dimensions: 1024
```

### PDF处理配置
```yaml
pdf:
  input_dir: "向量测试文档"  # PDF文件目录
  chunk_size: 512            # 文本分块大小
  min_length: 10
  max_length: 512
```

### 数据扩展配置
```yaml
expansion:
  target_count: 100000  # 目标文档数
  strategy: "repeat"    # "repeat" 或 "fuzzy"
```

### 性能配置
```yaml
performance:
  max_concurrent_requests: 16  # 最大并发请求数
  auto_tune_batch_size: true   # 自动调优batch size
  max_batch_size: 2048
```

## 输出文件

### 1. ES批量导入文件
`results/vectors/bulk_import.json`

格式：ES Bulk API格式（NDJSON）
```json
{"index": {"_index": "pdf_vectors", "_id": "doc_1"}}
{"text": "...", "vector": [...], "source_file": "xxx.pdf", "chunk_id": 1}
```

**导入前需先创建索引并设置 mapping**（见下方「Elasticsearch 索引 Mapping」），再执行 bulk 导入。

**推荐：用脚本流式导入（大文件不会 OOM）**

```bash
# 按 config.yaml 中的 ES 地址和索引名，流式导入（分批提交，不占大内存）
python import_to_es.py --config config.yaml

# 指定 bulk 文件和每批条数
python import_to_es.py --file results/vectors/bulk_import.json --chunk-size 500
```

若 bulk 文件很大（如 10 万条），不要用 `curl --data-binary`，会整文件进内存导致 OOM；用上面脚本即可。

**小文件可用 curl（不推荐大文件）**

```bash
curl -X POST 'localhost:9200/_bulk' \
  -H 'Content-Type: application/x-ndjson' \
  --data-binary @results/vectors/bulk_import.json
```

### Elasticsearch 索引 Mapping

`pdf_vectors` 索引入口文档结构与对应 mapping 如下（与 `config.yaml` 中 `model.dimensions`、`elasticsearch.index_name` 一致）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | `text` | 分块文本，支持全文检索 |
| `vector` | `dense_vector` | 向量，维度需与配置中 `dimensions`（如 1024）一致，用于 kNN 检索 |
| `source_file` | `keyword` | 来源 PDF 文件名 |
| `chunk_id` | `integer` | 分块序号 |
| `repeat_id` | `integer` | 扩展时的重复副本序号（可选） |

**创建索引（先执行，再 bulk 导入）：**

```bash
# 若已存在旧索引可先删除（慎用）：curl -X DELETE 'localhost:9200/pdf_vectors'
curl -X PUT 'localhost:9200/pdf_vectors' \
  -H 'Content-Type: application/json' \
  -d @es_pdf_vectors_mapping.json
```

mapping 文件：`test/es_pdf_vectors_mapping.json`。若模型维度不是 1024，请修改该文件中 `vector.dims` 与配置一致。

### 2. HTML报告
`results/report.html`

包含：
- 性能概览（处理时间、速度指标）
- Token统计（总数、平均值、处理速度）
- 处理时间分布图
- ES导入信息

## 性能优化

脚本使用了项目的最佳性能策略：

1. **异步并发**：16个并发请求同时发送
2. **自动batch调优**：自动寻找最优batch size（最大2048）
3. **HTTP/2**：启用HTTP/2提升性能
4. **连接池**：复用连接减少开销

## 数据扩展策略

当PDF文档数量较少时，脚本会自动扩展到目标数量（默认10万）：

- **repeat策略**：简单重复原始文档，添加序号后缀
- **fuzzy策略**：对文本进行轻微变换（添加前缀等）

## Token统计

支持两种tokenizer：
1. **tiktoken**（推荐）：快速、轻量
2. **transformers**：如果tiktoken不可用，自动回退

统计指标：
- 总token数
- 平均每文档token数
- Token计数速度（tokens/s）
- Token吞吐量（tokens/s）

## 故障排除

### 1. 连接Xinference失败
- 检查Xinference服务是否运行
- 检查网络连接
- 确认host和port配置正确

### 2. Token统计失败
- 安装tiktoken：`pip install tiktoken`
- 或安装transformers：`pip install transformers`

### 3. PDF提取失败
- 检查PDF文件是否损坏
- 确认pdfplumber已安装：`pip install pdfplumber`
- 某些PDF可能需要OCR（当前不支持）

### 4. 内存不足
- 减少batch_size
- 减少max_concurrent_requests
- 分批处理PDF文件

## 文件结构

```
test/
├── pdf_vectorize.py      # 主脚本
├── pdf_reader.py         # PDF文本提取
├── es_exporter.py        # ES导出
├── report_generator.py   # HTML报告生成
├── async_client.py       # 异步Xinference客户端
├── config.yaml           # 配置文件
├── requirements.txt      # 依赖文件
├── README.md             # 本文件
└── results/              # 输出目录
    ├── vectors/          # 向量文件
    └── report.html       # HTML报告
```

## uv 环境管理

本目录支持用 [uv](https://github.com/astral-sh/uv) 管理虚拟环境和依赖。

| 命令 | 说明 |
|------|------|
| `uv venv` | 在当前目录创建 `.venv` 虚拟环境 |
| `uv sync` | 按 `pyproject.toml` 安装/锁定依赖（推荐） |
| `uv pip install -r requirements.txt` | 按 `requirements.txt` 安装依赖 |
| `uv add 包名` | 添加依赖并更新 `pyproject.toml` |
| `uv remove 包名` | 移除依赖 |

**推荐流程：**

```bash
cd test
uv venv
uv sync
# Windows 激活
.venv\Scripts\Activate.ps1
# 运行脚本
python pdf_vectorize.py --config config.yaml
```

依赖定义在两处任选其一即可：
- **pyproject.toml**：用 `uv sync` 安装（版本锁定更清晰）
- **requirements.txt**：用 `uv pip install -r requirements.txt` 安装

## 注意事项

1. 确保Xinference服务正在运行
2. PDF文件放在`向量测试文档/`目录下
3. 首次运行可能需要较长时间（向量化10万文档）
4. ES导入文件可能很大（取决于向量维度和文档数）

## 许可证

与主项目保持一致。
