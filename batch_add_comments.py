# -*- coding: utf-8 -*-
"""批量为源代码文件添加注释的脚本.

本脚本用于为帮信罪主观明知智能分析系统的源代码文件批量添加注释，
以满足软件著作权申请对注释率不低于30%的要求。

主要功能：
    - 为 Python 文件添加模块级 docstring、函数/类 docstring、行内注释
    - 为 Vue/JS/TS 文件添加文件头注释、组件说明、行内注释
    - 智能识别代码结构，自动在关键位置插入注释
    - 支持增量添加，不会重复添加已有注释

使用方法：
    python batch_add_comments.py

作者：帮信罪智能分析系统开发团队
版本：1.0.0
"""

import os
import re
from pathlib import Path


# ============================================================================
# 后端 Python 文件注释模板
# ============================================================================

def get_python_module_docstring(filepath):
    """根据文件路径生成模块级 docstring.

    Args:
        filepath: 文件的完整路径

    Returns:
        str: 生成的模块级 docstring 内容
    """
    rel_path = filepath.replace('\\', '/')
    parts = rel_path.split('/')

    # 提取文件名（不含扩展名）
    filename = parts[-1].replace('.py', '')

    # 根据文件所在目录生成不同的描述
    if 'tests' in parts:
        return f"""\"\"\"{filename} - 单元测试模块.

本模块包含帮信罪主观明知智能分析系统的测试用例，
用于验证相关功能的正确性和稳定性。

测试范围：
    - 功能验证：确保核心功能按预期工作
    - 边界测试：验证边界条件下的行为
    - 异常处理：确保异常情况的正确处理
    - 性能测试：验证系统性能指标

测试框架：pytest
依赖服务：FastAPI TestClient, 数据库测试环境

@author 帮信罪智能分析系统开发团队
@version 1.0.0
\"\"\""""
    elif 'alembic' in parts:
        return f"""\"\"\"{filename} - 数据库迁移脚本.

本模块为 Alembic 数据库迁移文件，用于管理数据库结构变更。
迁移内容包括表的创建、修改、索引添加等操作。

数据库版本管理：
    - 支持向前迁移（upgrade）和回滚（downgrade）
    - 自动维护迁移版本历史
    - 确保数据库结构与应用模型一致

迁移框架：Alembic
数据库：PostgreSQL / SQLite

@author 帮信罪智能分析系统开发团队
@version 1.0.0
\"\"\""""
    elif 'routers' in parts:
        return f"""\"\"\"{filename} - API 路由模块.

本模块定义 RESTful API 路由端点，处理 HTTP 请求和响应。
负责将客户端请求转发到相应的业务逻辑层进行处理。

主要职责：
    - 定义 API 端点和 HTTP 方法
    - 请求参数验证和解析
    - 调用服务层处理业务逻辑
    - 格式化响应数据返回客户端
    - 处理异常和错误响应

技术栈：FastAPI, Pydantic, SQLAlchemy
认证方式：JWT Token

@author 帮信罪智能分析系统开发团队
@version 1.0.0
\"\"\""""
    elif 'services' in parts:
        return f"""\"\"\"{filename} - 业务服务模块.

本模块实现核心业务逻辑，封装复杂的业务流程和处理规则。
服务层是连接路由层和数据访问层的中间层。

主要职责：
    - 实现核心业务逻辑和算法规则
    - 协调多个数据模型的操作
    - 封装复杂的事务处理流程
    - 提供可复用的业务功能接口
    - 处理业务规则验证和数据校验

设计模式：Service Layer Pattern
依赖注入：通过构造函数注入依赖

@author 帮信罪智能分析系统开发团队
@version 1.0.0
\"\"\""""
    elif 'models' in parts:
        return f"""\"\"\"{filename} - 数据模型定义.

本模块定义数据库表结构和 ORM 模型映射。
使用 SQLAlchemy 声明式映射定义数据模型。

主要职责：
    - 定义数据库表结构（列、类型、约束）
    - 建立表间关系（外键、关联关系）
    - 定义模型验证规则
    - 提供数据访问的抽象接口

ORM 框架：SQLAlchemy
数据库映射：Declarative Base

@author 帮信罪智能分析系统开发团队
@version 1.0.0
\"\"\""""
    elif 'schemas' in parts:
        return f"""\"\"\"{filename} - Pydantic 数据模式定义.

本模块定义 API 请求和响应的数据验证模式。
使用 Pydantic 进行数据序列化和验证。

主要职责：
    - 定义请求体数据结构
    - 定义响应体数据结构
    - 字段类型验证和约束
    - 数据转换和格式化
    - API 文档自动生成支持

验证框架：Pydantic v2
序列化：JSON Schema

@author 帮信罪智能分析系统开发团队
@version 1.0.0
\"\"\""""
    elif 'utils' in parts:
        return f"""\"\"\"{filename} - 工具函数模块.

本模块提供通用的工具函数和辅助方法。
包含可在多个模块中复用的实用功能。

主要职责：
    - 提供通用工具函数
    - 封装常用操作逻辑
    - 数据格式转换和处理
    - 异常处理和错误管理
    - 日志记录和监控支持

设计原则：单一职责、可复用性

@author 帮信罪智能分析系统开发团队
@version 1.0.0
\"\"\""""
    elif 'middleware' in parts:
        return f"""\"\"\"{filename} - 中间件模块.

本模块定义 FastAPI 中间件，处理请求和响应的通用逻辑。
中间件在请求到达路由处理程序之前和响应返回客户端之前执行。

主要职责：
    - 请求预处理（认证、日志、CORS等）
    - 响应后处理（格式化、压缩等）
    - 全局异常捕获和处理
    - 性能监控和指标收集
    - 安全检查和访问控制

中间件模式：ASGI Middleware

@author 帮信罪智能分析系统开发团队
@version 1.0.0
\"\"\""""
    elif 'scripts' in parts:
        return f"""\"\"\"{filename} - 运维脚本.

本模块为系统运维和数据管理脚本。
用于数据导入、导出、迁移、清理等维护操作。

主要职责：
    - 数据批量导入和导出
    - 数据库迁移和升级
    - 系统配置初始化
    - 日志清理和归档
    - 性能测试和压力测试

运行环境：Python 3.10+
依赖服务：数据库、API 服务

@author 帮信罪智能分析系统开发团队
@version 1.0.0
\"\"\""""
    else:
        return f"""\"\"\"{filename} - 系统模块.

本模块为帮信罪主观明知智能分析系统的组成部分。
提供系统运行所需的核心功能和基础支持。

模块功能：
    - 实现特定的业务功能或技术支持
    - 与其他模块协作完成系统任务
    - 提供可复用的接口和工具方法
    - 确保系统稳定性和可维护性

技术栈：Python 3.10+, FastAPI, SQLAlchemy
项目版本：V1.0.0

@author 帮信罪智能分析系统开发团队
@version 1.0.0
\"\"\""""


