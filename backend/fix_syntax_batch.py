"""批量修复所有 Python 文件中的语法错误"""
import ast
import os
import re
from pathlib import Path

BACKEND_DIR = Path(r"c:\Users\Lenovo\Desktop\帮信罪辅助裁定软件\backend")
SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".venv", "venv", ".trae"}


def find_python_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if f.endswith(".py"):
                yield Path(dirpath) / f


def fix_indentation_errors(content: str) -> str:
    """修复缩进错误"""
    lines = content.split("\n")
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        # 修复模块级 import 语句的错误缩进（非函数/类内部）
        if stripped.startswith(("import ", "from ")) and indent > 0:
            # 检查前一行是否是函数/类定义或控制块
            if fixed_lines:
                prev_line = fixed_lines[-1]
                prev_stripped = prev_line.lstrip()
                prev_indent = len(prev_line) - len(prev_stripped)
                # 如果前一行是模块级（缩进为0）或空行或注释
                if (prev_indent == 0 and not prev_stripped.startswith(("def ", "class ", "@", "if ", "try:", "except", "for ", "while ", "with ", "else:"))) or prev_stripped == "" or prev_stripped.startswith("#"):
                    fixed_lines.append(stripped)
                    i += 1
                    continue

        fixed_lines.append(line)
        i += 1
    return "\n".join(fixed_lines)


def fix_merged_lines(content: str) -> str:
    """修复合并的代码行"""
    # 修复 "return Xreturn Y" -> "return X\n    return Y"
    content = re.sub(r'(return\s+[^\n]+?)return\s+', r'\1\n    return ', content)
    # 修复 "return Xexcept" -> "return X\n    except"
    content = re.sub(r'(return\s+[^\n]+?)except\s+', r'\1\n    except ', content)
    # 修复 "return Xif " -> "return X\n    if "
    content = re.sub(r'(return\s+[^\n]+?)if\s+', r'\1\n    if ', content)
    # 修复 "return Xfor " -> "return X\n    for "
    content = re.sub(r'(return\s+[^\n]+?)for\s+', r'\1\n    for ', content)
    # 修复 "return Xwhile " -> "return X\n    while "
    content = re.sub(r'(return\s+[^\n]+?)while\s+', r'\1\n    while ', content)
    # 修复 "return Xtry:" -> "return X\n    try:"
    content = re.sub(r'(return\s+[^\n]+?)try\s*:', r'\1\n    try:', content)
    return content


def fix_comment_in_code(content: str) -> str:
    """修复代码中间插入注释导致的问题"""
    lines = content.split("\n")
    fixed_lines = []
    for i, line in enumerate(lines):
        # 修复 "async w            # 异常处理：处理业务逻辑\nith" 模式
        # 这种情况需要手动处理，太复杂
        fixed_lines.append(line)
    return "\n".join(fixed_lines)


def fix_file(filepath: Path) -> tuple[bool, str]:
    """修复单个文件，返回(是否修改, 错误信息)"""
    try:
        original = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"读取失败: {e}"

    content = original
    changed = False

    # 应用修复
    new_content = fix_merged_lines(content)
    if new_content != content:
        content = new_content
        changed = True

    new_content = fix_indentation_errors(content)
    if new_content != content:
        content = new_content
        changed = True

    if changed:
        try:
            ast.parse(content)
            filepath.write_text(content, encoding="utf-8")
            return True, ""
        except SyntaxError as e:
            return False, f"修复后仍有语法错误: {e}"

    return False, ""


def main():
    print("开始批量修复语法错误...")
    fixed_count = 0
    error_count = 0
    for f in find_python_files(BACKEND_DIR / "app"):
        modified, err = fix_file(f)
        if modified:
            print(f"  修复: {f.name}")
            fixed_count += 1
        elif err:
            print(f"  错误: {f.name} - {err}")
            error_count += 1

    for f in find_python_files(BACKEND_DIR / "tests"):
        modified, err = fix_file(f)
        if modified:
            print(f"  修复: {f.name}")
            fixed_count += 1
        elif err:
            print(f"  错误: {f.name} - {err}")
            error_count += 1

    print(f"\n完成！修复 {fixed_count} 个文件，{error_count} 个文件仍有错误")


if __name__ == "__main__":
    main()
