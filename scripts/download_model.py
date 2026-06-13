#!/usr/bin/env python3
"""模型权重下载与处理工具 - 入口脚本

使用方法:
    python scripts/download_model.py download <repo_id> <filename>
    python scripts/download_model.py validate <file_path> <repo_id> <filename>
    python scripts/download_model.py merge <base_model> <lora_adapter> <output>
    python scripts/download_model.py generate-modelfile <model_name> <base_model_path>
    python scripts/download_model.py all <repo_id> <filename> <base_model>

示例:
    # 下载 LoRA 权重
    python scripts/download_model.py download username/model adapter_model.safetensors

    # 完整流程
    python scripts/download_model.py all \
        username/model adapter_model.safetensors \
        ./models/base-model.gguf \
        --model-name my-custom-model
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from model_downloader.cli import app  # noqa: E402


def main():
    """入口函数"""
    app()


if __name__ == "__main__":
    main()
