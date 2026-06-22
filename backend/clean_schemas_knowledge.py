"""彻底清理 schemas/knowledge.py 中的所有错误注释和拆分问题."""
import re

path = r"c:\Users\Lenovo\Desktop\帮信罪辅助裁定软件\backend\app\schemas\knowledge.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# 1. 移除所有独立的错误注释行（整行只有这种注释）
content = re.sub(r"^\s*#\s*条件判断[:：]处理业务逻辑\s*\n", "", content, flags=re.MULTILINE)
content = re.sub(r"^\s*#\s*异常处理[:：]处理业务逻辑\s*\n", "", content, flags=re.MULTILINE)
content = re.sub(r"^\s*#\s*捕获异常[:：]处理业务逻辑\s*\n", "", content, flags=re.MULTILINE)
content = re.sub(r"^\s*#\s*返回处理结果\s*\n", "", content, flags=re.MULTILINE)
content = re.sub(r"^\s*#\s*抛出异常.*\s*\n", "", content, flags=re.MULTILINE)
content = re.sub(r"^\s*#\s*应用装饰器[:：].*\s*\n", "", content, flags=re.MULTILINE)
content = re.sub(r"^\s*#\s*函数.*的初始化逻辑\s*\n", "", content, flags=re.MULTILINE)
content = re.sub(r"^\s*#\s*定义.*类\s*\n", "", content, flags=re.MULTILINE)
content = re.sub(r"^\s*#\s*条件判断[:：]检查.*\s*\n", "", content, flags=re.MULTILINE)
content = re.sub(r"^\s*#\s*初始化变量.*\s*\n", "", content, flags=re.MULTILINE)

# 2. 移除行尾的错误注释
content = re.sub(r"\s*#\s*条件判断[:：]处理业务逻辑\s*$", "", content, flags=re.MULTILINE)
content = re.sub(r"\s*#\s*异常处理[:：]处理业务逻辑\s*$", "", content, flags=re.MULTILINE)
content = re.sub(r"\s*#\s*捕获异常[:：]处理业务逻辑\s*$", "", content, flags=re.MULTILINE)

# 3. 修复被拆分的代码：合并下一行到当前行（当下一行缩进不匹配时）
# 特殊处理：def xxx\ntry_id(... 类型
content = re.sub(
    r"(def\s+\w+)\s*\n\s*(try_id\([^)]+\):)",
    r"\1\2",
    content
)

# 处理 "updated_at:\n datetime" 类型
content = re.sub(
    r"(updated_at:\s*)\n\s*(datetime)",
    r"\1\2",
    content
)

# 处理 "= None\n" 类型（如 source_url: str | None\n= None）
content = re.sub(
    r"(\|\s*None)\s*\n\s*(=\s*None)",
    r"\1 \2",
    content
)

# 处理 "raise ValueError(m\nsg)" 类型
content = re.sub(
    r"raise\s+ValueError\((\w+)\s*\n(\w+)\)",
    r"raise ValueError(\1\2)",
    content
)

# 处理 "_MALICIOUS_PATTERN\n.search" 类型
content = re.sub(
    r"(_MALICIOUS_PATTERN)\s*\n\s*(\.search\()",
    r"\1\2",
    content
)

# 处理 "if _MALICIOUS_PATTERN\n.search" 类型
content = re.sub(
    r"(if\s+_MALICIOUS_PATTERN)\s*\n\s*(\.search\([^)]+\):)",
    r"\1\2",
    content
)

# 处理 "if             # 条件判断...\nv is not None" 类型
content = re.sub(
    r"(if\s+)#\s*条件判断[:：]处理业务逻辑\s*\n\s*(v\s+is\s+not\s+None)",
    r"\1\2",
    content
)

# 处理 "async w            # 异常处理...\nith" 类型
content = re.sub(
    r"(async\s+w)\s*#\s*异常处理[:：]处理业务逻辑\s*\n\s*(ith\s+)",
    r"\1\2",
    content
)

# 处理 "default_key = \"chang    # 条件判断...\ne-this-..." 字符串拆分
content = re.sub(
    r"(default_key\s*=\s*\"[a-z\-]+)\s*#\s*条件判断[:：]处理业务逻辑\s*\n\s*\"([^\"]+)\"",
    r'\1\2"',
    content
)

# 处理 "user = result.scalar_one_or_n        # 条件判断...\none()" 类型
content = re.sub(
    r"(result\.scalar_one_or_n)\s*#\s*条件判断[:：]处理业务逻辑\s*\n\s*(one\(\))",
    r"\1\2",
    content
)

# 处理 "return cipher_suite.decrypt(val            # 捕获异常...\nue.encode())" 类型
content = re.sub(
    r"(cipher_suite\.decrypt\(val)\s*#\s*捕获异常[:：]处理业务逻辑\s*\n\s*(ue\.encode\(\)\)\.decode\(\))",
    r"\1\2",
    content
)

# 处理 "headers={\"WWW-Authentica    # 异常处理...\nte\": \"Bearer\"}," 类型
content = re.sub(
    r"(\"WWW-Authentica)\s*#\s*异常处理[:：]处理业务逻辑\s*\n\s*(te\":\s*\"Bearer\"\s*,?\s*})",
    r'\1\2',
    content
)

# 处理 "remaining_sec\n        # 条件判断...\nonds = int(" 类型
content = re.sub(
    r"(remaining_sec)\s*\n\s*#\s*条件判断[:：]处理业务逻辑\s*\n\s*(onds\s*=\s*int\()",
    r"\1\2",
    content
)

# 处理 "authorization: Authorization 头部    # 条件判断...\n原始值" 类型
content = re.sub(
    r"(Authorization\s+头部)\s*#\s*条件判断[:：]处理业务逻辑\s*\n\s*(原始值)",
    r"\1\2",
    content
)

# 处理 "\"\"\"处理 HTTP 请求        # 条件判断...\n并记录审计日志.\"\"\"" 类型
content = re.sub(
    r"(\"\"\"处理 HTTP 请求)\s*#\s*条件判断[:：]处理业务逻辑\s*\n\s*(并记录审计日志\.\"\"\")",
    r"\1\2",
    content
)

# 处理 "\"        # 条件判断...\n\"\"将明文加密后存入数据库.\"\"\"" 类型
content = re.sub(
    r"\"\s*#\s*条件判断[:：]处理业务逻辑\s*\n\s*(\"\"\"将明文加密后存入数据库\.\"\"\")",
    r"\1",
    content
)

# 处理 "if             # 条件判断...\nv is not None and (v < 0.0 or v > 1.0):" 类型
content = re.sub(
    r"if\s+#\s*条件判断[:：]处理业务逻辑\s*\n\s*(v\s+is\s+not\s+None\s+and\s+\(v\s*<\s*0\.0\s+or\s+v\s*>\s*1\.0\):)",
    r"if \1",
    content
)

# 4. 修复缩进问题：确保 if 块内的代码正确缩进
# 这个需要更复杂的逻辑，暂时跳过，让后续手动处理

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("清理完成")
