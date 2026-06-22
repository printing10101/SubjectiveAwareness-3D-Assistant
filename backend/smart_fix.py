"""智能修复被拆分的代码和截断的字符串"""
import re
import os

def fix_split_code(filepath):
    """修复被拆分的代码"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # 1. 修复被拆分的字符串（跨行的字符串）
    # 匹配: "文本\n续文" -> "文本续文"
    content = re.sub(r'"([^"]*)\n([^"]*)"', lambda m: f'"{m.group(1)}{m.group(2)}"', content)
    content = re.sub(r"'([^']*)\n([^']*)'", lambda m: f"'{m.group(1)}{m.group(2)}'", content)
    
    # 2. 修复被拆分的函数名、变量名、关键字patterns = [
        (r'ra\s*\nise', 'raise'),
        (r'if\s+labels\s*\n\s+is', 'if labels is'),
        (r'def\s+validate_passwo\s*\n\s*rd', 'def validate_password'),
        (r'_va\s*\nlidate', '_validate'),
        (r'matrix\s*=\s*\n', 'matrix = '),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    # 3. 移除错误的注释行（在代码中间的独立注释）
    # 匹配: 代码行后的独立注释行，如 "        # 初始化变量 xxx"
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 跳过纯注释行（如果它看起来像是错误插入的）
        if re.match(r'^\s*#\s*(初始化变量|条件判断|执行|遍历|抛出异常|返回处理)', line):
            # 检查是否是错误插入的注释（通常在代码中间）
            if i > 0 and i < len(lines) - 1:
                prev_line = lines[i-1].strip()
                next_line = lines[i+1].strip() if i+1 < len(lines) else ''
                # 如果前一行是代码，后一行也是代码，跳过这个注释
                if prev_line and not prev_line.startswith('#') and next_line and not next_line.startswith('#'):
                    i += 1
                    continue
        
        fixed_lines.append(line)
        i += 1
    
    content = '\n'.join(fixed_lines)
    
    # 4. 修复缩进问题lines = content.split('\n')
    fixed_lines = []
    for line in lines:
        # 保持原有缩进结构，只修复明显的错误
        if line and not line[0].isspace() and not line.startswith('#'):
            fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return Falsefiles = [
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

fixed = 0
for f in files:
    if os.path.exists(f):
        if fix_split_code(f):
            print(f"Fixed: {f}")
            fixed += 1

print(f"\nTotal fixed: {fixed} files")
