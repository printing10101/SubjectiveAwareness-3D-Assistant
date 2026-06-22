"""批量修复因错误注释插入导致的语法错误."""
import re
from pathlib import PathBAD_COMMENT_PATTERNS = [
    r'#\s*条件判断：处理业务逻辑',
    r'#\s*异常处理：处理业务逻辑',
    r'#\s*捕获异常：处理业务逻辑',
]

def fix_file(file_path: Path) -> bool:
    """修复单个文件，返回是否进行了修改."""
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  跳过 {file_path.name}: {e}")
        return False
    
    original_content = content
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # 检查是否是纯注释行（只包含错误注释）
        stripped = line.strip()
        is_pure_bad_comment = any(
            re.fullmatch(pattern, stripped) 
            for pattern in BAD_COMMENT_PATTERNS
        )
        
        if is_pure_bad_comment:
            # 跳过纯错误注释行
            continuefixed_line = line
        for pattern in BAD_COMMENT_PATTERNS:
            # 移除行内的错误注释（保留代码部分）
            fixed_line = re.sub(r'\s+' + pattern, '', fixed_line)
            fixed_line = re.sub(pattern + r'\s*', '', fixed_line)
        
        fixed_lines.append(fixed_line)
    
    fixed_content = '\n'.join(fixed_lines)
    
    if fixed_content != original_content:
        file_path.write_text(fixed_content, encoding='utf-8')
        return True
    return False

def main():
    """主函数."""
    app_dir = Path('app')
    if not app_dir.exists():
        print("错误: 未找到 app 目录")
        return
    
    fixed_count = 0
    total_count = 0
    
    for py_file in app_dir.rglob('*.py'):
        total_count += 1
        if fix_file(py_file):
            fixed_count += 1
            print(f"  已修复: {py_file.relative_to(app_dir.parent)}")
    
    print(f"\n修复完成: {fixed_count}/{total_count} 个文件已修复")

if __name__ == '__main__':
    main()
