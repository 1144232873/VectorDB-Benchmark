#!/usr/bin/env python3
"""
测试结果对比工具

读取多个测试结果文件，生成对比报告和 HTML 可视化
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import argparse


def load_results(results_dir: str = "quick_test_results") -> Dict[str, List[Dict]]:
    """加载所有测试结果
    
    Returns:
        {"sync": [...], "async": [...], "comparison": [...]}
    """
    results_path = Path(results_dir)
    if not results_path.exists():
        print(f"⚠ 结果目录不存在: {results_dir}")
        return {"sync": [], "async": [], "comparison": []}
    
    results = {"sync": [], "async": [], "comparison": []}
    
    for json_file in results_path.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            mode = data.get("test_info", {}).get("mode", "unknown")
            if mode in results:
                results[mode].append(data)
        except Exception as e:
            print(f"⚠ 无法读取 {json_file}: {e}")
    
    # 按时间排序
    for mode in results:
        results[mode].sort(key=lambda x: x.get("test_info", {}).get("timestamp", ""))
    
    return results


def print_summary(results: Dict[str, List[Dict]]):
    """打印结果摘要"""
    print("\n" + "="*80)
    print("测试结果汇总")
    print("="*80)
    
    for mode in ["sync", "async", "comparison"]:
        mode_results = results.get(mode, [])
        if mode_results:
            print(f"\n{mode.upper()} 模式测试:")
            print(f"  共 {len(mode_results)} 次测试")
            
            for i, test in enumerate(mode_results, 1):
                test_info = test.get("test_info", {})
                test_results = test.get("results", {})
                
                timestamp = test_info.get("datetime", "unknown")
                model = test_info.get("model", "unknown")
                num_docs = test_info.get("num_docs", 0)
                
                print(f"\n  测试 {i}:")
                print(f"    时间: {timestamp}")
                print(f"    模型: {model}")
                print(f"    文档数: {num_docs}")
                
                if mode == "comparison":
                    comp = test_results.get("comparison", {})
                    print(f"    提升: {comp.get('speedup', 0):.2f}x")
                else:
                    throughput = test_results.get("throughput", 0)
                    time_cost = test_results.get("time", 0)
                    print(f"    吞吐量: {throughput:.2f} docs/s")
                    print(f"    耗时: {time_cost:.2f}s")


def generate_html_report(results: Dict[str, List[Dict]], output_file: str = "quick_test_results/comparison_report.html"):
    """生成 HTML 对比报告"""
    
    html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>性能测试对比报告</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .section {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .test-card {
            border: 1px solid #e0e0e0;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            background: #fafafa;
        }
        .metric {
            display: inline-block;
            margin: 10px 20px 10px 0;
        }
        .metric-label {
            color: #666;
            font-size: 0.9em;
        }
        .metric-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #333;
        }
        .speedup {
            color: #4caf50;
            font-weight: bold;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #667eea;
            color: white;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>⚡ Phase 1 性能测试对比报告</h1>
        <p>生成时间: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
    </div>
"""
    
    # 同步模式测试
    if results["sync"]:
        html_content += """
    <div class="section">
        <h2>🔵 同步模式测试</h2>
        <table>
            <tr>
                <th>测试时间</th>
                <th>模型</th>
                <th>文档数</th>
                <th>批次大小</th>
                <th>吞吐量 (docs/s)</th>
                <th>耗时 (s)</th>
            </tr>
"""
        for test in results["sync"]:
            info = test["test_info"]
            res = test["results"]
            html_content += f"""
            <tr>
                <td>{info.get('datetime', 'N/A')[:19]}</td>
                <td>{info.get('model', 'N/A')}</td>
                <td>{info.get('num_docs', 0)}</td>
                <td>{info.get('batch_size', 0)}</td>
                <td>{res.get('throughput', 0):.2f}</td>
                <td>{res.get('time', 0):.2f}</td>
            </tr>
"""
        html_content += """
        </table>
    </div>
"""
    
    # 异步模式测试
    if results["async"]:
        html_content += """
    <div class="section">
        <h2>🚀 异步模式测试</h2>
        <table>
            <tr>
                <th>测试时间</th>
                <th>模型</th>
                <th>文档数</th>
                <th>批次大小</th>
                <th>并发数</th>
                <th>吞吐量 (docs/s)</th>
                <th>耗时 (s)</th>
            </tr>
"""
        for test in results["async"]:
            info = test["test_info"]
            res = test["results"]
            html_content += f"""
            <tr>
                <td>{info.get('datetime', 'N/A')[:19]}</td>
                <td>{info.get('model', 'N/A')}</td>
                <td>{info.get('num_docs', 0)}</td>
                <td>{info.get('batch_size', 0)}</td>
                <td>{info.get('concurrent_requests', 'N/A')}</td>
                <td>{res.get('throughput', 0):.2f}</td>
                <td>{res.get('time', 0):.2f}</td>
            </tr>
"""
        html_content += """
        </table>
    </div>
"""
    
    # 对比测试
    if results["comparison"]:
        html_content += """
    <div class="section">
        <h2>📊 性能对比</h2>
        <table>
            <tr>
                <th>测试时间</th>
                <th>模型</th>
                <th>文档数</th>
                <th>同步吞吐量</th>
                <th>异步吞吐量</th>
                <th>提升倍数</th>
                <th>节省时间</th>
            </tr>
"""
        for test in results["comparison"]:
            info = test["test_info"]
            res = test["results"]
            sync_res = res.get("sync", {})
            async_res = res.get("async", {})
            comp = res.get("comparison", {})
            
            html_content += f"""
            <tr>
                <td>{info.get('datetime', 'N/A')[:19]}</td>
                <td>{info.get('model', 'N/A')}</td>
                <td>{info.get('num_docs', 0)}</td>
                <td>{sync_res.get('throughput', 0):.2f} docs/s</td>
                <td>{async_res.get('throughput', 0):.2f} docs/s</td>
                <td class="speedup">{comp.get('speedup', 0):.2f}x</td>
                <td>{comp.get('time_saved_percent', 0):.1f}%</td>
            </tr>
"""
        html_content += """
        </table>
    </div>
"""
    
    html_content += """
</body>
</html>
"""
    
    # 保存 HTML
    output_path = Path(output_file)
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✓ HTML 报告已生成: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="测试结果对比工具")
    parser.add_argument(
        "--results-dir",
        type=str,
        default="quick_test_results",
        help="结果目录路径"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="quick_test_results/comparison_report.html",
        help="HTML 报告输出路径"
    )
    parser.add_argument(
        "--no-html",
        action="store_true",
        help="不生成 HTML 报告"
    )
    
    args = parser.parse_args()
    
    # 加载结果
    results = load_results(args.results_dir)
    
    total_tests = sum(len(results[mode]) for mode in results)
    if total_tests == 0:
        print(f"⚠ 未找到测试结果文件")
        print(f"   结果目录: {args.results_dir}")
        print(f"   请先运行测试: python test_async_performance.py")
        return 1
    
    # 打印摘要
    print_summary(results)
    
    # 生成 HTML
    if not args.no_html:
        generate_html_report(results, args.output)
    
    print("\n" + "="*80)
    print("✓ 完成")
    print("="*80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
