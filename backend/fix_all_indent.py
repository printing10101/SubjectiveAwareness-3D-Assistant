"""全面扫描并修复所有 Python 文件中的缩进和语法错误"""
import os
import re
import ast
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


def fix_file(filepath: Path) -> bool:
    """修复单个文件的语法错误，返回是否修改"""
    try:
        original = filepath.read_text(encoding="utf-8")
    except Exception:
        return False

    content = original
    lines = content.split("\n")
    fixed_lines = []
    changed = False

    # Pass 1: 修复合并的 return 语句
    # "return Xreturn Y" -> "return X\n    return Y"
    content = re.sub(
        r'(return\s+[^\n]+?)return\s+',
        r'\1\n    return ',
        content
    )
    # "return Xexcept " -> "return X\nexcept "
    content = re.sub(
        r'(return\s+[^\n]+?)except\s+',
        r'\1\nexcept ',
        content
    )
    # "return Xif " -> "return X\nif " (at same indent level)
    content = re.sub(
        r'(return\s+[^\n]+?)\n(\s*)if\s+',
        lambda m: m.group(0) if m.group(2) else m.group(1) + '\n    if ',
        content
    )

    # Pass 2: 修复合并的 except 语句
    # "except X:  ...return Yexcept Z:" -> split
    content = re.sub(
        r'(except\s+\w+(\s+as\s+\w+)?:[^\n]*?)\n(\s*)except\s+',
        r'\1\n\3except ',
        content
    )

    lines = content.split("\n")
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        # 检查方法/函数定义后的第一行缩进
        if re.match(r'(def |class |@property|@classmethod|@staticmethod)', stripped):
            fixed_lines.append(line)
            i += 1
            # 查看下一行
            if i < len(lines):
                next_line = lines[i]
                next_stripped = next_line.lstrip()
                next_indent = len(next_line) - len(next_stripped)
                # 如果是 docstring 或空行，继续
                if next_stripped.startswith('"""') or next_stripped.startswith("'''") or not next_stripped:
                    fixed_lines.append(next_line)
                    i += 1
                    # 找到 docstring 结束
                    if next_stripped.startswith('"""') or next_stripped.startswith("'''"):
                        quote = next_stripped[:3]
                        if next_stripped.count(quote) == 1:
                            while i < len(lines):
                                fixed_lines.append(lines[i])
                                if quote in lines[i] and lines[i].strip() != quote:
                                    i += 1
                                    break
                                i += 1
                    # 现在检查下一行
                    if i < len(lines):
                        body_line = lines[i]
                        body_stripped = body_line.lstrip()
                        body_indent = len(body_line) - len(body_stripped)
                        # 期望的缩进
                        if stripped.startswith(('def ', 'async def ', 'class ')):
                            expected = indent + 4
                        else:
                            expected = indent
                        # 如果 body 缩进不正确
                        if body_stripped and body_indent < expected and not body_stripped.startswith(('def ', 'class ', '@')):
                            fixed_lines.append(' ' * expected + body_stripped)
                            changed = True
                        else:
                            fixed_lines.append(body_line)
                        i += 1
                    continue
                # 如果不是 docstring，检查缩进
                if next_stripped and not next_stripped.startswith(('def ', 'class ', '@')):
                    if stripped.startswith(('def ', 'async def ', 'class ')):
                        expected = indent + 4
                    else:
                        expected = indent
                    if next_indent != expected and next_indent < expected:
                        fixed_lines.append(' ' * expected + next_stripped)
                        changed = True
                        i += 1
                        continue
            continue

        # 检查 if/for/while/try/except/with 后的缩进
        if re.match(r'(if |elif |else:|for |while |try:|except|finally:|with )', stripped):
            fixed_lines.append(line)
            i += 1
            # 查看下一行
            if i < len(lines):
                next_line = lines[i]
                next_stripped = next_line.lstrip()
                next_indent = len(next_line) - len(next_stripped)
                if next_stripped and not next_stripped.startswith(('def ', 'class ', '@', 'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except', 'finally:', 'with ')):
                    expected = indent + 4
                    if next_indent != expected and next_indent < expected:
                        fixed_lines.append(' ' * expected + next_stripped)
                        changed = True
                        i += 1
                        continue
            continue

        fixed_lines.append(line)
        i += 1

    if changed:
        result = "\n".join(fixed_lines)
        try:
            ast.parse(result)
            filepath.write_text(result, encoding="utf-8")
            return True
        except SyntaxError as e:
            print(f"  跳过 {filepath}: 修复后仍有语法错误 - {e}")
            return False
    return False


def main():
    print("开始扫描并修复语法错误...")
    fixed_count = 0
    for f in find_python_files(APP_DIR, TESTS_DIR):
        if fix_file(f):
            print(f"  修复: {f}")
            fixed_count += 1
    print(f"\n完成！共修复 {fixed_count} 个文件")


if __name__ == "__main__":
    main()
