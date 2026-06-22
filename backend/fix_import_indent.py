"""修复 import 语句的缩进问题。"""
import os
import re
from pathlib import Path

BACKEND_DIR = Path(r"c:\Users\Lenovo\Desktop\帮信罪辅助裁定软件\backend")
APP_DIR = BACKEND_DIR / "app"
TESTS_DIR = BACKEND_DIR / "tests"

SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".venv", "venv", ".trae"}


def find_python_files(*roots):
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for f in filenames:
                if f.endswith(".py"):
                    yield Path(dirpath) / f


def fix_import_indentation(content):
    """修复 import 语句的错误缩进。"""
    lines = content.split('\n')
    result = []
    in_docstring = False
    docstring_char = None
    
    for i, line in enumerate(lines):
        # 跟踪 docstring 状态
        if not in_docstring:
            if '"""' in line or "'''" in line:
                count_triple_double = line.count('"""')
                count_triple_single = line.count("'''")
                if count_triple_double % 2 == 1:
                    in_docstring = True
                    docstring_char = '"""'
                elif count_triple_single % 2 == 1:
                    in_docstring = True
                    docstring_char = "'''"
        else:
            if docstring_char in line:
                in_docstring = False
                docstring_char = None
            result.append(line)
            continue
        
        # 不在 docstring 中，检查是否是 import 语句
        stripped = line.lstrip()
        if stripped.startswith(('import ', 'from ')):
            # 检查是否有错误的缩进
            leading_spaces = len(line) - len(line.lstrip())
            # 如果缩进大于0且不是从属缩进（如函数内的import），则移除缩进
            # 简单规则：如果前面是空行或注释，且缩进>0，则移除
            if leading_spaces > 0:
                # 检查前一行
                if i == 0 or not result or result[-1].strip() == '' or result[-1].lstrip().startswith('#'):
                    # 移除缩进
                    result.append(stripped)
                    continue
        
        result.append(line)
    
    return '\n'.join(result)


def fix_merged_class_definition(content):
    """修复合并的类定义。"""
    # 模式: "from X import Yclass Z(Base):" -> "from X import Y\n\nclass Z(Base):"
    content = re.sub(
        r'(from\s+\S+\s+import\s+\S+)class\s+(\w+)',
        r'\1\n\n\nclass \2',
        content
    )
    return content


def fix_file(filepath):
    """修复单个文件。"""
    try:
        original = filepath.read_text(encoding="utf-8")
    except Exception:
        return False
    
    content = original
    
    # 1. 修复 import 缩进
    content = fix_import_indentation(content)
    
    # 2. 修复合并的类定义
    content = fix_merged_class_definition(content)
    
    if content != original:
        filepath.write_text(content, encoding="utf-8")
        return True
    return False


def main():
    files = list(find_python_files(APP_DIR, TESTS_DIR))
    print(f"找到 {len(files)} 个 Python 文件")
    
    fixed = 0
    for f in files:
        if fix_file(f):
            fixed += 1
            print(f"  修复: {f.relative_to(BACKEND_DIR)}")
    
    print(f"\n修复了 {fixed} 个文件")


if __name__ == "__main__":
    main()
