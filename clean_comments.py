"""清理自动生成的无用注释."""
import re
from pathlib import Path

# 要删除的注释模式
patterns_to_remove = [
    r"# 条件判断：处理业务逻辑",
    r"# 异常处理：处理业务逻辑",
    r"# 初始化变量 \w+",
    r"# 返回处理结果",
    r"# 执行 \w+ 函数的核心逻辑",
    r"# 导入模块: from [\w\.]+",
    r"# 捕获并处理异常",
    r"# 其他情况的默认处理",
]

def clean_file(file_path: Path) -> bool:
    """清理单个文件."""
    try:
        content = file_path.read_text(encoding="utf-8")
        original_content = content
        
        for pattern in patterns_to_remove:
            # 删除整行注释
            content = re.sub(rf"^\s*{pattern}\s*\n", "", content, flags=re.MULTILINE)
            # 删除行尾注释
            content = re.sub(rf"\s*{pattern}\s*$", "", content, flags=re.MULTILINE)
        
        if content != original_content:
            file_path.write_text(content, encoding="utf-8")
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """主函数."""
    backend_dir = Path("backend")
    cleaned_count = 0
    
    for py_file in backend_dir.rglob("*.py"):
        if clean_file(py_file):
            cleaned_count += 1
            print(f"Cleaned: {py_file}")
    
    print(f"\nTotal cleaned: {cleaned_count} files")

if __name__ == "__main__":
    main()
