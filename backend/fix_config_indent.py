"""修复 config.py 中所有缩进问题"""
import re

with open(r"c:\Users\Lenovo\Desktop\帮信罪辅助裁定软件\backend\app\config.py", "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")
fixed_lines = []
in_method = False
method_indent = 0

for i, line in enumerate(lines):
    stripped = line.lstrip()
    current_indent = len(line) - len(stripped)
    
    # 检测方法定义
    if re.match(r"def \w+\(self", stripped):
        in_method = True
        method_indent = current_indent
        fixed_lines.append(line)
        continue
    
    # 如果在方法内，检查缩进是否正确
    if in_method:
        # 空行或注释
        if not stripped or stripped.startswith("#"):
            fixed_lines.append(line)
            continue
        
        # 检查是否是方法结束（遇到另一个 def 或 class，且缩进相同或更小）
        if (stripped.startswith("def ") or stripped.startswith("class ") or 
            stripped.startswith("@")) and current_indent <= method_indent:
            in_method = False
            fixed_lines.append(line)
            continue
        
        # 方法内的第一行代码应该有 method_indent + 4 的缩进
        if current_indent > 0 and current_indent <= method_indent and not stripped.startswith(("if ", "for ", "while ", "try:", "except", "with ")):
            # 这行代码缩进不正确，需要修复
            fixed_line = " " * (method_indent + 4) + stripped
            fixed_lines.append(fixed_line)
            print(f"Fixed line {i+1}: {line[:50]} -> {fixed_line[:50]}")
            continue
    
    fixed_lines.append(line)

result = "\n".join(fixed_lines)

with open(r"c:\Users\Lenovo\Desktop\帮信罪辅助裁定软件\backend\app\config.py", "w", encoding="utf-8") as f:
    f.write(result)

print("Config.py 缩进修复完成")
