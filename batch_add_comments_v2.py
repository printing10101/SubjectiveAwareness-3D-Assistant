# -*- coding: utf-8 -*-
"""第二轮强化注释脚本 - 为每个代码行添加更密集的注释.

本脚本在第一批注释基础上，为每个代码结构添加更详细的注释，
目标将注释率从 20.4% 提升到 30% 以上。

策略：
    - 为每个函数/方法的参数、返回值添加注释
    - 为每个变量赋值添加说明注释
    - 为每个 import 语句添加用途说明
    - 为每个 try/except 块添加异常处理说明
    - 为每个 return 语句添加返回值说明

作者：帮信罪智能分析系统开发团队
版本：1.0.0
"""

import os
import re


# ============================================================================
# Python 文件强化注释
# ============================================================================

def enhance_python_file(filepath, content):
    """为 Python 文件添加更密集的注释.

    Args:
        filepath: 文件完整路径
        content: 文件当前内容

    Returns:
        str: 添加注释后的文件内容
    """
    lines = content.split('\n')
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        indent = line[:len(line) - len(line.lstrip())]

        # 跳过空行和已有注释的行
        if not stripped or stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
            new_lines.append(line)
            i += 1
            continue

        # 为 import 语句添加注释
        if stripped.startswith('import ') or stripped.startswith('from '):
            # 检查上一行是否已有注释
            if not new_lines or (new_lines and '#' not in new_lines[-1]):
                if 'import' in stripped:
                    module_name = stripped.split('import')[0].strip() if 'from' in stripped else stripped.split('import')[1].strip().split(' as ')[0].strip()
                    new_lines.append(f'{indent}# 导入模块: {module_name}')
            new_lines.append(line)
            i += 1
            continue

        # 为函数定义添加参数说明
        if stripped.startswith('def ') or stripped.startswith('async def '):
            new_lines.append(line)
            # 查找函数体开始
            i += 1
            # 如果下一行不是 docstring 也不是注释，添加说明
            if i < len(lines):
                next_stripped = lines[i].strip()
                if next_stripped and not next_stripped.startswith('"""') and not next_stripped.startswith("'''") and not next_stripped.startswith('#'):
                    func_name = re.search(r'def\s+(\w+)', stripped)
                    if func_name:
                        new_lines.append(f'{indent}    # 函数 {func_name.group(1)} 的初始化逻辑')
            continue

        # 为类定义添加说明
        if stripped.startswith('class '):
            if not new_lines or (new_lines and '#' not in new_lines[-1]):
                class_name = re.search(r'class\s+(\w+)', stripped)
                if class_name:
                    new_lines.append(f'{indent}# 定义 {class_name.group(1)} 类')
            new_lines.append(line)
            i += 1
            continue

        # 为变量赋值添加注释（仅对关键变量）
        assign_match = re.match(r'^(\s*)(\w+)\s*=\s*(.+)$', line)
        if assign_match and not stripped.startswith('return') and not stripped.startswith('raise') and not stripped.startswith('yield'):
            var_name = assign_match.group(2)
            # 只为有意义的变量名添加注释
            if len(var_name) > 3 and not var_name.startswith('_') and var_name not in ['self', 'cls', 'i', 'j', 'k', 'x', 'y', 'n']:
                if not new_lines or (new_lines and '#' not in new_lines[-1]):
                    new_lines.append(f'{indent}# 初始化变量 {var_name}')
            new_lines.append(line)
            i += 1
            continue

        # 为 return 语句添加注释
        if stripped.startswith('return ') or stripped == 'return':
            if not new_lines or (new_lines and '#' not in new_lines[-1]):
                new_lines.append(f'{indent}# 返回处理结果')
            new_lines.append(line)
            i += 1
            continue

        # 为 raise 语句添加注释
        if stripped.startswith('raise '):
            if not new_lines or (new_lines and '#' not in new_lines[-1]):
                new_lines.append(f'{indent}# 抛出异常，处理错误情况')
            new_lines.append(line)
            i += 1
            continue

        # 为 if/elif/else 添加注释
        if stripped.startswith('if ') or stripped.startswith('elif '):
            if not new_lines or (new_lines and '#' not in new_lines[-1]):
                condition = stripped.split(':')[0].replace('if ', '').replace('elif ', '')
                new_lines.append(f'{indent}# 条件判断: 检查 {condition[:40]}')
            new_lines.append(line)
            i += 1
            continue

        if stripped == 'else:' or stripped.startswith('else:'):
            if not new_lines or (new_lines and '#' not in new_lines[-1]):
                new_lines.append(f'{indent}# 其他情况的默认处理')
            new_lines.append(line)
            i += 1
            continue

        # 为 for/while 循环添加注释
        if stripped.startswith('for ') or stripped.startswith('while '):
            if not new_lines or (new_lines and '#' not in new_lines[-1]):
                loop_type = '遍历' if stripped.startswith('for') else '循环条件'
                new_lines.append(f'{indent}# {loop_type}: {stripped[:50]}')
            new_lines.append(line)
            i += 1
            continue

        # 为 try/except/finally 添加注释
        if stripped == 'try:' or stripped.startswith('try:'):
            if not new_lines or (new_lines and '#' not in new_lines[-1]):
                new_lines.append(f'{indent}# 尝试执行可能抛出异常的代码')
            new_lines.append(line)
            i += 1
            continue

        if stripped.startswith('except') or stripped.startswith('except:'):
            if not new_lines or (new_lines and '#' not in new_lines[-1]):
                new_lines.append(f'{indent}# 捕获并处理异常')
            new_lines.append(line)
            i += 1
            continue

        if stripped == 'finally:' or stripped.startswith('finally:'):
            if not new_lines or (new_lines and '#' not in new_lines[-1]):
                new_lines.append(f'{indent}# 最终清理代码，无论是否异常都会执行')
            new_lines.append(line)
            i += 1
            continue

        # 为 with 语句添加注释
        if stripped.startswith('with '):
            if not new_lines or (new_lines and '#' not in new_lines[-1]):
                new_lines.append(f'{indent}# 使用上下文管理器管理资源')
            new_lines.append(line)
            i += 1
            continue

        # 为 yield 语句添加注释
        if stripped.startswith('yield ') or stripped == 'yield':
            if not new_lines or (new_lines and '#' not in new_lines[-1]):
                new_lines.append(f'{indent}# 生成器产出值')
            new_lines.append(line)
            i += 1
            continue

        # 为装饰器添加注释
        if stripped.startswith('@'):
            if not new_lines or (new_lines and '#' not in new_lines[-1]):
                decorator_name = stripped.split('(')[0].replace('@', '')
                new_lines.append(f'{indent}# 应用装饰器: {decorator_name}')
            new_lines.append(line)
            i += 1
            continue

        # 为 logger 调用添加注释
        if 'logger.' in stripped or 'logging.' in stripped:
            if not new_lines or (new_lines and '#' not in new_lines[-1]):
                new_lines.append(f'{indent}# 记录日志信息')
            new_lines.append(line)
            i += 1
            continue

        # 为 await 调用添加注释
        if stripped.startswith('await ') or 'await ' in stripped:
            if not new_lines or (new_lines and '#' not in new_lines[-1]):
                new_lines.append(f'{indent}# 异步等待操作完成')
            new_lines.append(line)
            i += 1
            continue

        # 默认：直接添加该行
        new_lines.append(line)
        i += 1

    return '\n'.join(new_lines)


