"""
HTML报告生成器
生成包含测试速度和token评估的HTML性能报告
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# HTML报告模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF向量化测试报告</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header p {{
            font-size: 1.1em;
            opacity: 0.95;
        }}
        .card {{
            background: white;
            padding: 30px;
            margin-bottom: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .metric-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .metric-card h3 {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 10px;
        }}
        .metric-card .value {{
            font-size: 2em;
            font-weight: 700;
            color: #667eea;
        }}
        .metric-card .unit {{
            font-size: 0.8em;
            color: #999;
        }}
        .chart {{
            margin: 30px 0;
        }}
        .info-box {{
            background: #e7f3ff;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #2196F3;
            margin: 20px 0;
        }}
        .table-container {{
            overflow-x: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #667eea;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📄 PDF向量化测试报告</h1>
            <p>生成时间: {generation_time}</p>
            <p>模型: {model_name} | 总文档数: {total_docs:,} | 总向量数: {total_vectors:,}</p>
        </div>

        <!-- 性能概览 -->
        <div class="card">
            <h2>📊 性能概览</h2>
            <div class="metric-grid">
                {metrics_html}
            </div>
        </div>

        <!-- 速度指标 -->
        <div class="card">
            <h2>⚡ 速度指标</h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>指标</th>
                            <th>数值</th>
                            <th>单位</th>
                        </tr>
                    </thead>
                    <tbody>
                        {speed_table_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Token统计 -->
        <div class="card">
            <h2>🔤 Token统计</h2>
            <div class="metric-grid">
                {token_metrics_html}
            </div>
            <div id="token-chart" class="chart"></div>
        </div>

        <!-- 处理时间分布 -->
        <div class="card">
            <h2>⏱️ 处理时间分布</h2>
            <div id="time-chart" class="chart"></div>
        </div>

        <!-- ES导入信息 -->
        <div class="card">
            <h2>📦 Elasticsearch导入信息</h2>
            <div class="info-box">
                <p><strong>索引名称:</strong> {index_name}</p>
                <p><strong>向量文件路径:</strong> {vectors_file}</p>
                <p><strong>文档数量:</strong> {total_docs:,}</p>
                <p><strong>向量维度:</strong> {vector_dim}</p>
                <p><strong>导入命令:</strong></p>
                <pre style="background: #f5f5f5; padding: 10px; border-radius: 5px; margin-top: 10px;">curl -X POST '{es_host}:{es_port}/_bulk' -H 'Content-Type: application/x-ndjson' --data-binary @{vectors_file}</pre>
            </div>
        </div>

        <div class="footer">
            <p>PDF Vectorization Benchmark Report</p>
            <p>Generated by VectorDB-Benchmark Tool</p>
        </div>
    </div>

    <script>
        // Token统计图表
        {token_chart_script}

        // 处理时间分布图表
        {time_chart_script}
    </script>
</body>
</html>
"""


