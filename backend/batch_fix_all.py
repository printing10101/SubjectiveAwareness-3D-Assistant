"""批量修复所有语法错误 - 高级版本"""
import re
import os
import ast

def fix_all_syntax_errors(content):
    """修复所有类型的语法错误"""
    lines = content.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # 1. 移除错误插入的注释（在代码中间的）
        if re.search(r'\S\s{2,}#\s*(条件判断|异常处理|循环遍历|检查|验证|处理|初始化|执行|返回|应用|导入).*[:：].*业务逻辑', line):
            # 只保留注释前的代码部分
            code_part = re.split(r'\s{2,}#\s*(条件判断|异常处理|循环遍历|检查|验证|处理|初始化|执行|返回|应用|导入)', line)[0]
            result.append(code_part.rstrip())
            i += 1
            continue
        
        # 2. 移除独立的错误注释行（缩进错误的）
        if re.match(r'^\s{2,}#\s*(条件判断|异常处理|循环遍历|检查|验证|处理|初始化|执行|返回|应用|导入)\s*[:：]\s*.*业务逻辑', line):
            i += 1
            continue
        
        # 3. 处理字符串被截断的情况（跨行）
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            
            # 检查当前行是否以未闭合的字符串结尾
            if line.count('"') % 2 == 1 and next_line.strip() and not next_line.strip().startswith('#'):
                # 合并当前行和下一行
                combined = line.rstrip() + next_line.strip()
                if combined.count('"') % 2 == 0:
                    result.append(combined)
                    i += 2
                    continue
            
            # 检查f-string截断
            if 'f"' in line and line.count('"') % 2 == 1 and next_line.strip():
                combined = line.rstrip() + next_line.strip()
                if combined.count('"') % 2 == 0:
                    result.append(combined)
                    i += 2
                    continue
        
        # 4. 处理代码被拆分到多行的情况
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            
            # 检查是否是变量名/函数名被拆分（如 "for t" + "ag in v:"）
            if re.search(r'[a-zA-Z_]\s*$', line) and re.match(r'^\s*[a-zA-Z_]', next_line):
                # 检查中间是否有错误注释
                if i + 2 < len(lines) and re.match(r'^\s*#\s*(条件判断|异常处理|循环遍历)', lines[i + 1]):
                    # 跳过错误注释，合并代码
                    combined = line.rstrip() + next_line.strip()
                    result.append(combined)
                    i += 3
                    continue
                else:
                    # 直接合并
                    combined = line.rstrip() + next_line.strip()
                    result.append(combined)
                    i += 2
                    continue
        
        # 5. 处理缩进错误（如 "   stripped = v.strip()" 应该是 "        stripped = v.strip()"）
        if re.match(r'^\s{1,3}[a-z_]', line) and i > 0:
            # 检查前一行是否是正确的缩进
            prev_line = lines[i-1] if i > 0 else ""
            if prev_line and re.match(r'^\s{4,}', prev_line):
                # 修正缩进
                indent = len(prev_line) - len(prev_line.lstrip())
                result.append(' ' * indent + line.lstrip())
                i += 1
                continue
        
        result.append(line)
        i += 1
    
    return '\n'.join(result)

def fix_file(filepath):
    """修复单个文件"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 先尝试解析，如果没有错误就不需要修复
        try:
            ast.parse(content)
            return False, "No errors"
        except SyntaxError as e:
            passfixed_content = fix_all_syntax_errors(content)
        
        # 验证修复后的代码
        try:
            ast.parse(fixed_content)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True, "Fixed"
        except SyntaxError as e:
            return False, f"Still has errors: {e}"
            
    except Exception as e:
        return False, f"Error: {e}"

# 修复所有有语法错误的文件
files = [
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

print("开始批量修复语法错误...")
fixed = 0
failed = 0
for filepath in files:
    if os.path.exists(filepath):
        success, msg = fix_file(filepath)
        if success:
            print(f"✓ {filepath}")
            fixed += 1
        else:
            print(f"✗ {filepath}: {msg}")
            failed += 1

print(f"\n修复完成: {fixed} 成功, {failed} 失败")