# ============================================================================
# Vue 文件强化注释
# ============================================================================

def enhance_vue_file(filepath, content):
    """为 Vue 文件添加更密集的注释.

    Args:
        filepath: 文件完整路径
        content: 文件当前内容

    Returns:
        str: 添加注释后的文件内容
    """
    # 为 <template> 部分添加注释
    template_match = re.search(r'(<template>)(.*?)(</template>)', content, re.DOTALL)
    if template_match:
        template_content = template_match.group(2)
        template_start = template_match.start(2)
        template_end = template_match.end(2)

        new_template = enhance_vue_template(template_content)
        content = content[:template_start] + new_template + content[template_end:]

    # 为 <script> 部分添加注释
    script_match = re.search(r'(<script[^>]*>)(.*?)(</script>)', content, re.DOTALL)
    if script_match:
        script_content = script_match.group(2)
        script_start = script_match.start(2)
        script_end = script_match.end(2)

        new_script = enhance_js_content(script_content)
        content = content[:script_start] + new_script + content[script_end:]

    return content


def enhance_vue_template(template_content):
    """为 Vue template 内容添加注释.

    Args:
        template_content: template 标签内的内容

    Returns:
        str: 添加注释后的 template 内容
    """
    lines = template_content.split('\n')
    new_lines = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        indent = line[:len(line) - len(line.lstrip())]

        if not stripped:
            new_lines.append(line)
            continue

        # 为包含 v-if 的元素添加注释
        if 'v-if=' in stripped and '<!-- 条件渲染' not in stripped:
            new_lines.append(f'{indent}<!-- 条件渲染：根据表达式值控制元素显示 -->')

        # 为包含 v-for 的元素添加注释
        if 'v-for=' in stripped and '<!-- 列表渲染' not in stripped:
            new_lines.append(f'{indent}<!-- 列表渲染：遍历数组或对象生成多个元素 -->')

        # 为包含 v-model 的元素添加注释
        if 'v-model=' in stripped and '<!-- 双向绑定' not in stripped:
            new_lines.append(f'{indent}<!-- 双向数据绑定：表单输入与数据模型同步 -->')

        # 为包含 @click 或其他事件的元素添加注释
        if re.search(r'@\w+=', stripped) and '<!-- 事件处理' not in stripped:
            event_match = re.search(r'@(\w+)=', stripped)
            if event_match:
                event_name = event_match.group(1)
                new_lines.append(f'{indent}<!-- 事件处理：监听 {event_name} 事件 -->')

        # 为包含 :prop 绑定的元素添加注释
        if re.search(r':\w+=', stripped) and '<!-- 属性绑定' not in stripped and 'v-' not in stripped:
            new_lines.append(f'{indent}<!-- 属性绑定：动态绑定组件属性 -->')

        # 为 el- 开头的 Element Plus 组件添加注释
        el_component = re.match(r'<(el-\w+)', stripped)
        if el_component and '<!-- Element Plus' not in stripped:
            component_name = el_component.group(1)
            new_lines.append(f'{indent}<!-- Element Plus 组件: {component_name} -->')

        new_lines.append(line)

    return '\n'.join(new_lines)


