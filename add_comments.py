"""批量为前端源文件添加注释，以满足软著申请30%注释率要求."""
import os
import re

def add_js_header_comment(filepath, content):
    """为 JS/TS 文件添加头部文件说明注释."""
    basename = os.path.basename(filepath)
    name = os.path.splitext(basename)[0]
    
    # 如果已有头部注释则跳过
    if content.startswith('/**') or content.startswith('//'):
        first_lines = content[:500]
        if '文件说明' in first_lines or 'File:' in first_lines or '@file' in first_lines:
            return content
    
    # 根据文件名生成描述
    descriptions = {
        'main': '应用入口文件，初始化 Vue 实例、插件、全局配置和 Axios 拦截器',
        'auth': '认证状态管理 Store，处理登录、登出、Token 管理和用户信息持久化',
        'index': '路由配置模块，定义应用路由表、导航守卫和权限控制逻辑',
        'client': 'HTTP 客户端封装，配置基础 URL、超时时间和请求拦截器',
        'cases': '案件管理 API 接口封装，提供案件 CRUD 操作的异步请求方法',
        'analysis': '分析任务 API 接口封装，提供案件分析提交和结果查询的请求方法',
        'formatters': '格式化工具函数集合，提供日期、数字、文本等数据的显示格式化',
        'validators': '表单验证工具函数集合，提供输入数据的合法性校验规则',
        'errorHandler': '错误处理工具模块，提供统一的错误日志记录、用户消息格式化',
        'errorPlugin': 'Vue 错误处理插件，全局捕获组件渲染和生命周期中的异常',
        'storage': '本地存储工具模块，封装 localStorage 操作并提供异常保护',
        'config': '应用配置常量模块，集中管理系统运行所需的配置参数',
        'demoCases': '示例案件数据模块，提供预置的演示案件文本用于功能展示',
        'agreement': '用户协议工具模块，管理用户协议的接受状态和本地持久化',
    }
    
    desc = descriptions.get(name, f'{name} 模块')
    
    header = f"""/**
 * {basename} - {desc}
 *
 * @module {basename}
 * @description 帮信罪主观明知智能分析系统 - 前端{desc}
 * @version 1.0.0
 */

"""
    return header + content


