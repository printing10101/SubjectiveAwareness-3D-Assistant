import ast
import os

errors = []
for root, dirs, files in os.walk('app'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            try:
                with open(path, encoding='utf-8') as fh:
                    ast.parse(fh.read())
            except SyntaxError as e:
                errors.append((path, e.lineno, e.msg))

if not errors:
    print("All files OK!")
else:
    for path, lineno, msg in sorted(errors):
        print(f"{path}:{lineno}: {msg}")
    print(f"\nTotal: {len(errors)} files with syntax errors")
