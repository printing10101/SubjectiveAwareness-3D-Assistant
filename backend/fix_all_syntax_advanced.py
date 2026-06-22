"""全面修复所有Python文件中的语法错误 - 高级版本."""
import ast
import os
import re

def fix_file(filepath):
    """修复单个文件的语法错误."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 第一步：移除所有独立的错误注释行
        cleaned_lines = []
        for line in lines:
            if re.match(r'^\s*#\s*(条件判断|异常处理|捕获异常|返回处理结果|抛出异常|应用装饰器|函数.*的初始化逻辑|定义.*类|初始化变量|循环遍历|执行.*函数的核心逻辑|记录日志信息)[:：]', line):
                continue
            cleaned_lines.append(line)
        
        # 第二步：合并被拆分的字符串和标识符
        merged_lines = []
        i = 0
        while i < len(cleaned_lines):
            line = cleaned_lines[i].rstrip('\n\r')
            
            # 检查下一行是否是被拆分的延续
            if i + 1 < len(cleaned_lines):
                next_line = cleaned_lines[i + 1].rstrip('\n\r')
                
                # 情况1：字符串被拆分（当前行以未闭合的引号结尾，下一行以引号开头）
                if (line.rstrip().endswith('"') or line.rstrip().endswith("'")) and not line.rstrip().endswith('""') and not line.rstrip().endswith("''"):"') + line.count("'")
                    if quote_count % 2 == 1:  # 奇数个引号，说明字符串未闭合next_stripped = next_line.lstrip()
                        if next_stripped.startswith('"') or next_stripped.startswith("'"):
                            # 移除下一行开头的引号
                            next_stripped = next_stripped[1:]
                            line = line + next_stripped
                            i += 1
                            continue
                
                # 情况2：字符串字面量被拆分（如 "页码必须\n大于等于1"）
                if '"' in line and not line.strip().endswith(','):
                    # 检查当前行是否有未闭合的字符串
                    in_string = False
                    string_char = None
                    for j, char in enumerate(line):
                        if char in '"\'':
                            if not in_string:
                                in_string = True
                                string_char = char
                            elif char == string_char:
                                in_string = False
                                string_char = None
                    
                    if in_string:  # 字符串未闭合
                        next_stripped = next_line.lstrip()
                        # 移除下一行末尾的引号（如果有）
                        if next_stripped.endswith('",') or next_stripped.endswith('",'):
                            next_stripped = next_stripped[:-2] + '",'
                        elif next_stripped.endswith('"'):
                            next_stripped = next_stripped[:-1]
                        line = line + next_stripped
                        i += 1
                        continue
                
                # 情况3：标识符被拆分（如 is_cre\nator）
                if line.rstrip().endswith('_') or (line.rstrip() and line.rstrip()[-1].isalpha() and not line.strip().startswith('#') and not line.strip().startswith('def ') and not line.strip().startswith('class ')):
                    next_stripped = next_line.lstrip()
                    if next_stripped and (next_stripped[0].isalpha() or next_stripped[0] == '_'):
                        # 检查是否是标识符的一部分
                        if not line.rstrip().endswith(':') and not line.rstrip().endswith('=') and not line.rstrip().endswith('(') and not line.rstrip().endswith(','):
                            line = line.rstrip() + next_stripped
                            i += 1
                            continue
                
                # 情况4：f-string 被拆分
                if "f'" in line or 'f"' in line:
                    quote_count = line.count('"') + line.count("'")
                    if quote_count % 2 == 1:
                        next_stripped = next_line.lstrip()
                        line = line + next_stripped
                        i += 1
                        continue
            
            merged_lines.append(line)
            i += 1
        
        # 第三步：修复缩进问题
        fixed_lines = []
        for i, line in enumerate(merged_lines):
            # 检查是否是需要增加缩进的行（在 if/for/while/def/class 后面）
            if i > 0:
                prev_line = merged_lines[i - 1]
                prev_stripped = prev_line.rstrip()
                
                # 如果上一行以冒号结尾，当前行应该增加缩进
                if prev_stripped.endswith(':') and not prev_stripped.startswith('#'):
                    current_indent = len(line) - len(line.lstrip())
                    prev_indent = len(prev_line) - len(prev_line.lstrip())
                    
                    if current_indent <= prev_indent and line.strip() and not line.strip().startswith('#'):
                        # 需要增加缩进
                        line = ' ' * (prev_indent + 4) + line.lstrip()
            
            fixed_lines.append(line)
        
        # 第四步：移除行尾的错误注释
        final_lines = []
        for line in fixed_lines:
            line = re.sub(r'\s*#\s*(条件判断|异常处理|捕获异常|返回处理结果|抛出异常|应用装饰器|函数.*的初始化逻辑|定义.*类|初始化变量|循环遍历|执行.*函数的核心逻辑|记录日志信息)[:：].*$', '', line)
            final_lines.append(line)
        
        # 写回文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(final_lines))
        
        return True
    except Exception as e:
        print(f"处理 {filepath} 时出错: {e}")
        import traceback
        traceback.print_exc()
        return Falsefiles_to_fix = [
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

fixed_count = 0
for filepath in files_to_fix:
    if os.path.exists(filepath):
        print(f"正在修复: {filepath}")
        if fix_file(filepath):
            fixed_count += 1
    else:
        print(f"文件不存在: {filepath}")

print(f"\n总共修复了 {fixed_count} 个文件")