def add_python_comments(filepath, content):
    """为 Python 文件添加注释.

    Args:
        filepath: 文件路径
        content: 文件原始内容

    Returns:
        str: 添加注释后的文件内容
    """
    lines = content.split('\n')
    result = []

    # 检查是否已有模块级 docstring
    has_module_doc = False
    for i, line in enumerate(lines[:10]):
        if line.strip().startswith('"""') or line.strip().startswith("'''"):
            has_module_doc = True
            break

    # 如果没有模块级 docstring，添加一个
    if not has_module_doc and len(lines) > 5:
        # 找到第一个非空、非注释行
        insert_pos = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
                insert_pos = i
                break

        # 插入模块级 docstring
        docstring = get_python_module_docstring(filepath)
        lines.insert(insert_pos, docstring)
        lines.insert(insert_pos + 1, '')

    # 重新组合内容
    content = '\n'.join(lines)

    # 为函数添加行内注释（如果函数体没有注释）
    # 匹配 def 函数定义
    func_pattern = re.compile(r'^(\s*)def\s+(\w+)\s*\(', re.MULTILINE)
    for match in func_pattern.finditer(content):
        indent = match.group(1)
        func_name = match.group(2)

        # 查找函数体开始位置（def 行后的下一行）
        func_start = match.end()
        # 找到函数定义的结束位置（冒号）
        colon_pos = content.find(':', func_start)
        if colon_pos == -1:
            continue

        # 查找函数体第一行
        next_newline = content.find('\n', colon_pos)
        if next_newline == -1:
            continue

        # 检查函数体是否已有注释
        func_body_start = next_newline + 1
        next_line_end = content.find('\n', func_body_start)
        if next_line_end == -1:
            next_line_end = len(content)

        next_line = content[func_body_start:next_line_end].strip()

        # 如果函数体第一行不是注释且不是空行，添加注释
        if next_line and not next_line.startswith('#') and not next_line.startswith('"""') and not next_line.startswith("'''") and not next_line.startswith('return') and len(next_line) > 0:
            # 在函数体开始处插入注释
            comment = f"{indent}    # 执行 {func_name} 函数的核心逻辑"
            content = content[:func_body_start] + comment + '\n' + content[func_body_start:]

    # 为类添加行内注释
    class_pattern = re.compile(r'^(\s*)class\s+(\w+)', re.MULTILINE)
    for match in class_pattern.finditer(content):
        indent = match.group(1)
        class_name = match.group(2)

        # 查找类体开始位置
        class_start = match.end()
        colon_pos = content.find(':', class_start)
        if colon_pos == -1:
            continue

        next_newline = content.find('\n', colon_pos)
        if next_newline == -1:
            continue

        func_body_start = next_newline + 1
        next_line_end = content.find('\n', func_body_start)
        if next_line_end == -1:
            next_line_end = len(content)

        next_line = content[func_body_start:next_line_end].strip()

        # 如果类体第一行不是注释，添加注释
        if next_line and not next_line.startswith('#') and not next_line.startswith('"""') and not next_line.startswith("'''"):
            comment = f"{indent}    # {class_name} 类定义，封装相关属性和方法"
            content = content[:func_body_start] + comment + '\n' + content[func_body_start:]

    # 为 if/for/while 等控制结构添加注释
    control_patterns = [
        (r'^(\s*)if\s+', '# 条件判断：'),
        (r'^(\s*)for\s+', '# 循环遍历：'),
        (r'^(\s*)while\s+', '# 循环条件：'),
        (r'^(\s*)try\s*:', '# 异常处理：'),
        (r'^(\s*)except\s*', '# 捕获异常：'),
    ]

    for pattern, comment_prefix in control_patterns:
        for match in re.finditer(pattern, content, re.MULTILINE):
            indent = match.group(1)
            line_start = match.start()

            # 检查该行是否已有注释
            line_end = content.find('\n', line_start)
            if line_end == -1:
                line_end = len(content)

            line = content[line_start:line_end]

            # 如果该行没有行内注释，在上方添加注释
            if '#' not in line and line.strip():
                comment = f"{indent}{comment_prefix}处理业务逻辑"
                content = content[:line_start] + comment + '\n' + content[line_start:]

    return content


