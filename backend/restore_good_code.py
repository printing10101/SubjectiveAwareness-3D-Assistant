"""从 78e0b7c 提交恢复所有有语法错误的文件"""
import subprocess
import ast
from pathlib import Path

BACKEND_DIR = Path(r"c:\Users\Lenovo\Desktop\帮信罪辅助裁定软件\backend")
GOOD_COMMIT = "78e0b7c"

# 需要检查的目录
DIRS_TO_CHECK = [
    BACKEND_DIR / "app",
    BACKEND_DIR / "tests",
]


def find_python_files():
    """查找所有有语法错误的 Python 文件"""
    import os
    skip_dirs = {"__pycache__", ".git", "node_modules", ".venv", "venv", ".trae"}
    for root in DIRS_TO_CHECK:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
            for f in filenames:
                if f.endswith(".py"):
                    yield Path(dirpath) / f


def has_syntax_error(filepath: Path) -> bool:
    """检查文件是否有语法错误"""
    try:
        content = filepath.read_text(encoding="utf-8")
        ast.parse(content)
        return False
    except SyntaxError:
        return True
    except Exception:
        return False


def restore_from_commit(filepath: Path, commit: str) -> bool:
    """从指定提交恢复文件"""
    rel_path = filepath.relative_to(Path(r"c:\Users\Lenovo\Desktop\帮信罪辅助裁定软件"))
    try:
        result = subprocess.run(
            ["git", "show", f"{commit}:{rel_path.as_posix()}"],
            capture_output=True,
            text=True,
            cwd=r"c:\Users\Lenovo\Desktop\帮信罪辅助裁定软件",
            encoding="utf-8",
        )
        if result.returncode == 0:
            filepath.write_text(result.stdout, encoding="utf-8")
            return True
        return False
    except Exception:
        return False


def main():
    print("查找有语法错误的文件...")
    error_files = []
    for f in find_python_files():
        if has_syntax_error(f):
            error_files.append(f)

    print(f"找到 {len(error_files)} 个有语法错误的文件")

    # 尝试从 78e0b7c 恢复
    restored = 0
    still_broken = []
    for f in error_files:
        if restore_from_commit(f, GOOD_COMMIT):
            # 验证恢复后的文件
            if not has_syntax_error(f):
                print(f"  恢复: {f.relative_to(BACKEND_DIR)}")
                restored += 1
            else:
                print(f"  恢复后仍有错误: {f.relative_to(BACKEND_DIR)}")
                still_broken.append(f)
        else:
            print(f"  无法恢复（文件不存在于 {GOOD_COMMIT}）: {f.relative_to(BACKEND_DIR)}")
            still_broken.append(f)

    print(f"\n完成！恢复 {restored} 个文件，{len(still_broken)} 个文件仍有问题")


if __name__ == "__main__":
    main()
