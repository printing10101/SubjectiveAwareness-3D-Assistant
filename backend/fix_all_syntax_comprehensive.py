"""全面修复所有Python文件的语法错误."""
import ast
import os
import re

def fix_file(filepath):
    """修复单个文件的语法错误."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = contentcontent = re.sub(r'^\s*#\s*条件判断[:：]处理业务逻辑\s*\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*#\s*异常处理[:：]处理业务逻辑\s*\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*#\s*捕获异常[:：]处理业务逻辑\s*\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*#\s*返回处理结果\s*\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*#\s*抛出异常.*\s*\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*#\s*应用装饰器[:：].*\s*\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*#\s*函数.*的初始化逻辑\s*\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*#\s*定义.*类\s*\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*#\s*条件判断[:：]检查.*\s*\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*#\s*初始化变量.*\s*\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*#\s*循环遍历[:：]处理业务逻辑\s*\n', '', content, flags=re.MULTILINE)
        
        # 2. 移除行尾的错误注释
        content = re.sub(r'\s*#\s*条件判断[:：]处理业务逻辑\s*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'\s*#\s*异常处理[:：]处理业务逻辑\s*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'\s*#\s*捕获异常[:：]处理业务逻辑\s*$', '', content, flags=re.MULTILINE)
        
        # 3. 修复被拆分的字符串
        content = re.sub(r'"\s*#\s*条件判断[:：]处理业务逻辑\s*\n\s*"([^"]+)"', r'"\1"', content)
        content = re.sub(r'"\s*#\s*异常处理[:：]处理业务逻辑\s*\n\s*"([^"]+)"', r'"\1"', content)
        
        # 4. 修复被拆分的代码
        content = re.sub(r'(async\s+w)\s*#\s*异常处理[:：]处理业务逻辑\s*\n\s*(ith\s+)', r'\1\2', content)
        content = re.sub(r'(result\.scalar_one_or_n)\s*#\s*条件判断[:：]处理业务逻辑\s*\n\s*(one\(\))', r'\1\2', content)
        content = re.sub(r'(cipher_suite\.decrypt\(val)\s*#\s*捕获异常[:：]处理业务逻辑\s*\n\s*(ue\.encode\(\)\)\.decode\(\))', r'\1\2', content)
        content = re.sub(r'("WWW-Authentica)\s*#\s*异常处理[:：]处理业务逻辑\s*\n\s*(te":\s*"Bearer"\s*,?\s*})', r'\1\2', content)
        content = re.sub(r'(remaining_sec)\s*\n\s*#\s*条件判断[:：]处理业务逻辑\s*\n\s*(onds\s*=\s*int\()', r'\1\2', content)
        
        # 5. 修复缩进问题 - 确保if块内的代码正确缩进
        lines = content.split('\n')
        fixed_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # 检查是否是if语句后的错误缩进
            if i > 0 and 'if ' in lines[i-1] and line.strip() and not line.startswith(' ' * (len(lines[i-1]) - len(lines[i-1].lstrip()) + 4)):
                # 尝试修复缩进
                if line.strip() and not line.startswith(' '):
                    # 这行应该有缩进但没有
                    indent_level = len(lines[i-1]) - len(lines[i-1].lstrip())
                    line = ' ' * (indent_level + 4) + line.lstrip()
            fixed_lines.append(line)
            i += 1
        content = '\n'.join(fixed_lines)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"处理 {filepath} 时出错: {e}")
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
        if fix_file(filepath):
            print(f"已修复: {filepath}")
            fixed_count += 1
        else:
            print(f"无需修复: {filepath}")
    else:
        print(f"文件不存在: {filepath}")

print(f"\n总共修复了 {fixed_count} 个文件")