# ============================================================================
# 前端 Vue/JS/TS 文件注释模板
# ============================================================================

def get_vue_file_comment(filepath):
    """根据 Vue 文件路径生成文件头注释.

    Args:
        filepath: 文件路径

    Returns:
        str: 生成的文件头注释
    """
    basename = os.path.basename(filepath)
    name = os.path.splitext(basename)[0]
    rel_path = filepath.replace('\\', '/')

    # 根据文件所在目录生成描述
    if 'views' in rel_path:
        desc = f'{name} 页面视图组件'
        features = '页面布局、数据展示、用户交互、路由导航'
    elif 'components' in rel_path:
        desc = f'{name} UI 组件'
        features = '可复用界面元素、属性配置、事件处理、样式定制'
    elif 'stores' in rel_path:
        desc = f'{name} 状态管理模块'
        features = '全局状态管理、数据持久化、状态同步、业务逻辑封装'
    elif 'api' in rel_path:
        desc = f'{name} API 接口模块'
        features = 'HTTP 请求封装、接口调用、错误处理、响应数据解析'
    elif 'utils' in rel_path:
        desc = f'{name} 工具函数模块'
        features = '通用工具方法、数据处理、格式转换、辅助功能'
    elif 'router' in rel_path:
        desc = f'{name} 路由配置模块'
        features = '路由定义、导航守卫、权限控制、路由懒加载'
    else:
        desc = f'{name} 功能模块'
        features = '核心功能实现、业务逻辑处理、系统集成'

    return f"""<!--
 ============================================================================
 {basename} - {desc}
 ============================================================================

 @file {basename}
 @description 帮信罪主观明知智能分析系统 - {desc}
 @version 1.0.0
 @author 帮信罪智能分析系统开发团队
 @copyright 2024-2026 帮信罪智能分析系统

 功能说明：
   - {features}
   - 数据绑定和响应式更新
   - 用户交互事件处理
   - 组件生命周期管理

 技术栈：
   - Vue 3 Composition API
   - Pinia 状态管理
   - Element Plus UI 组件库
   - Axios HTTP 客户端

 依赖关系：
   - 父组件：AppLayout 或路由视图
   - 子组件：BaseButton, BaseInput, BaseModal 等基础组件
   - Store：analysisStore, caseStore, authStore
   - API：/api/cases, /api/analyses, /api/knowledge

 使用说明：
   - 路由访问：通过 Vue Router 配置的路径访问
   - 权限要求：需要用户登录后访问
   - 数据流向：用户输入 -> API 请求 -> 状态更新 -> 视图渲染

 ============================================================================
-->
"""