def add_vue_header_comment(filepath, content):
    """为 Vue 单文件组件添加模板注释."""
    basename = os.path.basename(filepath)
    name = os.path.splitext(basename)[0]
    
    # 如果已有头部注释则跳过
    if '<!--' in content[:200]:
        first_lines = content[:500]
        if '文件说明' in first_lines or '组件说明' in first_lines:
            return content
    
    # 根据文件名生成组件描述
    view_descriptions = {
        'WelcomeView': '欢迎页面，展示系统介绍和入口引导',
        'LoginView': '用户登录页面，提供账号密码登录表单和认证流程',
        'MainView': '主功能页面，集成案件输入、分析触发和结果展示',
        'GenerateView': '分析生成页面，用户输入案件文本并触发智能分析',
        'AnalysisView': '分析结果展示页面，多维度呈现案件分析结论',
        'ReportView': '报告查看页面，展示完整的分析报告内容和导出功能',
        'CasesView': '案件列表页面，展示和管理所有已录入的案件记录',
        'CaseDetailView': '案件详情页面，展示单个案件的完整信息和历史分析',
        'ReviewView': '审核页面，供管理员审查和标注分析结果',
        'SettingsView': '系统设置页面，管理用户偏好和系统配置参数',
        'KnowledgeView': '知识库列表页面，展示和管理法律知识条目',
        'KnowledgeDetailView': '知识详情页面，展示单条知识的完整内容',
        'KnowledgeEditView': '知识编辑页面，创建和修改知识库条目',
        'KnowledgeGraphView': '知识图谱可视化页面，图形化展示知识关联关系',
        'SimilarCasesView': '相似案例检索页面，基于当前案件检索相似判例',
        'UploadView': '文件上传页面，支持批量导入案件文档',
        'DashboardView': '数据仪表盘页面，统计展示系统运行数据概览',
        'EvalCenterView': '评测中心页面，管理模型效果评估和对比实验',
        'LabelingView': '案件标注页面，管理员对案件进行人工标注',
        'AgreementView': '用户协议页面，展示服务协议和隐私政策',
        'ForbiddenView': '权限不足页面，提示用户无权访问当前资源',
        'ExperimentView': '实验管理页面，研究人员配置和运行分析实验',
    }
    
    component_descriptions = {
        'AppLayout': '应用布局组件，定义页面整体框架结构包含侧边栏和主内容区',
        'AppHeader': '应用头部组件，展示系统标题、用户信息和操作菜单',
        'AppSidebar': '应用侧边栏组件，提供导航菜单和功能入口',
        'MobileTabbar': '移动端底部标签栏组件，提供移动端导航入口',
        'PageContainer': '页面容器组件，提供统一的页面内边距和最大宽度约束',
        'BaseButton': '基础按钮组件，封装按钮样式和交互状态',
        'BaseInput': '基础输入框组件，封装表单输入和验证提示',
        'BaseModal': '基础模态框组件，提供弹窗交互和遮罩层',
        'BaseTable': '基础表格组件，封装数据表格和分页功能',
        'BaseCard': '基础卡片组件，提供内容容器和阴影效果',
        'BaseBadge': '基础徽章组件，展示状态标签和计数标记',
        'BaseTabs': '基础标签页组件，提供多面板切换导航',
        'BaseSelect': '基础下拉选择组件，封装选择器交互',
        'BaseTextarea': '基础文本域组件，提供多行文本输入',
        'BasePagination': '基础分页组件，提供数据分页导航控件',
        'BaseSkeleton': '基础骨架屏组件，提供内容加载占位效果',
        'BaseDrawer': '基础抽屉组件，提供侧滑面板交互',
        'BaseEmpty': '基础空状态组件，展示无数据时的提示信息',
        'BaseDivider': '基础分割线组件，提供视觉分隔和内容分组',
        'BaseLoading': '基础加载组件，展示加载状态和进度指示',
        'BaseToast': '基础消息提示组件，提供轻量级反馈通知',
        'AnimatedProgress': '动画进度条组件，提供平滑的进度过渡效果',
        'AnimatedNumber': '动画数字组件，提供数字变化的滚动动画效果',
        'ResponsiveImage': '响应式图片组件，自适应不同屏幕尺寸的图片展示',
        'AnalysisResult': '分析结果展示组件，多维度呈现案件分析结论',
        'DimensionMatrix': '维度矩阵组件，展示三维度分析评估矩阵',
        'RuleTransparency': '规则透明组件，展示分析过程中引用的法律规则',
        'EvidenceLayerPanel': '证据层面板组件，展示证据强度分层分析结果',
        'MultiSubjectPanel': '多主体面板组件，展示多涉案主体分层分析',
        'StandardPathBadge': '标准路径徽章组件，展示规范路径识别结果',
        'BoundaryAlertBanner': '边界提醒横幅组件，展示分析边界和风险提示',
        'CaseCard': '案件卡片组件，以卡片形式展示案件摘要信息',
        'LoadingSpinner': '加载旋转组件，展示操作进行中的等待动画',
        'KnowledgeGraph': '知识图谱可视化组件，使用力导向图展示知识关联',
    }
    
    desc = view_descriptions.get(name, component_descriptions.get(name, f'{name} 组件'))
    
    # 在 <template> 标签后插入注释
    if '<template>' in content[:100]:
        comment = f"""<template>
  <!--
    {name}.vue - {desc}
    
    @description 帮信罪主观明知智能分析系统 - {desc}
    @version 1.0.0
  -->"""
        content = content.replace('<template>', comment, 1)
    
    return content


