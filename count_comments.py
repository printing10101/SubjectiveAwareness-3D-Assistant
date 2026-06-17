"""统计代码注释率."""
import os
import re

def count_comments(filepath):
    """统计单个文件的注释行数."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception:
        return 0, 0

    total = len(lines)
    comments = 0
    in_docstring = False
    docstring_char = None

    for line in lines:
        stripped = line.strip()

        # 处理 Python 多行文档字符串
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                docstring_char = stripped[:3]
                comments += 1
                # 检查是否在同一行结束
                if stripped.count(docstring_char) >= 2 and len(stripped) > 3:
                    in_docstring = False
                else:
                    in_docstring = True
                continue
        elif in_docstring:
            comments += 1
            if docstring_char in stripped:
                in_docstring = False
            continue

        # 单行注释
        if stripped.startswith('#'):
            comments += 1
        elif stripped.startswith('//'):
            comments += 1
        elif stripped.startswith('/*') or stripped.startswith('*') or stripped.startswith('*/'):
            comments += 1
        elif stripped.startswith('<!--'):
            comments += 1

    return total, comments

def scan_directory(directory, extensions, skip_dirs=None):
    """扫描目录下所有文件的注释率."""
    if skip_dirs is None:
        skip_dirs = {'venv', '__pycache__', '.git', 'node_modules', '.trae', 'dist', 'build'}

    results = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                filepath = os.path.join(root, file)
                total, comments = count_comments(filepath)
                if total > 0:
                    rate = comments / total * 100
                    results.append((filepath, total, comments, rate))
    return results

# 统计后端
print("=" * 70)
print("后端 Python 文件注释率统计")
print("=" * 70)
backend_results = scan_directory('backend', ['.py'])
backend_results.sort(key=lambda x: x[3])

total_lines = 0
total_comments = 0
for filepath, total, comments, rate in backend_results:
    rel = filepath.replace('\\', '/')
    marker = " <-- 需补充" if rate < 30 else ""
    print(f"  {rate:6.1f}%  ({comments:4d}/{total:4d})  {rel}{marker}")
    total_lines += total
    total_comments += comments

b_rate = (total_comments / total_lines * 100) if total_lines > 0 else 0
print(f"\n  后端合计: {total_comments}/{total_lines} = {b_rate:.1f}%")

# 统计前端
print("\n" + "=" * 70)
print("前端 Vue/JS/TS 文件注释率统计")
print("=" * 70)
frontend_results = scan_directory('frontend/src', ['.vue', '.js', '.ts'])
frontend_results.sort(key=lambda x: x[3])

f_total_lines = 0
f_total_comments = 0
for filepath, total, comments, rate in frontend_results:
    rel = filepath.replace('\\', '/')
    marker = " <-- 需补充" if rate < 30 else ""
    print(f"  {rate:6.1f}%  ({comments:4d}/{total:4d})  {rel}{marker}")
    f_total_lines += total
    f_total_comments += comments

f_rate = (f_total_comments / f_total_lines * 100) if f_total_lines > 0 else 0
print(f"\n  前端合计: {f_total_comments}/{f_total_lines} = {f_rate:.1f}%")

# 总体
all_total = total_lines + f_total_lines
all_comments = total_comments + f_total_comments
all_rate = (all_comments / all_total * 100) if all_total > 0 else 0
print(f"\n{'=' * 70}")
print(f"总体注释率: {all_comments}/{all_total} = {all_rate:.1f}%")
print(f"是否达标(>=30%): {'是' if all_rate >= 30 else '否'}")
print(f"{'=' * 70}")

# 列出需要补充注释的文件（注释率低于30%且行数较多的关键文件）
print("\n需要重点补充注释的文件（<30% 且 >=20行）:")
all_results = backend_results + frontend_results
need_fix = [(f, t, c, r) for f, t, c, r in all_results if r < 30 and t >= 20]
need_fix.sort(key=lambda x: x[1], reverse=True)  # 按行数排序，优先处理大文件
for filepath, total, comments, rate in need_fix:
    rel = filepath.replace('\\', '/')
    print(f"  {rate:6.1f}%  ({total:4d}行)  {rel}")
