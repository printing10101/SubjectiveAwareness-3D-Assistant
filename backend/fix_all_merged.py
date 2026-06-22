"""全面修复所有 Python 文件中因代码合并导致的语法错误。"""
import os
import re
import ast
import sys
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


def split_merged_import_line(line):
    """拆分一行中合并的多个 import 语句。"""
    # 匹配 "import Ximport Y" 或 "import Xfrom Y" 模式
    # 先处理 "from X import Yfrom Z import W" 模式
    parts = []
    
    # 用正则拆分：在 "import" 或 "from" 前面没有空格/换行的地方拆分
    # 但要注意不能在字符串内部拆分
    
    # 策略：逐字符扫描，跟踪是否在字符串内
    result_lines = []
    current = ""
    i = 0
    in_string = None  # None, '"', "'"
    
    while i < len(line):
        ch = line[i]
        
        # 处理字符串状态
        if in_string is None:
            if ch in ('"', "'"):
                # 检查是否是三引号
                if line[i:i+3] in ('"""', "'''"):
                    # 找到配对的结束三引号
                    end = line.find(line[i:i+3], i+3)
                    if end != -1:
                        current += line[i:end+3]
                        i = end + 3
                        continue
                    else:
                        current += line[i:]
                        break
                in_string = ch
                current += ch
            elif ch == '#':
                # 注释，剩余部分都是注释
                current += line[i:]
                break
            else:
                # 检查是否是不正当的 import/from 连接
                # 模式: 非空白字符后直接跟 "import" 或 "from"
                if line[i:i+6] == 'import' and i > 0 and not line[i-1].isspace():
                    # 检查前面不是 "from X import" 中的 import
                    # 即前面应该是某个语句的结束
                    result_lines.append(current.rstrip())
                    current = "import"
                    i += 6
                    continue
                elif line[i:i+4] == 'from' and i > 0 and not line[i-1].isspace():
                    result_lines.append(current.rstrip())
                    current = "from"
                    i += 4
                    continue
                else:
                    current += ch
        else:
            current += ch
            if ch == in_string:
                # 检查转义
                if i == 0 or line[i-1] != '\\':
                    in_string = None
        
        i += 1
    
    if current.strip():
        result_lines.append(current.strip())
    
    return result_lines if len(result_lines) > 1 else None


def fix_merged_returns(content):
    """修复合并的 return 语句。"""
    # "return Nonereturn X" -> "return None\n    return X"
    content = re.sub(r'return\s+None\s*return\s+', 'return None\n    return ', content)
    # "returntry:" -> "return\n    try:"
    content = re.sub(r'return\s*try\s*:', 'return\n    try:', content)
    # "returnif " -> "return\n    if "
    content = re.sub(r'return\s*if\s+', 'return\n    if ', content)
    # "returnexcept " -> "return\n    except "
    content = re.sub(r'return\s*except\s+', 'return\n    except ', content)
    # "returnfor " -> "return\n    for "
    content = re.sub(r'return\s*for\s+', 'return\n    for ', content)
    return content


def fix_merged_statements(content):
    """修复合并的语句，如 "return Nonevariable = ..." """
    # "return None<var>: <type>" 模式
    content = re.sub(
        r'return\s+None([a-zA-Z_]\w*\s*:\s*)',
        r'return None\n    \1',
        content
    )
    # "return<var> = " 模式 (return后直接跟变量赋值)
    content = re.sub(
        r'return\s+([a-zA-Z_]\w*\s*=\s*)',
        r'return\n    \1',
        content
    )
    return content


def fix_docstring_ending(content):
    """修复 docstring 结尾与代码合并的问题。"""
    # """..."""code -> """...\n    code
    # 匹配: """后紧跟非空白字符（不是换行、不是空格）
    content = re.sub(
        r'("""\s*)\n(\s*)([a-zA-Z_@#])',
        lambda m: m.group(1) + '\n' + m.group(2) + m.group(3) if '\n' in m.group(1) else m.group(0),
        content
    )
    
    # 具体模式: """<code> 应该是 """\n    <code>
    content = re.sub(
        r'"""\s*([a-zA-Z_]\w*[^\s"])',
        r'"""\n    \1',
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
    
    # 1. 修复合并的 return 语句
    content = fix_merged_returns(content)
    
    # 2. 修复合并的语句
    content = fix_merged_statements(content)
    
    # 3. 修复 docstring 结尾
    content = fix_docstring_ending(content)
    
    # 4. 逐行修复合并的 import
    lines = content.split('\n')
    new_lines = []
    changed = False
    
    for line in lines:
        stripped = line.strip()
        if stripped and ('import' in stripped) and not stripped.startswith('#'):
            # 检查是否有合并的 import
            result = split_merged_import_line(line)
            if result:
                indent = len(line) - len(line.lstrip())
                for r in result:
                    new_lines.append(' ' * indent + r.strip())
                changed = True
                continue
        
        # 检查其他合并模式：变量赋值后直接跟 "from"
        # 例如: "VAR = valuefrom X import Y"
        m = re.match(r'^(\s*\w[\w\[\],\s]*:\s*\w[\w\.\|,\s]*=\s*.+?)from\s+(\S+)\s+import\s+(.+)$', line)
        if m:
            new_lines.append(m.group(1).rstrip())
            new_lines.append(f"from {m.group(2)} import {m.group(3)}")
            changed = True
            continue
        
        new_lines.append(line)
    
    if changed:
        content = '\n'.join(new_lines)
    
    if content != original:
        filepath.write_text(content, encoding="utf-8")
        return True
    return False


def check_syntax(filepath):
    """检查文件是否有语法错误。"""
    try:
        source = filepath.read_text(encoding="utf-8")
        ast.parse(source)
        return True
    except SyntaxError as e:
        return False
    except Exception:
        return True


def main():
    files = list(find_python_files(APP_DIR, TESTS_DIR))
    print(f"找到 {len(files)} 个 Python 文件")
    
    # 第一轮修复
    fixed = 0
    for f in files:
        if fix_file(f):
            fixed += 1
            print(f"  修复: {f.relative_to(BACKEND_DIR)}")
    print(f"第一轮修复了 {fixed} 个文件")
    
    # 检查语法错误
    errors = []
    for f in files:
        if not check_syntax(f):
            try:
                source = f.read_text(encoding="utf-8")
                ast.parse(source)
            except SyntaxError as e:
                errors.append((f, e))
    
    if errors:
        print(f"\n仍有 {len(errors)} 个文件存在语法错误:")
        for f, e in errors[:20]:
            print(f"  {f.relative_to(BACKEND_DIR)}:{e.lineno}: {e.msg}")
    else:
        print("\n所有文件语法检查通过!")


if __name__ == "__main__":
    main()
