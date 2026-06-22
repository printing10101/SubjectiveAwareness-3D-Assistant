"""修复模块 docstring 格式错误。"""
import os

# 需要修复的文件列表
files_to_fix = [
    'app/eval/statistical.py',
    'app/schemas/user.py',
    'app/services/boundary_checker.py',
    'app/services/case_service.py',
    'app/services/conclusion_generator.py',
    'app/services/conflict_detector.py',
    'app/services/dedup_service.py',
    'app/services/document_processor.py',
    'app/services/evidence_layer.py',
    'app/services/evidence_strength_layer.py',
    'app/services/experiment.py',
    'app/services/knowledge_graph.py',
    'app/services/knowledge_graph_service.py',
    'app/services/knowledge_import_service.py',
    'app/services/knowledge_lifecycle_service.py',
    'app/services/knowledge_qa_service.py',
    'app/services/knowledge_relation_service.py',
    'app/services/knowledge_search_service.py',
    'app/services/knowledge_service.py',
    'app/services/multi_subject_analyzer.py',
]

def fix_docstring(filepath):
    """修复单个文件的 docstring。"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 检查前几行是否有问题
        if len(lines) < 3:
            return False
        
        # 如果第 1 行是空行，第 2 行是中文描述（没有 """），则需要修复
        if lines[0].strip() == '' and not lines[1].strip().startswith('"""'):
            # 找到 docstring 的结束位置（下一个空行或 from 语句）
            doc_end_idx = 2
            while doc_end_idx < len(lines):
                line = lines[doc_end_idx].strip()
                if line == '' or line.startswith('from ') or line.startswith('import '):
                    break
                doc_end_idx += 1
            
            # 构建新的 docstring
            module_desc = lines[1].strip()
            additional_lines = [lines[i].strip() for i in range(2, doc_end_idx) if lines[i].strip()]
            
            # 生成新的文件内容
            new_lines = ['"""模块说明。\n']
            new_lines.append('\n')
            new_lines.append(f'{module_desc}\n')
            for add_line in additional_lines:
                new_lines.append(f'{add_line}\n')
            new_lines.append('"""\n')
            new_lines.append('\n')
            
            # 添加剩余的内容
            new_lines.extend(lines[doc_end_idx:])
            
            # 写回文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            return True
        return False
    except Exception as e:
        print(f"修复 {filepath} 时出错: {e}")
        return Falsefixed_count = 0
for filepath in files_to_fix:
    if os.path.exists(filepath):
        print(f"正在修复: {filepath}")
        if fix_docstring(filepath):
            fixed_count += 1
            print(f"  ✓ 已修复")
        else:
            print(f"  - 无需修复")
    else:
        print(f"文件不存在: {filepath}")

print(f"\n总共修复了 {fixed_count} 个文件")
