"""智能修复所有语法错误"""
import re
import os
import ast

def fix_syntax_errors(content):
    """修复各种语法错误"""
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # 1. 移除错误插入的注释模式
        # 匹配: 代码后的 "    " 或类似
        if re.search(r'\S\s{2,}#\s*(条件判断|异常处理|循环遍历|检查|验证|处理|初始化|执行|返回|应用|导入).*[:：].*业务逻辑', line):
            # 只保留注释前的代码部分
            code_part = re.split(r'\s{2,}#\s*(条件判断|异常处理|循环遍历|检查|验证|处理|初始化|执行|返回|应用|导入)', line)[0]
            fixed_lines.append(code_part.rstrip())
            i += 1
            continue
        
        # 2. 移除独立的错误注释行
        if re.match(r'^\s{2,}#\s*(条件判断|异常处理|循环遍历|检查|验证|处理|初始化|执行|返回|应用|导入)\s*[:：]\s*.*业务逻辑', line):
            i += 1
            continue
        
        # 3. 处理字符串被截断的情况
        # 检查当前行是否以未闭合的字符串结尾
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            
            # 检查是否是字符串截断（当前行有奇数个引号，下一行继续）
            if line.count('"') % 2 == 1 and next_line.strip() and not next_line.strip().startswith('#'):
                # 合并当前行和下一行
                combined = line.rstrip() + next_line.strip()
                # 检查合并后是否完整
                if combined.count('"') % 2 == 0:
                    fixed_lines.append(combined)
                    i += 2
                    continue
            
            # 检查f-string截断
            if 'f"' in line and line.count('"') % 2 == 1 and next_line.strip():
                combined = line.rstrip() + next_line.strip()
                if combined.count('"') % 2 == 0:
                    fixed_lines.append(combined)
                    i += 2
                    continue
        
        # 4. 处理代码被拆分到多行的情况
        # 检查是否是变量名/函数名被拆分
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            
            # 检查是否是代码拆分（当前行以不完整的标识符结尾）
            if re.search(r'[a-zA-Z_]\s*$', line) and re.match(r'^\s*[a-zA-Z_]', next_line):
                # 检查是否是错误注释导致的拆分
                if i + 2 < len(lines) and re.match(r'^\s*#\s*(条件判断|异常处理|循环遍历)', lines[i + 1]):
                    # 跳过错误注释，合并代码
                    combined = line.rstrip() + next_line.strip()
                    fixed_lines.append(combined)
                    i += 3  # 跳过当前行、注释行、下一行
                    continue
        
        fixed_lines.append(line)
        i += 1
    
    return '\n'.join(fixed_lines)

def fix_file(filepath):
    """修复单个文件"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 先尝试解析，如果没有错误就不需要修复
        try:
            ast.parse(content)
            return False  # 没有语法错误
        except SyntaxError:
            passfixed_content = fix_syntax_errors(content)
        
        # 验证修复后的代码
        try:
            ast.parse(fixed_content)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True
        except SyntaxError as e:
            print(f"  Still has errors after fix: {e}")
            return False
            
    except Exception as e:
        print(f"  Error processing {filepath}: {e}")
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

print("开始修复语法错误...")
fixed_count = 0
for filepath in files:
    if os.path.exists(filepath):
        print(f"处理: {filepath}")
        if fix_file(filepath):
            print(f"  ✓ 已修复")
            fixed_count += 1
        else:
            print(f"  ✗ 未能修复或无需修复")
    else:
        print(f"  ✗ 文件不存在")

print(f"\n修复完成: {fixed_count}/{len(files)} 个文件")
