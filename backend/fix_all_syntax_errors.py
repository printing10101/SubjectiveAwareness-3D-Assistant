#!/usr/bin/env python3
"""批量修复代码库中的语法错误"""

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
        # 例如: "chang    # 条件判断\ne-this-to-a-secure-random-secret-key-in-production"
        # 应该合并为: "change-this-to-a-secure-random-secret-key-in-production"
        content = re.sub(
            r'["\']([^"\']*)\s+#\s+(?:初始化变量|条件判断|异常处理|异步等待|返回处理结果|函数)[^\n]*\n([^"\']*)["\']',
            lambda m: f'"{m.group(1).strip()}{m.group(2).strip()}"',
            content
        )
        
        # 修复模式2: 代码行被错误注释分割
        # 例如: "async w            # 异常处理\n..."
        # 应该合并为: "async with..."
        content = re.sub(
            r'(\w+)\s+#\s+(?:初始化变量|条件判断|异常处理|异步等待|返回处理结果|函数)[^\n]*\n(\w+)',
            lambda m: f'{m.group(1)}{m.group(2)}',
            content
        )
        
        # 修复模式3: 缩进错误的import语句
        # 例如: "    from datetime import UTC"
        # 应该为: "from datetime import UTC"
        content = re.sub(
            r'^    (from\s+\w+\s+import\s+.+)$',
            r'\1',
            content,
            flags=re.MULTILINE
        )
        
        # 修复模式4: 移除独立的错误注释行
        # 例如: 单独的 "# 初始化变量 xxx" 或 "# 条件判断: xxx"
        content = re.sub(
            r'^\s*#\s+(?:初始化变量|条件判断|异常处理|异步等待|返回处理结果|函数)[^\n]*\n',
            '',
            content,
            flags=re.MULTILINE
        )
        
        # 修复模式5: 修复被分割的函数调用
        # 例如: "user = result.scalar_one_or_n        # 条件判断\none()"
        # 应该为: "user = result.scalar_one_or_none()"
        content = re.sub(
            r'(\w+)\s+#\s+(?:初始化变量|条件判断|异常处理|异步等待|返回处理结果|函数)[^\n]*\n(\w+\()',
            lambda m: f'{m.group(1)}{m.group(2)}',
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
