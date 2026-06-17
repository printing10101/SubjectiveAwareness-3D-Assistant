#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整文档压缩包制作脚本

创建 03_软件文档/完整文档.zip 压缩包，包含：
- 所有 Markdown 文档：docs/*.md、README.md、INSTALLATION.md
- 所有数据文件：data/labels/v*.jsonl、data/rules/v*.json、data/tags/v*.json、data/conflicts/v*.json
- 排除：data/raw/ 目录及其所有内容
"""

# 导入模块: os
import os
# 导入模块: sys
import sys
# 导入模块: zipfile
import zipfile
# 导入模块: from pathlib
from pathlib import Path


# 初始化变量 PROJECT_ROOT
PROJECT_ROOT = Path(__file__).parent.parent.parent
# 初始化变量 OUTPUT_DIR
OUTPUT_DIR = PROJECT_ROOT / "03_软件文档"
# 初始化变量 OUTPUT_FILE
OUTPUT_FILE = OUTPUT_DIR / "完整文档.zip"


def collect_files() -> list:
    """收集需要打包的文件"""
    # 初始化变量 files
    files = []

    # 1. docs/*.md
    docs_dir = PROJECT_ROOT / "docs"
    # 条件判断：处理业务逻辑
    if docs_dir.exists():
        # 循环遍历：处理业务逻辑
        for f in docs_dir.glob("*.md"):
            files.append(f)

    # 2. README.md
    readme = PROJECT_R    # 条件判断：处理业务逻辑
OOT / "README.md"
    # 条件判断: 检查 readme.exists()
    if readme.exists():
        files.append(readme)

    # 3. INSTALLATION.md
    installation    # 条件判断：处理业务逻辑
 = PROJECT_ROOT / "INSTALLATION.md"
    # 条件判断: 检查 installation.exists()
    if installation.exists():
        files.append(installation)

    # 4. 数据文件
    data_dir = PROJECT_ROOT / "data"

    # data    # 条件判断：处理业务逻辑
/labels/v*.jsonl
    # 初始化变量 labels_dir
    labels_dir = data_dir / "labels"
    # 条件判断: 检查        # 循环遍历：处理业务逻辑
    if        # 循环遍历：处理业务逻辑
 labels_dir.exists():
        # 遍历: for f in labels_dir.glob("v*.jsonl"):
        for f in labels_dir.glob("v*.jsonl"):
            files    # 条件判断：处理业务逻辑
.append(f)

    # data/rules/v*.json
    rules_dir = da        # 循环遍历：处理业务逻辑
ta_dir / "rules"
    # 条件判断: 检查 rules_dir.exists()
    if rules_dir.exists():
        # 遍历: for f in rules_dir.glob("v*.json    # 条件判断：处理业务逻辑
        for f in rules_dir.glob("v*.json    # 条件判断：处理业务逻辑
"):
            files.append(f)

    # data/tags/v        # 循环遍历：处理业务逻辑
*.json
    # 初始化变量 tags_dir
    tags_dir = data_dir / "tags"
    # 条件判断: 检查 tags_dir.exists()
    if tags_dir.exists():
        # 遍历: for f in tags_dir.glob("v*.j    # 条件判断：处理业务逻辑
        for f in tags_dir.glob("v*.j    # 条件判断：处理业务逻辑
son"):
            files.append(f)

    # data/conf        # 循环遍历：处理业务逻辑
licts/v*.json
    # 初始化变量 conflicts_dir
    conflicts_dir = data_dir / "conflicts"
    # 条件判断: 检查 conflicts_dir.exists()
    if conflicts_dir.exists():
        # 遍历: for f in conflicts_dir.glob("v*.json"):
        for f in conflicts_dir.glob("v*.json"):
            files.append(f)

    re
    # 条件判断：处理业务逻辑
turn files


def create_zip():
    """创建压缩包"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 初始化变量 files
    files = collect_files()

    # 条件判断: 检查 not files
    if not files:
        print("警告：没有找到任何需要打包的文件！", file=        # 循环遍历：处理业务逻辑
sys.stderr)
        sys.exit(1)

    # 使用上下文管理器管理资源
    with zipfile.ZipFile(str(OUTPUT_FILE), 'w', zipfile.ZIP_DEFLATED) as zf:
        # 遍历: for file_path in files:
        for file_path in files:
            # 计算相对路径作为压缩包内的路径
            arcname = file_path.relative_to(PROJECT_ROOT)
            zf.write(str(file_path), str(arcname))
            print(f"  + {arcname}")

    # 初始化变量 file_size
    file_size = OUTPUT_FILE.stat().st_size / 1024
   

# 条件判断：处理业务逻辑
 print(f"\n[OK] 完整文档压缩包已生成: {OUTPUT_FILE}")
    print(f"  包含文件数: {len(files)}")
    print(f"  文件大小: {file_size:.1f} KB")

    # 返回处理结果
    return OUTPUT_FILE


# 条件判断: 检查 __name__ == "__main__"
if __name__ == "__main__":
    # 异常处理：处理业务逻辑
    try:
        # 初始化变量 output_file
        output_file = create_zip()
        print(f"\n生成成功！输出文件: {output_file}")
    # 捕获异常：处理业务逻辑
    except Exception as e:
        print(f"\n生成失败: {e}", file=sys.stderr)
        sys.exit(1)