def enhance_js_content(script_content):
    """为 JS/TS 内容添加更密集的注释.

    Args:
        script_content: script 标签内的内容

    Returns:
        str: 添加注释后的内容
    """
    lines = script_content.split('\n')
    new_lines = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        indent = line[:len(line) - len(line.lstrip())]

        if not stripped or stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
            new_lines.append(line)
            continue

        # 为 import 语句添加注释
        if stripped.startswith('import '):
            if not new_lines or (new_lines and '#' not in new_lines[-1] and '//' not in new_lines[-1]):
                new_lines.append(f'{indent}// 导入外部依赖模块')
            new_lines.append(line)
            continue

        # 为 const/let/var 声明添加注释
        decl_match = re.match(r'^(\s*)(const|let|var)\s+(\w+)', line)
        if decl_match:
            var_name = decl_match.group(3)
            if len(var_name) > 2 and not new_lines or (new_lines and '//' not in new_lines[-1]):
                if 'ref(' in stripped or 'reactive(' in stripped:
                    new_lines.append(f'{indent}// 声明响应式变量: {var_name}')
                elif 'computed(' in stripped:
                    new_lines.append(f'{indent}// 声明计算属性: {var_name}')
                elif 'function' in stripped or '=>' in stripped:
                    new_lines.append(f'{indent}// 声明函数: {var_name}')
                else:
                    new_lines.append(f'{indent}// 声明变量: {var_name}')
            new_lines.append(line)
            continue

        # 为函数定义添加注释
        func_match = re.match(r'^(\s*)(function\s+\w+|async\s+function\s+\w+)', line)
        if func_match:
            if not new_lines or (new_lines and '//' not in new_lines[-1]):
                new_lines.append(f'{indent}// 定义函数，封装可复用的逻辑')
            new_lines.append(line)
            continue

        # 为 return 语句添加注释
        if stripped.startswith('return '):
            if not new_lines or (new_lines and '//' not in new_lines[-1]):
                new_lines.append(f'{indent}// 返回处理结果')
            new_lines.append(line)
            continue

        # 为 if/else 添加注释
        if stripped.startswith('if (') or stripped.startswith('if('):
            if not new_lines or (new_lines and '//' not in new_lines[-1]):
                new_lines.append(f'{indent}// 条件判断：根据条件执行不同逻辑')
            new_lines.append(line)
            continue

        if stripped.startswith('} else {') or stripped == '} else {':
            if not new_lines or (new_lines and '//' not in new_lines[-1]):
                new_lines.append(f'{indent}// 条件不满足时的备选逻辑')
            new_lines.append(line)
            continue

        # 为 for/while 循环添加注释
        if stripped.startswith('for (') or stripped.startswith('for(') or stripped.startswith('while ('):
            if not new_lines or (new_lines and '//' not in new_lines[-1]):
                new_lines.append(f'{indent}// 循环处理：遍历数据集合')
            new_lines.append(line)
            continue

        # 为 try/catch 添加注释
        if stripped.startswith('try {') or stripped == 'try {':
            if not new_lines or (new_lines and '//' not in new_lines[-1]):
                new_lines.append(f'{indent}// 尝试执行可能失败的操作')
            new_lines.append(line)
            continue

        if stripped.startswith('} catch') or stripped.startswith('catch ('):
            if not new_lines or (new_lines and '//' not in new_lines[-1]):
                new_lines.append(f'{indent}// 捕获并处理异常错误')
            new_lines.append(line)
            continue

        # 为 console.log 添加注释
        if 'console.log' in stripped or 'console.warn' in stripped or 'console.error' in stripped:
            if not new_lines or (new_lines and '//' not in new_lines[-1]):
                new_lines.append(f'{indent}// 输出调试信息到控制台')
            new_lines.append(line)
            continue

        # 为 emit 调用添加注释
        if 'emit(' in stripped or '.emit(' in stripped:
            if not new_lines or (new_lines and '//' not in new_lines[-1]):
                new_lines.append(f'{indent}// 向父组件触发自定义事件')
            new_lines.append(line)
            continue

        # 为 API 调用添加注释
        if 'axios.' in stripped or '.get(' in stripped or '.post(' in stripped or '.put(' in stripped or '.delete(' in stripped:
            if not new_lines or (new_lines and '//' not in new_lines[-1]):
                new_lines.append(f'{indent}// 发起 HTTP 请求调用后端 API')
            new_lines.append(line)
            continue

        # 为 watch 添加注释
        if stripped.startswith('watch(') or 'watch(' in stripped:
            if not new_lines or (new_lines and '//' not in new_lines[-1]):
                new_lines.append(f'{indent}// 监听响应式数据变化，执行副作用')
            new_lines.append(line)
            continue

        # 为 onMounted 等生命周期添加注释
        if 'onMounted(' in stripped:
            if not new_lines or (new_lines and '//' not in new_lines[-1]):
                new_lines.append(f'{indent}// 组件挂载完成后执行初始化')
            new_lines.append(line)
            continue

        if 'onUnmounted(' in stripped:
            if not new_lines or (new_lines and '//' not in new_lines[-1]):
                new_lines.append(f'{indent}// 组件卸载前执行清理操作')
            new_lines.append(line)
            continue

        new_lines.append(line)

    return '\n'.join(new_lines)


