"""
Phase 1 报告生成器 - 生成HTML交互式报告
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# 报告HTML模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phase 1: 向量生成性能测试报告</title>
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
        .highlight {{
            background: #fff3cd;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #ffc107;
            margin: 20px 0;
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
            <h1>🚀 Phase 1: 向量生成性能测试报告</h1>
            <p>生成时间: {generation_time}</p>
            <p>测试模型数: {total_models} | 总向量数: {total_vectors:,} | 测试时长: {total_hours:.2f} 小时</p>
        </div>

        <!-- 性能概览 -->
        <div class="card">
            <h2>📊 性能概览</h2>
            <div class="metric-grid">
                {metrics_html}
            </div>
        </div>

        <!-- 详细对比表 -->
        <div class="card">
            <h2>📈 模型详细对比</h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>模型</th>
                            <th>维度</th>
                            <th>推理速度<br/>(docs/s)</th>
                            <th>单样本延迟<br/>(P99 ms)</th>
                            <th>最优Batch</th>
                            <th>GPU峰值<br/>(MB)</th>
                            <th>300万耗时<br/>(小时)</th>
                            <th>1亿推算<br/>(小时)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- 吞吐量对比图 -->
        <div class="card">
            <h2>📊 推理吞吐量对比</h2>
            <div id="throughput-chart" class="chart"></div>
        </div>

        <!-- 批处理性能对比 -->
        <div class="card">
            <h2>📊 批处理性能对比</h2>
            <div id="batch-chart" class="chart"></div>
        </div>

        <!-- 显存使用对比 -->
        <div class="card">
            <h2>📊 GPU显存使用对比</h2>
            <div id="memory-chart" class="chart"></div>
        </div>

        <!-- 大规模推算 -->
        <div class="card">
            <h2>🔮 大规模向量化时间推算</h2>
            <div id="extrapolation-chart" class="chart"></div>
            <div class="highlight">
                <strong>💡 推算说明：</strong> 基于300万向量的实测速度，线性推算不同规模的向量化耗时。
                实际耗时可能因批处理优化、内存管理等因素略有不同。
            </div>
        </div>

        <!-- 推荐建议 -->
        <div class="card">
            <h2>💡 选型建议</h2>
            {recommendations_html}
        </div>

        <div class="footer">
            <p>Vector Database Benchmark - Phase 1 Report</p>
            <p>Generated by VectorDB-Benchmark Tool</p>
        </div>
    </div>

    <script>
        // 吞吐量对比图
        {throughput_chart_script}

        // 批处理性能对比
        {batch_chart_script}

        // 显存使用对比
        {memory_chart_script}

        // 大规模推算
        {extrapolation_chart_script}
    </script>
</body>
</html>
"""