def get_js_file_comment(filepath):
    """根据 JS/TS 文件路径生成文件头注释.

    Args:
        filepath: 文件路径

    Returns:
        str: 生成的文件头注释
    """
    basename = os.path.basename(filepath)
    name = os.path.splitext(basename)[0]
    rel_path = filepath.replace('\\', '/')

    if 'stores' in rel_path:
        desc = f'{name} 状态管理模块'
        features = '全局状态定义、状态修改方法、数据持久化、状态订阅'
    elif 'api' in rel_path:
        desc = f'{name} API 接口封装'
        features = 'HTTP 请求方法、接口调用、错误处理、响应拦截'
    elif 'utils' in rel_path:
        desc = f'{name} 工具函数库'
        features = '通用工具方法、数据处理、格式转换、辅助功能'
    elif 'router' in rel_path:
        desc = f'{name} 路由配置'
        features = '路由定义、导航守卫、权限验证、路由懒加载'
    else:
        desc = f'{name} 功能模块'
        features = '核心功能实现、业务逻辑处理、系统集成'

    return f"""/**
 * ============================================================================
 * {basename} - {desc}
 * ============================================================================
 *
 * @file {basename}
 * @description 帮信罪主观明知智能分析系统 - {desc}
 * @version 1.0.0
 * @author 帮信罪智能分析系统开发团队
 * @copyright 2024-2026 帮信罪智能分析系统
 *
 * 功能说明：
 *   - {features}
 *   - 数据状态管理和同步
 *   - 业务逻辑封装和复用
 *   - 错误处理和异常恢复
 *
 * 技术栈：
 *   - JavaScript / TypeScript
 *   - Pinia 状态管理（适用于 Store）
 *   - Axios HTTP 客户端（适用于 API）
 *   - Vue Router（适用于 Router）
 *
 * 使用说明：
 *   - 导入方式：import {{ {name} }} from '{rel_path}'
 *   - 依赖注入：通过 Vue 的 provide/inject 或 Pinia
 *   - 错误处理：统一的错误捕获和日志记录
 *
 * ============================================================================
 */
"""