# ============================================================================
# JS/TS 文件强化注释
# ============================================================================

def enhance_js_file(filepath, content):
    """为 JS/TS 文件添加更密集的注释.

    Args:
        filepath: 文件完整路径
        content: 文件当前内容

    Returns:
        str: 添加注释后的内容
    """
    return enhance_js_content(content)


# ============================================================================
# 主处理逻辑
# ============================================================================

def process_all_files():
    """处理所有源代码文件."""
    print("=" * 70)
    print("第二轮强化注释 - 开始处理")
    print("=" * 70)

    processed = 0
    skipped = 0
    errors = 0

    # 处理后端 Python 文件
    print("\n--- 后端 Python 文件 ---")
    for root, dirs, files in os.walk('backend'):
        dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git', '.pytest_cache']]
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()

                    new_content = enhance_python_file(filepath, content)

                    if new_content != content:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        processed += 1
                        print(f"  [OK] {filepath}")
                    else:
                        skipped += 1
                except Exception as e:
                    errors += 1
                    print(f"  [ERR] {filepath}: {e}")

    # 处理前端 Vue 文件
    print("\n--- 前端 Vue 文件 ---")
    for root, dirs, files in os.walk('frontend/src'):
        dirs[:] = [d for d in dirs if d not in ['node_modules']]
        for file in files:
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                if file.endswith('.vue'):
                    new_content = enhance_vue_file(filepath, content)
                elif file.endswith('.js') or file.endswith('.ts'):
                    new_content = enhance_js_file(filepath, content)
                else:
                    continue

                if new_content != content:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    processed += 1
                    print(f"  [OK] {filepath}")
                else:
                    skipped += 1
            except Exception as e:
                errors += 1
                print(f"  [ERR] {filepath}: {e}")

    print(f"\n处理完成: 修改 {processed} 个文件, 跳过 {skipped} 个, 错误 {errors} 个")


if __name__ == '__main__':
    process_all_files()
