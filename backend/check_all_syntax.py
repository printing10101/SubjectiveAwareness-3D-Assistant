"""检查所有Python文件的语法错误."""
import ast
import os

errors = []
for root, dirs, files in os.walk('app'):
    for filename in files:
        if filename.endswith('.py'):
            filepath = os.path.join(root, filename)
            try:
                with open(filepath, encoding='utf-8') as f:
                    ast.parse(f.read())
            except SyntaxError as e:
                errors.append(f"{filepath}:{e.lineno}: {e.msg}")
            except IndentationError as e:
                errors.append(f"{filepath}:{e.lineno}: {e.msg}")

if errors:
    print("发现语法错误:")
    for err in errors[:20]:
        print(err)
else:
    print("所有文件语法检查通过!")