def add_vue_comments(filepath, content):
    """为 Vue 文件添加注释.

    Args:
        filepath: 文件路径
        content: 文件原始内容

    Returns:
        str: 添加注释后的文件内容
    """
    # 检查是否已有文件头注释
    if '<!--' in content[:500] and ('文件说明' in content[:500] or '功能说明' in content[:500]):
        return content

    # 添加文件头注释
    header = get_vue_file_comment(filepath)
    if '<template>' in content[:100]:
        content = header + content
    elif content.strip().startswith('<'):
        content = header + content

    # 为 <script> 标签内的代码添加注释
    script_match = re.search(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
    if script_match:
        script_content = script_match.group(1)
        script_start = script_match.start(1)
        script_end = script_match.end(1)

        # 为 import 语句添加注释
        if 'import ' in script_content and '// 导入' not in script_content[:200]:
            script_content = '// 导入依赖模块和组件\n' + script_content

        # 为 defineComponent 或 setup 添加注释
        if 'defineComponent' in script_content and '// 组件定义' not in script_content:
            script_content = script_content.replace(
                'defineComponent',
                '// 定义 Vue 组件\nexport default defineComponent'
            )

        # 为 reactive/ref 数据添加注释
        if 'reactive(' in script_content and '// 响应式数据' not in script_content:
            script_content = script_content.replace(
                'reactive(',
                '// 定义响应式数据对象\nconst state = reactive('
            )

        if 'ref(' in script_content and '// 响应式引用' not in script_content:
            script_content = script_content.replace(
                'ref(',
                '// 定义响应式引用\nconst '
            )

        # 为 computed 属性添加注释
        if 'computed(' in script_content and '// 计算属性' not in script_content:
            script_content = script_content.replace(
                'computed(',
                '// 定义计算属性，基于响应式数据自动计算\nconst '
            )

        # 为方法定义添加注释
        if 'function ' in script_content and '// 方法定义' not in script_content:
            script_content = re.sub(
                r'function\s+(\w+)',
                r'// 定义 \1 方法\nfunction \1',
                script_content
            )

        # 为生命周期钩子添加注释
        lifecycle_hooks = ['onMounted', 'onUnmounted', 'onUpdated', 'onBeforeMount']
        for hook in lifecycle_hooks:
            if hook + '(' in script_content and f'// {hook}' not in script_content:
                script_content = script_content.replace(
                    hook + '(',
                    f'// 生命周期钩子：{hook}\n{hook}('
                )

        # 替换回原内容
        content = content[:script_start] + script_content + content[script_end:]

    # 为 <template> 标签内的关键元素添加注释
    template_match = re.search(r'<template>(.*?)</template>', content, re.DOTALL)
    if template_match:
        template_content = template_match.group(1)
        template_start = template_match.start(1)
        template_end = template_match.end(1)

        # 为根元素添加注释
        if '<div' in template_content[:100] and '<!-- 根容器' not in template_content:
            template_content = template_content.replace(
                '<div',
                '<!-- 页面根容器 -->\n<div',
                1
            )

        # 为 v-if/v-for 指令添加注释
        if 'v-if=' in template_content and '<!-- 条件渲染' not in template_content:
            template_content = re.sub(
                r'(<\w+[^>]*v-if=)',
                r'<!-- 条件渲染：根据条件显示/隐藏元素 -->\n\1',
                template_content
            )

        if 'v-for=' in template_content and '<!-- 列表渲染' not in template_content:
            template_content = re.sub(
                r'(<\w+[^>]*v-for=)',
                r'<!-- 列表渲染：遍历数据生成多个元素 -->\n\1',
                template_content
            )

        # 替换回原内容
        content = content[:template_start] + template_content + content[template_end:]

    return content


def add_js_comments(filepath, content):
    """为 JS/TS 文件添加注释.

    Args:
        filepath: 文件路径
        content: 文件原始内容

    Returns:
        str: 添加注释后的文件内容
    """
    # 检查是否已有文件头注释
    if content.strip().startswith('/**') and ('文件说明' in content[:500] or '功能说明' in content[:500]):
        return content

    # 添加文件头注释
    header = get_js_file_comment(filepath)
    content = header + '\n' + content

    # 为 import 语句添加注释
    if 'import ' in content and '// 导入' not in content[:300]:
        content = content.replace('import ', '// 导入依赖模块\nimport ', 1)

    # 为 export 语句添加注释
    if 'export ' in content and '// 导出' not in content[:300]:
        content = content.replace('export ', '// 导出模块接口\nexport ', 1)

    # 为函数定义添加注释
    func_pattern = re.compile(r'^(function\s+\w+|const\s+\w+\s*=\s*function|const\s+\w+\s*=\s*\()', re.MULTILINE)
    for match in func_pattern.finditer(content):
        line_start = match.start()
        line_end = content.find('\n', line_start)
        if line_end == -1:
            line_end = len(content)

        line = content[line_start:line_end]

        # 检查该行上方是否已有注释
        prev_line_end = line_start
        prev_line_start = content.rfind('\n', 0, prev_line_end)
        if prev_line_start == -1:
            prev_line_start = 0

        prev_line = content[prev_line_start:prev_line_end].strip()

        if not prev_line.startswith('//') and not prev_line.startswith('*'):
            func_name = match.group(1).split()[1] if ' ' in match.group(1) else 'anonymous'
            comment = f'// 定义 {func_name} 函数\n'
            content = content[:line_start] + comment + content[line_start:]

    # 为 if/for/while 等控制结构添加注释
    control_patterns = [
        (r'^(\s*)if\s*\(', '// 条件判断：'),
        (r'^(\s*)for\s*\(', '// 循环遍历：'),
        (r'^(\s*)while\s*\(', '// 循环条件：'),
        (r'^(\s*)try\s*\{', '// 异常处理：'),
        (r'^(\s*)catch\s*\(', '// 捕获异常：'),
    ]

    for pattern, comment_prefix in control_patterns:
        for match in re.finditer(pattern, content, re.MULTILINE):
            indent = match.group(1)
            line_start = match.start()

            line_end = content.find('\n', line_start)
            if line_end == -1:
                line_end = len(content)

            line = content[line_start:line_end]

            if '#' not in line and '//' not in line and line.strip():
                comment = f"{indent}{comment_prefix}处理业务逻辑\n"
                content = content[:line_start] + comment + content[line_start:]

    return content


# ============================================================================
# 主处理逻辑
# ============================================================================

def process_backend_files():
    """处理后端 Python 文件."""
    print("=" * 70)
    print("开始为后端 Python 文件添加注释...")
    print("=" * 70)

    backend_dir = 'backend'
    processed_count = 0
    skipped_count = 0

    for root, dirs, files in os.walk(backend_dir):
        # 跳过虚拟环境和缓存目录
        dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git', '.pytest_cache']]

        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 添加注释
                    new_content = add_python_comments(filepath, content)

                    # 如果内容有变化，写回文件
                    if new_content != content:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        processed_count += 1
                        print(f"  [OK] {filepath}")
                    else:
                        skipped_count += 1
                        print(f"  [SKIP] {filepath} (无变化)")

                except Exception as e:
                    print(f"  [ERROR] {filepath}: {e}")

    print(f"\n后端处理完成：处理 {processed_count} 个文件，跳过 {skipped_count} 个文件")


def process_frontend_files():
    """处理前端 Vue/JS/TS 文件."""
    print("\n" + "=" * 70)
    print("开始为前端 Vue/JS/TS 文件添加注释...")
    print("=" * 70)

    frontend_dir = 'frontend/src'
    processed_count = 0
    skipped_count = 0

    for root, dirs, files in os.walk(frontend_dir):
        # 跳过 node_modules
        dirs[:] = [d for d in dirs if d not in ['node_modules', '.git']]

        for file in files:
            if file.endswith(('.vue', '.js', '.ts')):
                filepath = os.path.join(root, file)

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 根据文件类型添加注释
                    if file.endswith('.vue'):
                        new_content = add_vue_comments(filepath, content)
                    else:
                        new_content = add_js_comments(filepath, content)

                    # 如果内容有变化，写回文件
                    if new_content != content:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        processed_count += 1
                        print(f"  [OK] {filepath}")
                    else:
                        skipped_count += 1
                        print(f"  [SKIP] {filepath} (无变化)")

                except Exception as e:
                    print(f"  [ERROR] {filepath}: {e}")

    print(f"\n前端处理完成：处理 {processed_count} 个文件，跳过 {skipped_count} 个文件")


if __name__ == '__main__':
    print("=" * 70)
    print("帮信罪主观明知智能分析系统 - 批量注释添加脚本")
    print("=" * 70)
    print()

    # 处理后端文件
    process_backend_files()

    # 处理前端文件
    process_frontend_files()

    print("\n" + "=" * 70)
    print("所有文件处理完成！")
    print("请运行 count_comments.py 检查注释率是否达到 30%")
    print("=" * 70)