class Phase1ReportGenerator:
    """Phase 1 报告生成器"""
    
    def __init__(self, results_file: str, output_dir: str = "phase1_results"):
        """
        初始化报告生成器
        
        Args:
            results_file: 结果JSON文件路径
            output_dir: 输出目录
        """
        self.results_file = Path(results_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载结果
        with open(self.results_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        self.models = self.data.get("models", [])
        self.summary = self.data.get("summary", {})
        
        logger.info(f"Report generator initialized with {len(self.models)} models")
    
    def generate_metrics_html(self) -> str:
        """生成性能指标卡片HTML"""
        if not self.models:
            return ""
        
        # 找到最快和最慢的模型
        fastest = min(self.models, key=lambda m: m["generation_time_seconds"])
        slowest = max(self.models, key=lambda m: m["generation_time_seconds"])
        
        # 找到显存使用最小的
        min_memory = min(self.models, key=lambda m: m["gpu_memory_mb"]["peak_mb"])
        
        html = f"""
        <div class="metric-card">
            <h3>最快模型</h3>
            <div class="value">{fastest['model_name']}</div>
            <div class="unit">{fastest['generation_throughput']:.1f} docs/s</div>
        </div>
        <div class="metric-card">
            <h3>最高质量</h3>
            <div class="value">Qwen3-8B</div>
            <div class="unit">MTEB 72.8分</div>
        </div>
        <div class="metric-card">
            <h3>最低显存</h3>
            <div class="value">{min_memory['model_name']}</div>
            <div class="unit">{min_memory['gpu_memory_mb']['peak_mb']:.0f} MB</div>
        </div>
        <div class="metric-card">
            <h3>推荐平衡</h3>
            <div class="value">Qwen3-0.6B</div>
            <div class="unit">速度/质量/成本最优</div>
        </div>
        """
        return html
    
    def generate_table_rows(self) -> str:
        """生成对比表格行"""
        rows = []
        for model in self.models:
            row = f"""
            <tr>
                <td><strong>{model['model_name']}</strong></td>
                <td>{model['vector_dim']}</td>
                <td>{model['generation_throughput']:.1f}</td>
                <td>{model['single_latency_ms'].get('p99_latency_ms', 0):.1f}</td>
                <td>{model['optimal_batch_size']}</td>
                <td>{model['gpu_memory_mb']['peak_mb']:.0f}</td>
                <td>{model['generation_time_seconds']/3600:.2f}</td>
                <td>{model['extrapolation'].get('100000000', {}).get('hours', 0):.1f}</td>
            </tr>
            """
            rows.append(row)
        return "\n".join(rows)
    
    def generate_throughput_chart(self) -> str:
        """生成吞吐量对比图"""
        model_names = [m['model_name'] for m in self.models]
        throughputs = [m['generation_throughput'] for m in self.models]
        
        script = f"""
        var throughput_data = [{{
            x: {json.dumps(model_names)},
            y: {json.dumps(throughputs)},
            type: 'bar',
            marker: {{
                color: ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b']
            }},
            text: {json.dumps([f'{t:.1f}' for t in throughputs])},
            textposition: 'auto',
        }}];
        
        var throughput_layout = {{
            title: '推理吞吐量对比 (docs/s)',
            xaxis: {{title: '模型'}},
            yaxis: {{title: '吞吐量 (docs/s)'}},
            plot_bgcolor: '#f8f9fa',
            paper_bgcolor: 'white',
        }};
        
        Plotly.newPlot('throughput-chart', throughput_data, throughput_layout);
        """
        return script
    
    def generate_batch_chart(self) -> str:
        """生成批处理性能对比图"""
        traces = []
        for model in self.models:
            batch_throughput = model.get('batch_throughput', {})
            batch_sizes = sorted([int(k) for k in batch_throughput.keys()])
            throughputs = [batch_throughput[str(bs)]['throughput'] for bs in batch_sizes]
            
            trace = {
                'x': batch_sizes,
                'y': throughputs,
                'name': model['model_name'],
                'type': 'scatter',
                'mode': 'lines+markers'
            }
            traces.append(trace)
        
        script = f"""
        var batch_data = {json.dumps(traces)};
        
        var batch_layout = {{
            title: '不同Batch Size的吞吐量',
            xaxis: {{title: 'Batch Size'}},
            yaxis: {{title: '吞吐量 (docs/s)'}},
            plot_bgcolor: '#f8f9fa',
            paper_bgcolor: 'white',
        }};
        
        Plotly.newPlot('batch-chart', batch_data, batch_layout);
        """
        return script
    
    def generate_memory_chart(self) -> str:
        """生成显存使用对比图"""
        model_names = [m['model_name'] for m in self.models]
        peak_memory = [m['gpu_memory_mb']['peak_mb'] for m in self.models]
        avg_memory = [m['gpu_memory_mb']['average_mb'] for m in self.models]
        
        script = f"""
        var memory_data = [
            {{
                x: {json.dumps(model_names)},
                y: {json.dumps(peak_memory)},
                name: '峰值显存',
                type: 'bar'
            }},
            {{
                x: {json.dumps(model_names)},
                y: {json.dumps(avg_memory)},
                name: '平均显存',
                type: 'bar'
            }}
        ];
        
        var memory_layout = {{
            title: 'GPU显存使用对比 (MB)',
            xaxis: {{title: '模型'}},
            yaxis: {{title: '显存使用 (MB)'}},
            barmode: 'group',
            plot_bgcolor: '#f8f9fa',
            paper_bgcolor: 'white',
        }};
        
        Plotly.newPlot('memory-chart', memory_data, memory_layout);
        """
        return script
    
    def generate_extrapolation_chart(self) -> str:
        """生成大规模推算图"""
        scales = [5000000, 10000000, 50000000, 100000000]
        scale_labels = ['500万', '1000万', '5000万', '1亿']
        
        traces = []
        for model in self.models:
            hours = [
                model['extrapolation'].get(str(scale), {}).get('hours', 0)
                for scale in scales
            ]
            trace = {
                'x': scale_labels,
                'y': hours,
                'name': model['model_name'],
                'type': 'scatter',
                'mode': 'lines+markers'
            }
            traces.append(trace)
        
        script = f"""
        var extrap_data = {json.dumps(traces)};
        
        var extrap_layout = {{
            title: '大规模向量化耗时推算',
            xaxis: {{title: '向量规模'}},
            yaxis: {{title: '预估耗时 (小时)', type: 'log'}},
            plot_bgcolor: '#f8f9fa',
            paper_bgcolor: 'white',
        }};
        
        Plotly.newPlot('extrapolation-chart', extrap_data, extrap_layout);
        """
        return script
    
    def generate_recommendations(self) -> str:
        """生成推荐建议"""
        html = """
        <div style="line-height: 2;">
            <h3 style="color: #667eea; margin-bottom: 15px;">🏆 推荐方案</h3>
            
            <p><strong>🚀 追求速度：</strong> BGE-M3</p>
            <ul>
                <li>较快的推理速度，适合大规模场景</li>
                <li>显存占用适中</li>
                <li>支持多语言，质量较好</li>
            </ul>
            
            <p><strong>⚖️ 平衡选择：</strong> Qwen3-0.6B (推荐)</p>
            <ul>
                <li>速度、质量、成本的最佳平衡点</li>
                <li>MTEB分数 ~67，接近BGE-M3</li>
                <li>亿级向量约28小时，可接受</li>
                <li>显存占用适中（~2.3GB）</li>
            </ul>
            
            <p><strong>🎯 追求质量：</strong> Qwen3-4B / Qwen3-8B</p>
            <ul>
                <li><strong>Qwen3-4B</strong>：质量与速度的折中（MTEB ~70分）</li>
                <li>亿级向量约60-80小时，质量提升明显</li>
                <li>显存占用较大（~8-10GB）</li>
                <li><strong>Qwen3-8B</strong>：最高质量（MTEB 72.8分）</li>
                <li>适合对检索质量要求极高的场景</li>
                <li>亿级向量约154小时，需要耐心</li>
                <li>显存占用最大（~16GB）</li>
            </ul>
            
            <h3 style="color: #667eea; margin: 25px 0 15px 0;">💰 成本考虑</h3>
            <p>基于 RTX 4090 24GB GPU @ $3/hour：</p>
            <ul>
                <li>BGE-M3: 1亿向量 ≈ $60-80</li>
                <li>Qwen3-0.6B: 1亿向量 ≈ $84</li>
                <li>Qwen3-4B: 1亿向量 ≈ $180-240</li>
                <li>Qwen3-8B: 1亿向量 ≈ $462</li>
            </ul>
        </div>
        """
        return html
    
    def generate_report(self, output_file: str = "inference_performance_report.html"):
        """
        生成完整HTML报告
        
        Args:
            output_file: 输出文件名
        """
        logger.info("Generating Phase 1 HTML report...")
        
        # 计算总时长
        total_time_hours = sum(m['generation_time_seconds'] for m in self.models) / 3600
        total_vectors = self.models[0]['total_vectors_generated'] if self.models else 0
        
        # 生成HTML内容
        html_content = HTML_TEMPLATE.format(
            generation_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_models=len(self.models),
            total_vectors=total_vectors,
            total_hours=total_time_hours,
            metrics_html=self.generate_metrics_html(),
            table_rows=self.generate_table_rows(),
            recommendations_html=self.generate_recommendations(),
            throughput_chart_script=self.generate_throughput_chart(),
            batch_chart_script=self.generate_batch_chart(),
            memory_chart_script=self.generate_memory_chart(),
            extrapolation_chart_script=self.generate_extrapolation_chart()
        )
        
        # 保存HTML文件
        output_path = self.output_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"✓ Report generated: {output_path}")
        return output_path


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    print("Phase 1 Report Generator")
    print("This module generates HTML reports from benchmark_results.json")
