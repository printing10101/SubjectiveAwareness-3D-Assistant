"""修复被拆分的注释."""
import re
from pathlib import Path

def fix_split_comments(content: str) -> str:
    """修复被拆分的注释."""
    lines = content.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # 检查是否是拆分的注释（以 # 开头，但下一行没有缩进且不是 # 开头）
        if (i + 1 < len(lines) and 
            line.strip().startswith('#') and 
            lines[i + 1] and 
            not lines[i + 1].startswith(' ') and 
            not lines[i + 1].startswith('\t') and
            not lines[i + 1].strip().startswith('#') and
            not lines[i + 1].strip().startswith('def ') and
            not lines[i + 1].strip().startswith('class ') and
            not lines[i + 1].strip().startswith('import ') and
            not lines[i + 1].strip().startswith('from ') and
            not lines[i + 1].strip().startswith('return ') and
            not lines[i + 1].strip().startswith('if ') and
            not lines[i + 1].strip().startswith('else') and
            not lines[i + 1].strip().startswith('elif ') and
            not lines[i + 1].strip().startswith('try:') and
            not lines[i + 1].strip().startswith('except') and
            not lines[i + 1].strip().startswith('finally:') and
            not lines[i + 1].strip().startswith('with ') and
            not lines[i + 1].strip().startswith('for ') and
            not lines[i + 1].strip().startswith('while ') and
            not lines[i + 1].strip().startswith('raise ') and
            not lines[i + 1].strip().startswith('@') and
            len(lines[i + 1].strip()) > 0 and
            not any(keyword in lines[i + 1] for keyword in ['=', '(', ')', '[', ']', '{', '}', '.', ',', ';', ':'])):
            
            # 合并下一行到当前注释
            result.append(line + ' ' + lines[i + 1].strip())
            i += 2
        else:
            result.append(line)
            i += 1
    
    return '\n'.join(result)

def fix_file(file_path: Path) -> bool:
    """修复单个文件."""
    try:
        content = file_path.read_text(encoding="utf-8")
        fixed_content = fix_split_comments(content)
        
        if fixed_content != content:
            file_path.write_text(fixed_content, encoding="utf-8")
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """主函数."""
    backend_dir = Path("backend")
    fixed_count = 0
    
    for py_file in backend_dir.rglob("*.py"):
        if fix_file(py_file):
            fixed_count += 1
            print(f"Fixed: {py_file}")
    
    print(f"\nTotal fixed: {fixed_count} files")

if __name__ == "__main__":
    main()
