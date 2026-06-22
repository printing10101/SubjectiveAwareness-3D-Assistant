"""系统性修复 schemas/knowledge.py 中的语法错误."""
import re

path = r"c:\Users\Lenovo\Desktop\帮信罪辅助裁定软件\backend\app\schemas\knowledge.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")
out = []
i = 0
while i < len(lines):
    line = lines[i]
    # 移除单独成行的错误注释
    if re.match(r"^\s*#\s*条件判断[:：]处理业务逻辑\s*$", line):
        i += 1
        continue
    if re.match(r"^\s*#\s*函数.*的初始化逻辑\s*$", line):
        i += 1
        continueline = re.sub(r"\s*#\s*条件判断[:：]处理业务逻辑\s*$", "", line)
    line = re.sub(r"\s*#\s*异常处理[:：]处理业务逻辑\s*$", "", line)
    line = re.sub(r"\s*#\s*捕获异常[:：]处理业务逻辑\s*$", "", line)
    # 修复被拆分的字符串: 如 "change-this-to-a-secure-...-key"
    # 修复被拆分的代码: 下一行以非缩进开头且当前行以 = 或 ( 结尾等
    out.append(line)
    i += 1

# 合并被拆分的行
merged = []
i = 0
while i < len(out):
    line = out[i]
    # 如果下一行以空白开头但缩进不匹配，可能是被拆分的代码
    if i + 1 < len(out):
        next_line = out[i + 1]
        # 检测形如 "def validate_target_en\ntry_id(cls, v..." 的拆分
        if re.match(r"^\s*def\s+\w+$", line.rstrip()) and next_line and not next_line.lstrip().startswith(("#", "\"\"\"", "'''")):
            # 合并
            merged.append(line.rstrip() + next_line.lstrip())
            i += 2
            continue
        # 检测 "updated_at:\n datetime" 类型
        if line.rstrip().endswith(":") and re.match(r"^\s+\w+\s*$", next_line):
            merged.append(line.rstrip() + next_line.strip())
            i += 2
            continue
    merged.append(line)
    i += 1

with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(merged))
print("修复完成")
