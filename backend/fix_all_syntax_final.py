"""修复所有Python文件中的语法错误。

主要问题：
1. 错误注释导致代码被拆分（如 `self._keywo\n# 注释\nrd_extract`）
2. 标识符被错误注释打断
3. 字符串被错误注释截断
"""

import re
from pathlib import Path


def fix_split_identifier(content: str) -> str:
    """修复被注释拆分的标识符。"""
    # 模式：标识符的一部分 + 注释行 + 标识符的另一部分
    # 例如：self._keywo\n        # 条件判断：处理业务逻辑\nrd_extract
    pattern = r'(\w+)\s*\n\s*#\s*[^#\n]+\n\s*(\w+)'
    
    def replacer(match):
        part1 = match.group(1)
        part2 = match.group(2)
        # 检查是否应该合并（合并后是否是有效的Python标识符）
        combined = part1 + part2
        if re.match(r'^[a-zA-Z_]\w*$', combined):
            # 检查合并后是否更合理
            if len(part1) > 2 and len(part2) > 2:
                return combined
        return match.group(0)
    
    return re.sub(pattern, replacer, content)


def fix_split_method_calls(content: str) -> str:
    """修复被注释拆分的方法调用。"""
    # 修复 self._keywo\n# 注释\nrd_extract(case_text) 这种模式
    lines = content.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # 检查是否是拆分模式的第一部分
        if i + 2 < len(lines):
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            next_next_line = lines[i + 2] if i + 2 < len(lines) else ""
            
            # 检查是否是：部分标识符 + 注释 + 剩余标识符
            if (next_line.strip().startswith('#') and 
                not next_next_line.strip().startswith('#')):
                
                # 提取当前行末尾的标识符片段
                match1 = re.search(r'(\w+)\s*$', line)
                # 提取下下行的标识符片段
                match2 = re.match(r'\s*(\w+)', next_next_line)
                
                if match1 and match2:
                    part1 = match1.group(1)
                    part2 = match2.group(1)
                    combined = part1 + part2
                    
                    # 检查是否是合理的方法名或变量名
                    if len(part1) > 2 and len(part2) > 2:
                        # 合并这两行，跳过注释行
                        new_line = line[:match1.start()] + combined + next_next_line[match2.end():]
                        result.append(new_line)
                        i += 3  # 跳过注释行
                        continue
        
        result.append(line)
        i += 1
    
    return '\n'.join(result)


def fix_inline_comments_in_code(content: str) -> str:
    """修复代码中间的错误注释。"""
    lines = content.split('\n')
    result = []
    
    for line in lines:
        # 移除行尾的错误注释模式
        # 但保留正常的注释
        if '# 条件判断：处理业务逻辑' in line:
            line = line.replace('# 条件判断：处理业务逻辑', '').rstrip()
        if '# 执行' in line and '函数的核心逻辑' in line:
            line = line.replace(re.search(r'#\s*执行[^#\n]+函数的核心逻辑', line).group(0), '').rstrip()
        if '# 初始化变量' in line and line.strip().startswith('#'):
            # 如果整行都是注释，保留
            pass
        elif '# 初始化变量' in line:
            # 如果注释在代码后面，移除
            line = re.sub(r'\s*#\s*初始化变量\s+\w+', '', line).rstrip()
        
        result.append(line)
    
    return '\n'.join(result)


def fix_split_strings(content: str) -> str:
    """修复被拆分的字符串。"""
    # 修复类似：msg = f"规则数据文件不存在：\n    # 注释\n {path}"
    lines = content.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # 检查是否是不完整的字符串（以引号结尾但没有闭合）
        if '"' in line and line.count('"') % 2 == 1:
            # 检查下一行是否是注释，再下一行是否继续字符串
            if i + 2 < len(lines):
                next_line = lines[i + 1] if i + 1 < len(lines) else ""
                next_next_line = lines[i + 2] if i + 2 < len(lines) else ""
                
                if next_line.strip().startswith('#'):
                    # 尝试合并字符串
                    # 提取当前行的字符串部分
                    match = re.search(r'(["\'])(.*?)$', line)
                    if match:
                        quote = match.group(1)
                        str_start = match.group(2)
                        
                        # 提取下下行的字符串部分
                        match2 = re.search(rf'{quote}(.*?){quote}', next_next_line)
                        if match2:
                            str_end = match2.group(1)
                            # 合并字符串
                            combined = str_start + str_end
                            new_line = line[:match.start()] + quote + combined + quote + next_next_line[match2.end():]
                            result.append(new_line)
                            i += 3
                            continue
        
        result.append(line)
        i += 1
    
    return '\n'.join(result)


def fix_file(filepath: Path) -> bool:
    """修复单个文件。"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original = f.read()
        
        content = original
        
        # 应用各种修复
        content = fix_split_method_calls(content)
        content = fix_split_identifier(content)
        content = fix_inline_comments_in_code(content)
        content = fix_split_strings(content)
        
        # 写回文件
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
        
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")
        return False


def main():
    """主函数。"""
    # 修复所有Python文件
    backend_dir = Path(__file__).parent
    
    fixed_count = 0
    error_count = 0
    
    for py_file in backend_dir.rglob("*.py"):
        # 跳过这个修复脚本本身
        if py_file.name == "fix_all_syntax_final.py":
            continue
        
        # 跳过 __pycache__ 目录
        if "__pycache__" in str(py_file):
            continue
        
        if fix_file(py_file):
            print(f"Fixed: {py_file}")
            fixed_count += 1
    
    print(f"\nTotal fixed: {fixed_count}")


if __name__ == "__main__":
    main()
