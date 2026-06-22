"""验证所有Python文件语法."""
import ast
import pathlib

errors = []
for f in pathlib.Path('app').rglob('*.py'):
    try:
        ast.parse(f.read_text('utf-8'))
    except SyntaxError as e:
        errors.append((str(f), e.lineno, e.msg))

if errors:
    print(f"发现 {len(errors)} 个语法错误:")
    for f, line, msg in errors[:10]:  # 只显示前10个
        print(f"  {f}:{line} - {msg}")
else:
    print("所有文件语法检查通过!")
