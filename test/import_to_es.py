#!/usr/bin/env python3
"""
将 results/vectors/bulk_import.json 流式导入到 Elasticsearch。
按批提交，不将整个文件载入内存，避免 curl --data-binary 的 OOM。
"""

import argparse
import logging
import sys
from pathlib import Path

import yaml

from es_exporter import ESExporter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(
        description="将 bulk_import.json 流式导入到 Elasticsearch（避免大文件 OOM）"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="配置文件路径",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="bulk 文件路径，默认使用 config 中的 results/vectors/bulk_import.json",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="每批提交的文档数（默认 500）",
    )
    parser.add_argument(
        "--index",
        type=str,
        default=None,
        help="覆盖配置文件中的索引名",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    es_cfg = config.get("elasticsearch", {})
    host = es_cfg.get("host", "localhost")
    port = int(es_cfg.get("port", 9200))
    index_name = args.index or es_cfg.get("index_name", "pdf_vectors")
    bulk_size = es_cfg.get("bulk_size", 5000)

    bulk_file = args.file
    if bulk_file is None:
        out_cfg = config.get("output", {})
        vectors_dir = Path(out_cfg.get("vectors_dir", "results/vectors"))
        bulk_file = vectors_dir / "bulk_import.json"

    bulk_file = bulk_file.resolve()
    if not bulk_file.exists():
        logger.error("Bulk 文件不存在: %s", bulk_file)
        sys.exit(1)

    exporter = ESExporter(index_name=index_name, bulk_size=bulk_size)
    result = exporter.import_bulk_file_to_es(
        bulk_file=bulk_file,
        host=host,
        port=port,
        index_name_override=args.index,
        chunk_size=args.chunk_size,
        show_progress=True,
    )
    logger.info("导入结果: %s", result)


if __name__ == "__main__":
    main()
