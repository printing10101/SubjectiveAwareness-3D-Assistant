"""扫描 backend/app 下所有 .py 文件的语法错误."""
import ast
import os
from pathlib import Path

ROOT = Path(r"c:\Users\Lenovo\Desktop\帮信罪辅助裁定软件\backend\app")
errors = []
for path in ROOT.rglob("*.py"):
    try:
        src = path.read_text(encoding="utf-8")
        ast.parse(src, filename=str(path))
    except SyntaxError as e:
        errors.append((path, e.lineno, e.msg, e.text))

print(f"共扫描 {sum(1 for _ in ROOT.rglob('*.py'))} 个文件, 发现 {len(errors)} 个语法错误:")
for p, ln, msg, txt in errors:
    rel = p.relative_to(ROOT.parent.parent)
    print(f"  {rel}:{ln}: {msg}")
    if txt:
        print(f"    {txt.rstrip()}")
