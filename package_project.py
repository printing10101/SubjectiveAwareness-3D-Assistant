#!/usr/bin/env python3
"""项目打包脚本：清理并生成标准ZIP压缩包，验证完整性并生成校验和"""

import hashlib
import os
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\Lenovo\Desktop\微信程序开发")
OUTPUT_DIR = PROJECT_ROOT
ZIP_NAME = "legal_judgment_analysis_system.zip"
SHA256_NAME = ZIP_NAME + ".sha256"

EXCLUDE_PATTERNS = {
    # 虚拟环境
    ".venv",
    # Python 缓存
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".cache",
    "*.pyc",
    "*.pyo",
    # 依赖目录
    "node_modules",
    # 环境变量
    ".env",
    # 日志文件
    "logs",
    "*.log",
    # 数据库文件
    "*.db",
    # IDE 配置文件
    ".vscode",
    ".idea",
    ".vs",
    "*.sublime-project",
    "*.sublime-workspace",
    # 操作系统文件
    "Thumbs.db",
    ".DS_Store",
    # 编译缓存
    "unsloth_compiled_cache",
    # 临时文件
    "*.tmp",
    "*.temp",
    "ruff_issues.txt",
    "pyright_output.txt",
    # Git
    ".git",
    ".gitignore",
}


def is_excluded(name: str, rel: str) -> bool:
    if name in EXCLUDE_PATTERNS:
        return True

    for pattern in EXCLUDE_PATTERNS:
        if pattern.startswith("*.") and name.endswith(pattern[1:]):
            return True

    # 排除特定路径
    specific_excludes = [
        "backend/.env",
        "backend/ruff_issues.txt",
        "backend/logs",
        "backend/app.db",
        "backend/test.db",
    ]
    for exc in specific_excludes:
        if rel == exc or rel.startswith(exc + "/"):
            return True

    # 排除 frontend/node_modules
    if "/node_modules/" in rel or rel.startswith("node_modules/"):
        return True

    # 排除所有 __pycache__
    if "/__pycache__/" in rel or rel.startswith("__pycache__/"):
        return True

    # 排除所有 .pyc / .pyo
    if name.endswith(".pyc") or name.endswith(".pyo"):
        return True

    # 排除所有 .log 文件
    if name.endswith(".log"):
        return True

    # 排除所有 .db 文件
    if name.endswith(".db"):
        return True

    return False


def dir_excluded(name: str) -> bool:
    return name in EXCLUDE_PATTERNS and not name.startswith("*")


def collect_files(root: Path) -> list[Path]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace("\\", "/")
        if rel_dir == ".":
            rel_dir = ""

        # 就地修剪排除的目录，防止 os.walk 进入
        dirnames[:] = [
            d
            for d in dirnames
            if not dir_excluded(d)
            and not is_excluded(d, f"{rel_dir}/{d}" if rel_dir else d)
        ]

        for fname in sorted(filenames):
            fpath = os.path.join(dirpath, fname)
            rel = os.path.relpath(fpath, root).replace("\\", "/")
            if not is_excluded(fname, rel):
                files.append(Path(fpath))

    return sorted(files)


def create_zip(root: Path, files: list[Path], output_path: Path) -> None:
    print(f"正在创建压缩包: {output_path.name}")
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            arcname = file_path.relative_to(root).as_posix()
            zf.write(file_path, arcname)
    print(f"压缩包创建完成: {output_path}")


def verify_zip(zip_path: Path) -> bool:
    print(f"\n正在验证压缩包完整性: {zip_path.name}")
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            bad = zf.testzip()
            if bad:
                print(f"错误: 压缩包中文件损坏: {bad}")
                return False
            file_count = len(zf.namelist())
            print(f"验证通过: 压缩包包含 {file_count} 个文件")
            return True
    except Exception as e:
        print(f"验证失败: {e}")
        return False


def list_contents(zip_path: Path) -> None:
    print("\n压缩包文件列表:")
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            size_kb = info.file_size / 1024
            print(f"  {info.filename} ({size_kb:.1f} KB)")


def create_checksum(file_path: Path, checksum_path: Path) -> None:
    print("\n正在生成 SHA256 校验和...")
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    checksum = sha256.hexdigest()
    with open(checksum_path, "w") as f:
        f.write(f"{checksum}  {file_path.name}\n")
    print(f"SHA256: {checksum}")
    print(f"校验和已保存至: {checksum_path}")


def verify_checksum(file_path: Path, checksum_path: Path) -> bool:
    print("\n正在验证校验和...")
    with open(checksum_path, "r") as f:
        expected = f.read().strip().split()[0]
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    actual = sha256.hexdigest()
    match = expected == actual
    if match:
        print("校验和验证通过 [OK]")
    else:
        print("校验和验证失败 [FAILED]")
        print(f"  期望: {expected}")
        print(f"  实际: {actual}")
    return match


def print_summary(files: list[Path], root: Path) -> None:
    print(f"项目根目录: {root}")
    print(f"将被打包的文件总数: {len(files)}")
    total_size = sum(f.stat().st_size for f in files)
    print(f"总大小: {total_size / 1024 / 1024:.2f} MB")

    dirs = set(f.parent for f in files)
    print(f"涉及目录数: {len(dirs)}")


def main():
    root = PROJECT_ROOT
    zip_path = OUTPUT_DIR / ZIP_NAME
    sha256_path = OUTPUT_DIR / SHA256_NAME

    print("=" * 60)
    print("  法律智能判决分析系统 - 项目打包工具")
    print("=" * 60)

    # 如果已存在压缩包，先删除
    if zip_path.exists():
        zip_path.unlink()
    if sha256_path.exists():
        sha256_path.unlink()

    # Step 1: 收集文件
    print("\n[1/5] 正在扫描项目文件...")
    files = collect_files(root)
    print_summary(files, root)

    # Step 2: 创建压缩包
    print("\n[2/5] 正在创建压缩包...")
    create_zip(root, files, zip_path)

    # Step 3: 验证完整性
    print("\n[3/5] 正在验证压缩包完整性...")
    if not verify_zip(zip_path):
        sys.exit(1)

    # Step 4: 生成校验和
    print("\n[4/5] 正在生成 SHA256 校验和...")
    create_checksum(zip_path, sha256_path)

    # Step 5: 最终验证
    print("\n[5/5] 正在执行最终验证...")
    verify_checksum(zip_path, sha256_path)

    actual_size = zip_path.stat().st_size
    print(f"\n{'=' * 60}")
    print("  打包完成!")
    print(f"  压缩包: {zip_path}")
    print(f"  压缩包大小: {actual_size / 1024 / 1024:.2f} MB")
    print(f"  校验和文件: {sha256_path}")
    print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
