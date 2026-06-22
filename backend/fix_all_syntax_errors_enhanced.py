#!/usr/bin/env python3
"""批量修复代码库中的语法错误 - 增强版"""

import re
import os
from pathlib import Path

def fix_file(filepath: Path) -> bool:
    """修复单个文件中的语法错误"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 修复模式1: 字符串被错误注释截断
        content = re.sub(
            r'["\']([^"\']*)\s+#\s+(?:初始化变量|条件判断|异常处理|异步等待|返回处理结果|函数)[^\n]*\n([^"\']*)["\']',
            lambda m: f'"{m.group(1).strip()}{m.group(2).strip()}"',
            content
        )
        
        # 修复模式2: 代码行被错误注释分割
        content = re.sub(
            r'(\w+)\s+#\s+(?:初始化变量|条件判断|异常处理|异步等待|返回处理结果|函数)[^\n]*\n(\w+)',
            lambda m: f'{m.group(1)}{m.group(2)}',
            content
        )
        
        # 修复模式3: 缩进错误的import语句
        content = re.sub(
            r'^    (from\s+\w+\s+import\s+.+)$',
            r'\1',
            content,
            flags=re.MULTILINE
        )
        
        # 修复模式4: 移除独立的错误注释行
        content = re.sub(
            r'^\s*#\s+(?:初始化变量|条件判断|异常处理|异步等待|返回处理结果|函数)[^\n]*\n',
            '',
            content,
            flags=re.MULTILINE
        )
        
        # 修复模式5: 修复被分割的函数调用
        content = re.sub(
            r'(\w+)\s+#\s+(?:初始化变量|条件判断|异常处理|异步等待|返回处理结果|函数)[^\n]*\n(\w+\()',
            lambda m: f'{m.group(1)}{m.group(2)}',
            content
        )
        
        # 修复模式6: 修复被分割的字符串字面量（f-string中的变量）
        content = re.sub(
            r'(\{[^}]*?)\s+#\s+(?:初始化变量|条件判断|异常处理|异步等待|返回处理结果|函数)[^\n]*\n([^}]*?\})',
            lambda m: f'{m.group(1)}{m.group(2)}',
            content
        )
        
        # 修复模式7: 修复被分割的变量赋值
        content = re.sub(
            r'(\w+\s*=\s*["\'][^"\']*)\s+#\s+(?:初始化变量|条件判断|异常处理|异步等待|返回处理结果|函数)[^\n]*\n([^"\']*["\'])',
            lambda m: f'{m.group(1)}{m.group(2)}',
            content
        )
        
        # 修复模式8: 修复被分割的字典键值对
        content = re.sub(
            r'(\{[^}]*?"[^"]*)\s+#\s+(?:初始化变量|条件判断|异常处理|异步等待|返回处理结果|函数)[^\n]*\n([^"]*"[^}]*?\})',
            lambda m: f'{m.group(1)}{m.group(2)}',
            content
        )
        
        # 修复模式9: 修复docstring后紧跟return语句的错误
        # 例如: """判断数据库 URL 是否为 PostgreSQL."""return"postgresql" in url
        # 应该为: """判断数据库 URL 是否为 PostgreSQL."""\n    return "postgresql" in url
        content = re.sub(
            r'("""[^"]*""")return',
            r'\1\n    return ',
            content
        )
        
        # 修复模式10: 修复return后缺少空格的问题
        content = re.sub(
            r'return"',
            r'return "',
            content
        )
        
        # 修复模式11: 修复字典定义后紧跟if语句的错误
        # 例如: kwargs: dict = {"echo": settings.DB_ECHO}if _is_postgresql(url):
        # 应该为: kwargs: dict = {"echo": settings.DB_ECHO}\n    if _is_postgresql(url):
        content = re.sub(
            r'(\{[^}]*\})(if\s+\w+)',
            r'\1\n    \2',
            content
        )
        
        # 修复模式12: 修复类定义后紧跟Base的错误
        # 例如: )Base = declarative_base()
        # 应该为: )\n\nBase = declarative_base()
        content = re.sub(
            r'\)(Base\s*=\s*declarative_base\(\))',
            r')\n\n\1',
            content
        )
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"修复文件 {filepath} 时出错: {e}")
        return False

def main():
    """主函数"""
    backend_dir = Path(__file__).parent / 'app'
    
    if not backend_dir.exists():
        print(f"目录不存在: {backend_dir}")
        return
    
    fixed_count = 0
    error_count = 0
    
    # 遍历所有Python文件
    for py_file in backend_dir.rglob('*.py'):
        if fix_file(py_file):
            print(f"已修复: {py_file}")
            fixed_count += 1
        else:
            error_count += 1
    
    print(f"\n修复完成:")
    print(f"  成功修复: {fixed_count} 个文件")
    print(f"  无需修复: {error_count} 个文件")

if __name__ == '__main__':
    main()
