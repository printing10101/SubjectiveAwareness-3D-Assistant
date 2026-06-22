"""从 78e0b7c 提交恢复所有有语法错误的文件"""
import subprocess
import ast
import os
from pathlib import Path

BACKEND_DIR = Path(r"c:\Users\Lenovo\Desktop\帮信罪辅助裁定软件\backend")
SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".venv", "venv", ".trae"}


def find_python_files():
    for root in [BACKEND_DIR / "app", BACKEND_DIR / "tests"]:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for f in filenames:
                if f.endswith(".py"):
                    yield Path(dirpath) / f


def has_syntax_error(filepath: Path) -> bool:
    try:
        content = filepath.read_text(encoding="utf-8")
        ast.parse(content)
        return False
    except SyntaxError:
        return True
    except Exception:
        return False


def restore_from_commit(filepath: Path, commit: str) -> bool:
    rel_path = filepath.relative_to(Path(r"c:\Users\Lenovo\Desktop\帮信罪辅助裁定软件"))
    try:
        result = subprocess.run(
            ["git", "checkout", commit, "--", rel_path.as_posix()],
            capture_output=True,
            text=True,
            cwd=r"c:\Users\Lenovo\Desktop\帮信罪辅助裁定软件",
        )
        return result.returncode == 0
    except Exception:
        return False


def main():
    print("查找有语法错误的文件...")
    error_files = []
    for f in find_python_files():
        if has_syntax_error(f):
            error_files.append(f)

    print(f"找到 {len(error_files)} 个有语法错误的文件")

    restored = 0
    still_broken = []
    for f in error_files:
        if restore_from_commit(f, "78e0b7c"):
            if not has_syntax_error(f):
                print(f"  恢复: {f.relative_to(BACKEND_DIR)}")
                restored += 1
            else:
                print(f"  恢复后仍有错误: {f.relative_to(BACKEND_DIR)}")
                still_broken.append(f)
        else:
            print(f"  无法恢复（V1.1.0新增）: {f.relative_to(BACKEND_DIR)}")
            still_broken.append(f)

    print(f"\n完成！恢复 {restored} 个文件，{len(still_broken)} 个文件仍有问题")
    if still_broken:
        print("\n需要手动修复的文件:")
        for f in still_broken:
            print(f"  {f.relative_to(BACKEND_DIR)}")


if __name__ == "__main__":
    main()
