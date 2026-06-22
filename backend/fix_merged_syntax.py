"""批量修复代码合并导致的语法错误。

主要修复模式：
1. 多个 import 语句合并在一行
2. 关键字后直接跟另一个关键字（returntry, returnif, returnexcept 等）
3. 字符串字面量被截断
"""
import os
import re
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "app"

# 需要跳过的目录
SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".venv", "venv"}


def find_python_files(root: Path):
    """递归查找所有 Python 文件。"""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            if filename.endswith(".py"):
                yield Path(dirpath) / filename


def fix_merged_imports(content: str) -> str:
    """修复合并的 import 语句。"""
    lines = content.split("\n")
    result = []
    
    for line in lines:
        # 模式1: "import Ximport Y" 或 "from X import Yfrom Z"
        # 查找 "import" 前面紧跟非空白字符的情况
        if "import" in line:
            # 处理 "import Ximport Y" 模式
            new_line = re.sub(r'(?<!^)(?<!\s)import\s+', r'\nimport ', line)
            # 处理 "from X import Yfrom Z" 模式
            new_line = re.sub(r'(?<!^)from\s+(\S+)\s+import\s+([^f\n]+)from\s+', 
                             lambda m: f'from {m.group(1)} import {m.group(2).strip()}\nfrom ', 
                             new_line)
            if new_line != line:
                # 拆分多行
                for sub_line in new_line.split('\n'):
                    if sub_line.strip():
                        result.append(sub_line)
                continue
        
        # 模式2: 变量赋值后直接跟 "from" 或 "import"
        # 例如: "VAR = valuefrom X import Y"
        match = re.search(r'(\S)\s*from\s+([a-zA-Z_][\w.]*)\s+import\s+(.+)$', line)
        if match and not line.strip().startswith('from'):
            prefix = line[:match.start() + 1]
            from_part = f"from {match.group(2)} import {match.group(3)}"
            result.append(prefix)
            result.append(from_part)
            continue
        
        result.append(line)
    
    return "\n".join(result)


def fix_merged_keywords(content: str) -> str:
    """修复合并的关键字。"""
    # 模式: "returntry:", "returnif", "returnexcept", "returnfor", "returnwhile"
    patterns = [
        (r'\breturn(try:)', r'return\n\1'),
        (r'\breturn(if\s)', r'return\n\1'),
        (r'\breturn(except\s)', r'return\n\1'),
        (r'\breturn(for\s)', r'return\n\1'),
        (r'\breturn(while\s)', r'return\n\1'),
        (r'\breturn(raise\s)', r'return\n\1'),
        (r'return([A-Z][A-Z_]+\s*=)', r'return\n\1'),  # returnVAR = ...
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    return content


def fix_string_literal_issues(content: str) -> str:
    """修复字符串字面量问题。"""
    # 模式: """xxxx") 应该是 """\n    xxx")
    # 例如: """正在启动案件分析 API...")
    content = re.sub(r'("""[^"\n]{5,})("\))', r'\1\n    \2', content)
    
    # 模式: """?" not in path: 应该是 """\n    if "?" not in path:
    content = re.sub(r'("""\?)\s+(not in)', r'\1\n    if \2', content)
    
    return content


def fix_file(filepath: Path) -> bool:
    """修复单个文件。返回是否修改了文件。"""
    try:
        original = filepath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"读取失败 {filepath}: {e}")
        return False
    
    content = original
    
    # 依次应用各种修复
    content = fix_merged_imports(content)
    content = fix_merged_keywords(content)
    content = fix_string_literal_issues(content)
    
    if content != original:
        try:
            filepath.write_text(content, encoding="utf-8")
            print(f"已修复: {filepath}")
            return True
        except Exception as e:
            print(f"写入失败 {filepath}: {e}")
            return False
    
    return False


def main():
    """主函数。"""
    print(f"扫描目录: {BACKEND_DIR}")
    fixed_count = 0
    total_count = 0
    
    for py_file in find_python_files(BACKEND_DIR):
        total_count += 1
        if fix_file(py_file):
            fixed_count += 1
    
    print(f"\n扫描文件总数: {total_count}")
    print(f"修复文件数: {fixed_count}")


if __name__ == "__main__":
    main()
