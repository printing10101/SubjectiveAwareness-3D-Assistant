"""修复关键的语法错误 - 专门处理注释插入导致的错误"""
import re

def fix_knowledge_schema():
    """修复 schemas/knowledge.py 的关键错误"""
    filepath = 'app/schemas/knowledge.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复第195-199行的错误
    content = re.sub(
        r'# 应用装饰器: classmeth\s+\n\s+@classmeth\s+\nod\n\s+\n\s+def validate_title',
        '@classmethod\n    def validate_title',
        content
    )
    
    # 修复第203-204行的错误
    content = re.sub(
        r'Args:\n\s+\n\s+v: 原始标题字符串',
        'Args:\n            v: 原始标题字符串',
        content
    )
    
    # 修复第211-212行的错误
    content = re.sub(
        r'""\s+\n"',
        '"""',
        content
    )
    
    # 修复第219-220行的错误
    content = re.sub(
        r'raise Value\s+\nError\(msg\)',
        'raise ValueError(msg)',
        content
    )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Fixed: {filepath}")

def fix_common_errors(content):
    """修复常见的错误模式"""
    # 1. 移除错误插入的注释
    content = re.sub(r'\s+\n', '\n', content)
    content = re.sub(r'\s+# 异常处理：处理业务逻辑\n', '\n', content)
    content = re.sub(r'\s+# 循环遍历：处理业务逻辑\n', '\n', content)
    content = re.sub(r'\s+# 初始化变量.*\n', '\n', content)
    content = re.sub(r'\s+# 抛出异常.*\n', '\n', content)
    content = re.sub(r'\s+# 返回处理结果\n', '\n', content)
    
    # 2. 修复字符串截断
    content = re.sub(r'"([^"]*)\n([^"]*)"', lambda m: f'"{m.group(1)}{m.group(2)}"', content)
    
    # 3. 修复代码拆分
    content = re.sub(r'(\w+)\s*\n(\w+)', lambda m: f'{m.group(1)}{m.group(2)}' if len(m.group(1)) < 20 and len(m.group(2)) < 20 else m.group(0), content)
    
    return content

if __name__ == '__main__':
    fix_knowledge_schema()
    print("关键文件修复完成")
