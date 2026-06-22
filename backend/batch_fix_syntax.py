"""批量修复语法错误"""
import re
import os

def fix_file(filepath):
    """修复单个文件的语法错误"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 移除错误插入的注释模式
        # 模式1: 代码中间被注释截断，如 "if labels    "
        if re.search(r'\S+\s+#\s*(条件判断|异常处理|循环遍历|检查|验证|处理).*：.*业务逻辑', line):
            # 提取注释前的代码部分
            code_part = re.split(r'\s+#\s*(条件判断|异常处理|循环遍历|检查|验证|处理)', line)[0]
            fixed_lines.append(code_part + '\n')
            i += 1
            continue
        
        # 模式2: 字符串被注释截断，如 "string    # 注释\n续"
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            # 检查当前行是否以未闭合的字符串结尾
            if re.search(r'["\'][^"\']*$', line) and re.search(r'^\s*#\s*(条件判断|异常处理|循环遍历)', next_line):
                # 跳过错误注释，合并下一行的字符串
                fixed_lines.append(line.rstrip() + '\n')
                i += 2  # 跳过错误注释行
                continue
        
        # 模式3: 代码被拆分到多行，如 "if labels\n    # 注释\n    续"
        if re.match(r'^\s*#\s*(条件判断|异常处理|循环遍历|检查|验证|处理).*：.*业务逻辑', line):
            # 跳过这行错误注释
            i += 1
            continue
        
        # 模式4: 移除独立的错误注释行
        if re.match(r'^\s*#\s*(条件判断|异常处理|循环遍历|检查|验证|处理)\s*[:：]\s*.*业务逻辑', line):
            i += 1
            continue
        
        fixed_lines.append(line)
        i += 1
    
    # 写回文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    return len(lines) != len(fixed_lines)

# 修复所有有语法错误的文件
files_to_fix = [
    'app/eval/statistical.py',
    'app/schemas/knowledge.py',
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
    'app/services/path_identifier.py',
    'app/services/prompt_manager.py',
    'app/services/real_judgment_loader.py',
    'app/services/report_exporter.py',
    'app/services/report_generator.py',
    'app/services/review_checklist.py',
    'app/services/rule_engine.py',
    'app/services/similar_cases.py',
    'app/services/standard_path_recognizer.py',
    'app/services/subject_stratifier.py',
    'app/services/system_service.py',
    'app/services/tag_extractor.py',
    'app/services/tier_combiner.py',
    'app/services/version_manager.py',
    'app/services/versioned_data_loader.py',
    'app/types/analysis_v2.py',
    'app/utils/anonymizer.py',
    'app/utils/cache.py',
    'app/utils/common.py',
]

fixed_count = 0
for filepath in files_to_fix:
    if os.path.exists(filepath):
        if fix_file(filepath):
            print(f"Fixed: {filepath}")
            fixed_count += 1
        else:
            print(f"No changes: {filepath}")
    else:
        print(f"Not found: {filepath}")

print(f"\nTotal fixed: {fixed_count} files")
