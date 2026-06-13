#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整文档压缩包制作脚本

创建 03_软件文档/完整文档.zip 压缩包，包含：
- 所有 Markdown 文档：docs/*.md、README.md、INSTALLATION.md
- 所有数据文件：data/labels/v*.jsonl、data/rules/v*.json、data/tags/v*.json、data/conflicts/v*.json
- 排除：data/raw/ 目录及其所有内容
"""

import os
import sys
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "03_软件文档"
OUTPUT_FILE = OUTPUT_DIR / "完整文档.zip"


def collect_files() -> list:
    """收集需要打包的文件"""
    files = []

    # 1. docs/*.md
    docs_dir = PROJECT_ROOT / "docs"
    if docs_dir.exists():
        for f in docs_dir.glob("*.md"):
            files.append(f)

    # 2. README.md
    readme = PROJECT_ROOT / "README.md"
    if readme.exists():
        files.append(readme)

    # 3. INSTALLATION.md
    installation = PROJECT_ROOT / "INSTALLATION.md"
    if installation.exists():
        files.append(installation)

    # 4. 数据文件
    data_dir = PROJECT_ROOT / "data"

    # data/labels/v*.jsonl
    labels_dir = data_dir / "labels"
    if labels_dir.exists():
        for f in labels_dir.glob("v*.jsonl"):
            files.append(f)

    # data/rules/v*.json
    rules_dir = data_dir / "rules"
    if rules_dir.exists():
        for f in rules_dir.glob("v*.json"):
            files.append(f)

    # data/tags/v*.json
    tags_dir = data_dir / "tags"
    if tags_dir.exists():
        for f in tags_dir.glob("v*.json"):
            files.append(f)

    # data/conflicts/v*.json
    conflicts_dir = data_dir / "conflicts"
    if conflicts_dir.exists():
        for f in conflicts_dir.glob("v*.json"):
            files.append(f)

    return files


def create_zip():
    """创建压缩包"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    files = collect_files()

    if not files:
        print("警告：没有找到任何需要打包的文件！", file=sys.stderr)
        sys.exit(1)

    with zipfile.ZipFile(str(OUTPUT_FILE), 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            # 计算相对路径作为压缩包内的路径
            arcname = file_path.relative_to(PROJECT_ROOT)
            zf.write(str(file_path), str(arcname))
            print(f"  + {arcname}")

    file_size = OUTPUT_FILE.stat().st_size / 1024
    print(f"\n[OK] 完整文档压缩包已生成: {OUTPUT_FILE}")
    print(f"  包含文件数: {len(files)}")
    print(f"  文件大小: {file_size:.1f} KB")

    return OUTPUT_FILE


if __name__ == "__main__":
    try:
        output_file = create_zip()
        print(f"\n生成成功！输出文件: {output_file}")
    except Exception as e:
        print(f"\n生成失败: {e}", file=sys.stderr)
        sys.exit(1)
