"""全面修复所有语法错误."""
import re
from pathlib import Path

def fix_file(file_path: Path, fixes: list[tuple[str, str]]) -> bool:
    """修复单个文件."""
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  跳过 {file_path}: {e}")
        return False
    
    original = content
    for old, new in fixes:
        content = content.replace(old, new)
    
    if content != original:
        file_path.write_text(content, encoding='utf-8')
        print(f"  已修复: {file_path}")
        return True
    return False

def main():
    """主函数."""
    print("开始全面语法修复...")
    
    # confusion_matrix.py
    fix_file(Path('app/eval/confusion_matrix.py'), [
        ('        row_str = f"{labels[i][:cell_width]:<{cell_width}} | "\n\n\n    \n        row_str',
         '        row_str = f"{labels[i][:cell_width]:<{cell_width}} | "\n        row_str'),
    ])
    
    # statistical.py
    fix_file(Path('app/eval/statistical.py'), [
        ('    q25 = _percentile(sorted_vals, 25.0)\n  q75',
         '    q25 = _percentile(sorted_vals, 25.0)\n    q75'),
    ])
    
    # routers/knowledge.py
    fix_file(Path('app/routers/knowledge.py'), [
        ('    response_model=KnowledgeEntryResponse,\n\n    status_code',
         '    response_model=KnowledgeEntryResponse,\n    status_code'),
    ])
    
    # routers/labels.py
    fix_file(Path('app/routers/labels.py'), [
        ('        )\n    # 返回处理结果\n    return case',
         '        )\n    return case'),
    ])
    
    # routers/reports.py
    fix_file(Path('app/routers/reports.py'), [
        ('    report_id: int,\n    # 函数 submit_review 的初始化逻辑\n    request: ReviewRequest,',
         '    report_id: int,\n    request: ReviewRequest,'),
    ])
    
    # schemas/knowledge.py
    fix_file(Path('app/schemas/knowledge.py'), [
        ('    page: int = Field(..., ge=1, description="页码")\n  page_size',
         '    page: int = Field(..., ge=1, description="页码")\n    page_size'),
    ])
    
    # schemas/user.py
    fix_file(Path('app/schemas/user.py'), [
        ('        return username\n    # 应用装饰器: field_validator\n    @field_validator("password")\n    # 应用装饰器: classmethod\n    @classmethod\n    def validate_password',
         '        return username\n\n    @field_validator("password")\n    @classmethod\n    def validate_password'),
    ])
    
    # services/boundary_checker.py
    fix_file(Path('app/services/boundary_checker.py'), [
        ('            texts.append(\nstr(case.case_text))',
         '            texts.append(str(case.case_text))'),
        ('        # 条件判断: 检查 hasattr(case, "case_facts") and case.cas\n        if hasattr(case, "case_facts") and case.case_facts:\n            texts.append(\nstr(case.case_facts))',
         '        if hasattr(case, "case_facts") and case.case_facts:\n            texts.append(str(case.case_facts))'),
    ])
    
    # services/case_service.py
    fix_file(Path('app/services/case_service.py'), [
        ('    raise ValueError(f"无效的排序字段: {sort_by}")\n    # 构建查询语句\n    stmt = select(Case)\n    # 条件判断: 检查 user_id is not None\n    if user_id is not None:\n        stmt = stmt.where(Case.user_id == user_id)\n    # 条件判断: 检查 search_term\n    if search_term:\n\n        search_pattern = f"%{search_term}%"\n        # 条件判断: 检查 search_field == "all"',
         '    raise ValueError(f"无效的排序字段: {sort_by}")\n    stmt = select(Case)\n    if user_id is not None:\n        stmt = stmt.where(Case.user_id == user_id)\n    if search_term:\n        search_pattern = f"%{search_term}%"\n        if search_field == "all"'),
    ])
    
    print("\n修复完成!")

if __name__ == '__main__':
    main()