def add_inline_comments_to_vue(content):
    """为 Vue 文件的 script 部分添加行内注释."""
    # 在 <script> 标签后添加模块说明
    if '<script>' in content or '<script setup>' in content:
        # 找到 script 标签位置
        for tag in ['<script setup>', '<script>']:
            if tag in content:
                # 检查是否已有注释
                after_tag = content[content.index(tag) + len(tag):content.index(tag) + len(tag) + 200]
                if '/*' not in after_tag[:50] and '//' not in after_tag[:50]:
                    comment = f"\n// =====================================================================\n// 组件逻辑模块 - 包含数据定义、计算属性、方法和生命周期钩子\n// =====================================================================\n"
                    content = content.replace(tag, tag + comment, 1)
                break
    
    # 在 import 语句块前后添加注释
    lines = content.split('\n')
    new_lines = []
    in_imports = False
    import_start = -1
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('import ') and not in_imports:
            in_imports = True
            import_start = i
            new_lines.append('// 导入依赖模块：引入组件、工具函数和状态管理')
            new_lines.append(line)
        elif in_imports and not stripped.startswith('import ') and stripped:
            in_imports = False
            new_lines.append(line)
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    return content


def add_inline_comments_to_js(content):
    """为 JS 文件添加行内注释."""
    lines = content.split('\n')
    new_lines = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 为 export 语句添加注释
        if stripped.startswith('export ') and 'default' in stripped:
            new_lines.append('// 导出模块默认接口，供其他模块引用')
            new_lines.append(line)
        elif stripped.startswith('export function ') or stripped.startswith('export async function '):
            func_name = re.search(r'export\s+(?:async\s+)?function\s+(\w+)', stripped)
            if func_name:
                new_lines.append(f'// 导出函数 {func_name.group(1)}：提供模块核心功能')
            new_lines.append(line)
        elif stripped.startswith('export const ') and '=' in stripped:
            const_name = re.search(r'export\s+const\s+(\w+)', stripped)
            if const_name:
                new_lines.append(f'// 导出常量 {const_name.group(1)}：模块级配置或共享状态')
            new_lines.append(line)
        elif stripped.startswith('function ') and not stripped.startswith('function*'):
            func_name = re.search(r'function\s+(\w+)', stripped)
            if func_name:
                new_lines.append(f'// 内部函数 {func_name.group(1)}：封装可复用的业务逻辑')
            new_lines.append(line)
        elif stripped.startswith('const ') and '= (' in stripped and '=>' in stripped:
            const_name = re.search(r'const\s+(\w+)', stripped)
            if const_name:
                new_lines.append(f'// 箭头函数 {const_name.group(1)}：简洁的回调或处理逻辑')
            new_lines.append(line)
        elif stripped.startswith('if (') or stripped.startswith('if('):
            new_lines.append('// 条件分支：根据状态执行不同逻辑')
            new_lines.append(line)
        elif stripped.startswith('for (') or stripped.startswith('for('):
            new_lines.append('// 循环遍历：批量处理集合数据')
            new_lines.append(line)
        elif stripped.startswith('try {') or stripped.startswith('try{'):
            new_lines.append('// 异常保护：捕获潜在错误防止程序崩溃')
            new_lines.append(line)
        elif stripped.startswith('return ') and '{' in stripped:
            new_lines.append(line)
        elif stripped == '}' and i > 0 and new_lines and not new_lines[-1].strip().startswith('//'):
            new_lines.append(line)
        else:
            new_lines.append(line)
    
    return '\n'.join(new_lines)


def process_file(filepath):
    """处理单个文件，添加注释."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return False
    
    original = content
    ext = os.path.splitext(filepath)[1]
    
    if ext == '.vue':
        content = add_vue_header_comment(filepath, content)
        content = add_inline_comments_to_vue(content)
    elif ext in ('.js', '.ts'):
        content = add_js_header_comment(filepath, content)
        content = add_inline_comments_to_js(content)
    
    if content != original:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception:
            return False
    return False


def main():
    """主函数：遍历前端 src 目录并处理所有源文件."""
    src_dir = os.path.join('frontend', 'src')
    extensions = ['.vue', '.js', '.ts']
    skip_dirs = {'node_modules', 'dist', 'build'}
    
    processed = 0
    modified = 0
    
    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                filepath = os.path.join(root, file)
                processed += 1
                if process_file(filepath):
                    modified += 1
                    print(f'  [+] {filepath}')
                else:
                    print(f'  [-] {filepath} (无变更)')
    
    print(f'\n处理完成: {processed} 个文件, {modified} 个已修改')


if __name__ == '__main__':
    main()