class ReportGenerator:
    """PDF向量化测试报告生成器"""
    
    def __init__(self, output_dir: str = "results"):
        """
        初始化报告生成器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_metrics_html(self, stats: Dict[str, Any]) -> str:
        """生成性能指标卡片HTML"""
        html = f"""
        <div class="metric-card">
            <h3>总处理时间</h3>
            <div class="value">{stats.get('total_time_seconds', 0):.2f}</div>
            <div class="unit">秒</div>
        </div>
        <div class="metric-card">
            <h3>文档处理速度</h3>
            <div class="value">{stats.get('docs_per_second', 0):.1f}</div>
            <div class="unit">docs/s</div>
        </div>
        <div class="metric-card">
            <h3>向量生成速度</h3>
            <div class="value">{stats.get('vectors_per_second', 0):.1f}</div>
            <div class="unit">vectors/s</div>
        </div>
        <div class="metric-card">
            <h3>Token处理速度</h3>
            <div class="value">{stats.get('tokens_per_second', 0):.1f}</div>
            <div class="unit">tokens/s</div>
        </div>
        """
        return html
    
    def generate_speed_table_rows(self, stats: Dict[str, Any]) -> str:
        """生成速度指标表格行"""
        rows = [
            ("PDF提取时间", f"{stats.get('pdf_extraction_time', 0):.2f}", "秒"),
            ("数据扩展时间", f"{stats.get('expansion_time', 0):.2f}", "秒"),
            ("Token统计时间", f"{stats.get('token_count_time', 0):.2f}", "秒"),
            ("向量化时间", f"{stats.get('vectorization_time', 0):.2f}", "秒"),
            ("ES导出时间", f"{stats.get('export_time', 0):.2f}", "秒"),
            ("总处理时间", f"{stats.get('total_time_seconds', 0):.2f}", "秒"),
            ("文档处理速度", f"{stats.get('docs_per_second', 0):.2f}", "docs/s"),
            ("向量生成速度", f"{stats.get('vectors_per_second', 0):.2f}", "vectors/s"),
            ("Token处理速度", f"{stats.get('tokens_per_second', 0):.2f}", "tokens/s"),
        ]
        
        html_rows = []
        for label, value, unit in rows:
            html_rows.append(f"""
            <tr>
                <td><strong>{label}</strong></td>
                <td>{value}</td>
                <td>{unit}</td>
            </tr>
            """)
        
        return "\n".join(html_rows)
    
    def generate_token_metrics_html(self, stats: Dict[str, Any]) -> str:
        """生成Token统计指标卡片"""
        html = f"""
        <div class="metric-card">
            <h3>总Token数</h3>
            <div class="value">{stats.get('total_tokens', 0):,}</div>
            <div class="unit">tokens</div>
        </div>
        <div class="metric-card">
            <h3>平均每文档Token数</h3>
            <div class="value">{stats.get('avg_tokens_per_doc', 0):.1f}</div>
            <div class="unit">tokens/doc</div>
        </div>
        <div class="metric-card">
            <h3>Token计数速度</h3>
            <div class="value">{stats.get('token_count_speed', 0):.1f}</div>
            <div class="unit">tokens/s</div>
        </div>
        <div class="metric-card">
            <h3>Token吞吐量</h3>
            <div class="value">{stats.get('token_throughput', 0):.1f}</div>
            <div class="unit">tokens/s</div>
        </div>
        """
        return html
    
    def generate_token_chart(self, stats: Dict[str, Any]) -> str:
        """生成Token统计图表"""
        total_tokens = stats.get('total_tokens', 0)
        avg_tokens = stats.get('avg_tokens_per_doc', 0)
        token_count_speed = stats.get('token_count_speed', 0)
        token_throughput = stats.get('token_throughput', 0)
        
        script = f"""
        var token_data = [{{
            x: ['总Token数', '平均每文档Token数', 'Token计数速度', 'Token吞吐量'],
            y: [{total_tokens}, {avg_tokens}, {token_count_speed}, {token_throughput}],
            type: 'bar',
            marker: {{
                color: ['#667eea', '#764ba2', '#f093fb', '#4facfe']
            }},
            text: [{total_tokens}, {avg_tokens:.1f}, {token_count_speed:.1f}, {token_throughput:.1f}],
            textposition: 'auto',
        }}];
        
        var token_layout = {{
            title: 'Token统计对比',
            xaxis: {{title: '指标'}},
            yaxis: {{title: '数值'}},
            plot_bgcolor: '#f8f9fa',
            paper_bgcolor: 'white',
        }};
        
        Plotly.newPlot('token-chart', token_data, token_layout);
        """
        return script
    
    def generate_time_chart(self, stats: Dict[str, Any]) -> str:
        """生成处理时间分布图表"""
        times = {
            'PDF提取': stats.get('pdf_extraction_time', 0),
            '数据扩展': stats.get('expansion_time', 0),
            'Token统计': stats.get('token_count_time', 0),
            '向量化': stats.get('vectorization_time', 0),
            'ES导出': stats.get('export_time', 0),
        }
        
        labels = list(times.keys())
        values = list(times.values())
        
        script = f"""
        var time_data = [{{
            labels: {json.dumps(labels)},
            values: {json.dumps(values)},
            type: 'pie',
            marker: {{
                colors: ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b']
            }},
            textinfo: 'label+percent',
            textposition: 'outside'
        }}];
        
        var time_layout = {{
            title: '处理时间分布',
            plot_bgcolor: '#f8f9fa',
            paper_bgcolor: 'white',
        }};
        
        Plotly.newPlot('time-chart', time_data, time_layout);
        """
        return script
    
    def generate_report(
        self,
        stats: Dict[str, Any],
        config: Dict[str, Any],
        output_file: str = "report.html"
    ) -> Path:
        """
        生成完整HTML报告
        
        Args:
            stats: 统计信息字典
            config: 配置信息字典
            output_file: 输出文件名
            
        Returns:
            输出文件路径
        """
        logger.info("Generating HTML report...")
        
        # 准备数据
        model_name = config.get('model', {}).get('name', 'unknown')
        index_name = config.get('elasticsearch', {}).get('index_name', 'pdf_vectors')
        es_host = config.get('elasticsearch', {}).get('host', 'localhost')
        es_port = config.get('elasticsearch', {}).get('port', 9200)
        vector_dim = config.get('model', {}).get('dimensions', 1024)
        vectors_file = config.get('output', {}).get('vectors_file', 'results/vectors/bulk_import.json')
        
        total_docs = stats.get('total_documents', 0)
        total_vectors = stats.get('total_vectors', total_docs)
        
        # 生成HTML内容
        html_content = HTML_TEMPLATE.format(
            generation_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            model_name=model_name,
            total_docs=total_docs,
            total_vectors=total_vectors,
            metrics_html=self.generate_metrics_html(stats),
            speed_table_rows=self.generate_speed_table_rows(stats),
            token_metrics_html=self.generate_token_metrics_html(stats),
            token_chart_script=self.generate_token_chart(stats),
            time_chart_script=self.generate_time_chart(stats),
            index_name=index_name,
            vectors_file=vectors_file,
            vector_dim=vector_dim,
            es_host=es_host,
            es_port=es_port
        )
        
        # 保存HTML文件：若 output_file 已包含 output_dir 前缀（如 "results/report.html"），
        # 则直接使用该路径，避免 self.output_dir / output_file 产生 results/results/report.html
        output_dir_str = str(self.output_dir)
        if output_file.startswith(output_dir_str + '/') or output_file.startswith(output_dir_str + '\\'):
            output_path = Path(output_file)
        else:
            output_path = self.output_dir / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"✓ Report generated: {output_path}")
        return output_path


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    generator = ReportGenerator()
    
    # 测试数据
    test_stats = {
        'total_documents': 100000,
        'total_vectors': 100000,
        'total_time_seconds': 3600,
        'pdf_extraction_time': 100,
        'expansion_time': 50,
        'token_count_time': 200,
        'vectorization_time': 3000,
        'export_time': 250,
        'docs_per_second': 27.78,
        'vectors_per_second': 27.78,
        'total_tokens': 5000000,
        'avg_tokens_per_doc': 50.0,
        'token_count_speed': 25000.0,
        'token_throughput': 1388.89,
        'tokens_per_second': 1388.89
    }
    
    test_config = {
        'model': {'name': 'qwen3-0.6b', 'dimensions': 1024},
        'elasticsearch': {'index_name': 'pdf_vectors', 'host': 'localhost', 'port': 9200},
        'output': {'vectors_file': 'results/vectors/bulk_import.json'}
    }
    
    generator.generate_report(test_stats, test_config, "test_report.html")
    print("\n测试报告已生成: test_report.html")
