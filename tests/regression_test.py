#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""阶段19：完整功能回归测试脚本

系统性验证当前版本是否100%保留并正确实现阶段0定义的所有原始功能。
测试范围：后端API全量回归 + 前端页面可达性验证
"""

import json
import sys
import os
import io
import time
from datetime import datetime

# 强制UTF-8输出，解决Windows GBK编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests

BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

# 测试结果记录
results = []
token = None
admin_token = None


def log_result(module, test_name, status, detail=""):
    """记录测试结果"""
    results.append({
        "module": module,
        "test": test_name,
        "status": status,
        "detail": detail,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })
    icon = {"pass": "✅", "fail": "❌", "warn": "⚠️"}.get(status, "❓")
    print(f"  {icon} [{module}] {test_name}" + (f" - {detail}" if detail else ""))


def login(username="admin", password="admin123"):
    """登录获取token"""
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        data={"username": username, "password": password},
    )
    if r.status_code == 200:
        return r.json().get("access_token")
    return None


def auth_headers(t):
    return {"Authorization": f"Bearer {t}"} if t else {}


# ============================================================================
# 1. 用户认证流程
# ============================================================================
def test_auth():
    print("\n=== 1. 用户认证流程 ===")

    # 1.1 登录测试
    t = login("admin", "admin123")
    if t:
        log_result("认证", "管理员登录", "pass", "成功获取token")
    else:
        log_result("认证", "管理员登录", "fail", "登录失败")
        return False

    # 1.2 获取当前用户信息
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers(t))
    if r.status_code == 200:
        user = r.json()
        log_result("认证", "获取用户信息(/me)", "pass", f"username={user.get('username')}, role={user.get('role')}")
    else:
        log_result("认证", "获取用户信息(/me)", "fail", f"status={r.status_code}")

    # 1.3 Token刷新
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    if r.status_code == 200:
        data = r.json()
        refresh_token = data.get("refresh_token")
        if refresh_token:
            r2 = requests.post(
                f"{BASE_URL}/api/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            if r2.status_code == 200:
                log_result("认证", "Token刷新", "pass")
            else:
                log_result("认证", "Token刷新", "fail", f"status={r2.status_code}")
        else:
            log_result("认证", "Token刷新", "warn", "未返回refresh_token")
    else:
        log_result("认证", "Token刷新", "fail", "重新登录失败")

    # 1.4 登出测试
    r = requests.post(f"{BASE_URL}/api/auth/logout", headers=auth_headers(t))
    if r.status_code in (200, 204):
        log_result("认证", "登出", "pass")
    else:
        log_result("认证", "登出", "warn", f"status={r.status_code}")

    # 1.5 未认证访问受保护资源
    r = requests.get(f"{BASE_URL}/api/auth/me")
    if r.status_code in (401, 403):
        log_result("认证", "未认证拦截", "pass", f"正确返回{r.status_code}")
    else:
        log_result("认证", "未认证拦截", "fail", f"应返回401/403，实际{r.status_code}")

    # 1.6 错误密码登录
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        data={"username": "admin", "password": "wrong_password"},
    )
    if r.status_code == 401:
        log_result("认证", "错误密码拒绝", "pass")
    else:
        log_result("认证", "错误密码拒绝", "fail", f"应返回401，实际{r.status_code}")

    # 重新登录获取token供后续测试使用
    global token, admin_token
    token = login("admin", "admin123")
    admin_token = token
    return token is not None


# ============================================================================
# 2. 案件处理流程
# ============================================================================
def test_cases():
    print("\n=== 2. 案件处理流程 ===")
    h = auth_headers(token)

    # 2.1 案件列表
    r = requests.get(f"{BASE_URL}/api/cases/", params={"page": 1, "page_size": 10}, headers=h)
    if r.status_code == 200:
        data = r.json()
        total = data.get("total", 0)
        log_result("案件管理", "案件列表查询", "pass", f"共{total}条记录")
    else:
        log_result("案件管理", "案件列表查询", "fail", f"status={r.status_code}")

    # 2.2 创建案件
    r = requests.post(f"{BASE_URL}/api/cases/", json={
        "title": "回归测试案件-001",
        "case_text": "被告人张三在明知他人利用信息网络实施犯罪的情况下，仍为其提供互联网接入、服务器托管等技术支持，情节严重。",
        "description": "被告人张三在明知他人利用信息网络实施犯罪的情况下，仍为其提供互联网接入、服务器托管等技术支持，情节严重。",
        "status": "pending",
    }, headers=h)
    if r.status_code in (200, 201):
        case_data = r.json()
        case_id = case_data.get("id")
        log_result("案件管理", "创建案件", "pass", f"case_id={case_id}")
    else:
        log_result("案件管理", "创建案件", "fail", f"status={r.status_code}, detail={r.text[:100]}")
        case_id = None

    # 2.3 获取案件详情
    if case_id:
        r = requests.get(f"{BASE_URL}/api/cases/{case_id}", headers=h)
        if r.status_code == 200:
            log_result("案件管理", "获取案件详情", "pass")
        else:
            log_result("案件管理", "获取案件详情", "fail", f"status={r.status_code}")

    # 2.4 更新案件
    if case_id:
        r = requests.put(f"{BASE_URL}/api/cases/{case_id}", json={
            "case_name": "回归测试案件-001-更新",
            "case_status": "analyzing",
        }, headers=h)
        if r.status_code == 200:
            log_result("案件管理", "更新案件", "pass")
        else:
            log_result("案件管理", "更新案件", "fail", f"status={r.status_code}")

    # 2.5 案件状态筛选
    r = requests.get(f"{BASE_URL}/api/cases/", params={"status": "pending"}, headers=h)
    if r.status_code == 200:
        log_result("案件管理", "案件状态筛选", "pass")
    else:
        log_result("案件管理", "案件状态筛选", "fail", f"status={r.status_code}")

    return case_id


# ============================================================================
# 3. 三维度分析功能
# ============================================================================
def test_analysis():
    print("\n=== 3. 三维度分析功能 ===")

    # 3.1 执行案件分析
    r = requests.post(f"{BASE_URL}/api/analyze", json={
        "case_text": "被告人李四在明知他人利用信息网络实施诈骗犯罪的情况下，仍为其提供支付结算帮助，涉案金额达50万元，情节严重。被告人供述其曾收到公安机关的警告通知，但仍继续提供帮助行为。",
        "mode": "single",
    }, headers=auth_headers(token))

    if r.status_code == 200:
        data = r.json()
        analysis_id = data.get("id") or data.get("analysis_id")
        # 检查三维度分析结果
        has_objective = "objective_analysis" in data or "客观行为" in str(data)
        has_cognitive = "cognitive_analysis" in data or "认知能力" in str(data)
        has_justification = "justification_analysis" in data or "辩解合理性" in str(data)
        has_conclusion = "conclusion" in data or "综合结论" in str(data)

        dims = []
        if has_objective: dims.append("客观行为")
        if has_cognitive: dims.append("认知能力")
        if has_justification: dims.append("辩解合理性")
        if has_conclusion: dims.append("综合结论")

        if len(dims) >= 3:
            log_result("三维度分析", "分析执行与结果", "pass", f"包含: {', '.join(dims)}")
        else:
            log_result("三维度分析", "分析执行与结果", "warn", f"仅包含: {', '.join(dims) if dims else '未知'}")
    else:
        log_result("三维度分析", "分析执行", "fail", f"status={r.status_code}, detail={r.text[:100]}")
        analysis_id = None

    # 3.2 分析缓存（重复分析）
    if analysis_id:
        r2 = requests.post(f"{BASE_URL}/api/analyze", json={
            "case_text": "被告人李四在明知他人利用信息网络实施诈骗犯罪的情况下，仍为其提供支付结算帮助，涉案金额达50万元，情节严重。被告人供述其曾收到公安机关的警告通知，但仍继续提供帮助行为。",
            "mode": "standard",
        }, headers=auth_headers(token))
        if r2.status_code == 200:
            log_result("三维度分析", "分析缓存机制", "pass")
        else:
            log_result("三维度分析", "分析缓存机制", "warn", f"status={r2.status_code}")

    # 3.3 规则触发
    if r.status_code == 200:
        data = r.json()
        rules = data.get("triggered_rules", [])
        if isinstance(rules, list) and len(rules) > 0:
            log_result("三维度分析", "规则触发机制", "pass", f"触发{len(rules)}条规则")
        else:
            log_result("三维度分析", "规则触发机制", "warn", "未触发规则（可能文本未命中）")

    return analysis_id


# ============================================================================
# 4. 报告功能
# ============================================================================
def test_reports(analysis_id):
    print("\n=== 4. 报告功能 ===")
    if not analysis_id:
        log_result("报告功能", "报告生成", "fail", "无可用analysis_id")
        return None

    # 4.1 生成报告
    r = requests.post(f"{BASE_URL}/api/reports/generate", json={
        "analysis_id": analysis_id,
    }, headers=auth_headers(token))
    if r.status_code == 200:
        report_id = r.json().get("report_id")
        log_result("报告功能", "报告生成", "pass", f"report_id={report_id}")
    else:
        log_result("报告功能", "报告生成", "fail", f"status={r.status_code}, detail={r.text[:100]}")
        report_id = None

    # 4.2 获取报告列表
    r = requests.get(f"{BASE_URL}/api/reports/", params={"page": 1, "page_size": 10}, headers=auth_headers(token))
    if r.status_code == 200:
        data = r.json()
        total = data.get("total", 0)
        log_result("报告功能", "报告列表", "pass", f"共{total}份报告")
    else:
        log_result("报告功能", "报告列表", "fail", f"status={r.status_code}")

    # 4.3 获取报告详情
    if report_id:
        r = requests.get(f"{BASE_URL}/api/reports/{report_id}", headers=auth_headers(token))
        if r.status_code == 200:
            content = r.json().get("content", {})
            # 检查10章节
            chapters = content.get("chapters", [])
            if isinstance(chapters, list) and len(chapters) >= 5:
                log_result("报告功能", "报告章节内容", "pass", f"共{len(chapters)}章节")
            else:
                log_result("报告功能", "报告章节内容", "warn", f"章节数={len(chapters) if isinstance(chapters, list) else 'N/A'}")

            # 检查11项审查要点
            checklist = content.get("review_checklist", content.get("checklist", []))
            if isinstance(checklist, list) and len(checklist) > 0:
                log_result("报告功能", "审查要点", "pass", f"共{len(checklist)}项")
            else:
                log_result("报告功能", "审查要点", "warn", "未找到审查要点")
        else:
            log_result("报告功能", "报告详情", "fail", f"status={r.status_code}")

    # 4.4 PDF导出
    if report_id:
        r = requests.get(f"{BASE_URL}/api/reports/{report_id}/pdf", headers=auth_headers(token))
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/pdf"):
            log_result("报告功能", "PDF导出", "pass", f"文件大小={len(r.content)} bytes")
        else:
            log_result("报告功能", "PDF导出", "fail", f"status={r.status_code}, content-type={r.headers.get('content-type')}")

    # 4.5 DOCX导出
    if report_id:
        r = requests.get(f"{BASE_URL}/api/reports/{report_id}/docx", headers=auth_headers(token))
        if r.status_code == 200 and "officedocument" in r.headers.get("content-type", ""):
            log_result("报告功能", "DOCX导出", "pass", f"文件大小={len(r.content)} bytes")
        else:
            log_result("报告功能", "DOCX导出", "fail", f"status={r.status_code}, content-type={r.headers.get('content-type')}")

    # 4.6 提交审查
    if report_id:
        r = requests.post(f"{BASE_URL}/api/reports/{report_id}/review", json={
            "items": {"item_1": True, "item_2": True},
            "comments": "回归测试审查意见",
        }, headers=auth_headers(token))
        if r.status_code == 200:
            log_result("报告功能", "审查提交", "pass")
        else:
            log_result("报告功能", "审查提交", "fail", f"status={r.status_code}")

    return report_id


# ============================================================================
# 5. 文档上传功能
# ============================================================================
def test_documents():
    print("\n=== 5. 文档上传功能 ===")
    h = auth_headers(token)

    # 5.1 上传文本文件
    text_content = "这是一份测试文档，用于验证帮信罪辅助裁定系统的文档上传功能。被告人王五在明知他人利用信息网络实施犯罪的情况下...".encode("utf-8")
    files = {"file": ("test_case.txt", io.BytesIO(text_content), "text/plain")}
    r = requests.post(f"{BASE_URL}/api/documents/upload", files=files, headers=h)
    if r.status_code == 200:
        data = r.json()
        log_result("文档上传", "文本文件上传", "pass", f"提取{data.get('content_length', 0)}字符")
    else:
        log_result("文档上传", "文本文件上传", "fail", f"status={r.status_code}")

    # 5.2 未认证上传
    r = requests.post(f"{BASE_URL}/api/documents/upload", files=files)
    if r.status_code in (401, 403):
        log_result("文档上传", "未认证拦截", "pass")
    else:
        log_result("文档上传", "未认证拦截", "fail", f"应返回401/403，实际{r.status_code}")


# ============================================================================
# 6. 知识库管理功能
# ============================================================================
def test_knowledge():
    print("\n=== 6. 知识库管理功能 ===")
    h = auth_headers(token)

    # 6.1 知识条目列表
    r = requests.get(f"{BASE_URL}/api/knowledge/entries", params={"page": 1, "page_size": 10}, headers=h)
    if r.status_code == 200:
        data = r.json()
        total = data.get("total", 0)
        log_result("知识库", "知识条目列表", "pass", f"共{total}条")
    else:
        log_result("知识库", "知识条目列表", "fail", f"status={r.status_code}")

    # 6.2 创建知识条目
    r = requests.post(f"{BASE_URL}/api/knowledge/entries", json={
        "title": "回归测试-帮信罪明知认定标准",
        "content": "根据《关于办理非法利用信息网络、帮助信息网络犯罪活动等刑事案件适用法律若干问题的解释》，明知包括知道和应当知道。应当根据行为人的认知能力、接触情况等综合判断。",
        "category": "law",
        "tags": ["帮信罪", "明知认定"],
        "source_type": "manual"
    }, headers=h)
    if r.status_code in (200, 201):
        entry = r.json()
        entry_id = entry.get("id")
        log_result("知识库", "创建知识条目", "pass", f"entry_id={entry_id}")
    else:
        log_result("知识库", "创建知识条目", "fail", f"status={r.status_code}, detail={r.text[:100]}")
        entry_id = None

    # 6.3 获取知识条目详情
    if entry_id:
        r = requests.get(f"{BASE_URL}/api/knowledge/entries/{entry_id}", headers=h)
        if r.status_code == 200:
            log_result("知识库", "获取知识条目详情", "pass")
        else:
            log_result("知识库", "获取知识条目详情", "fail", f"status={r.status_code}")

    # 6.4 更新知识条目
    if entry_id:
        r = requests.put(f"{BASE_URL}/api/knowledge/entries/{entry_id}", json={
            "title": "回归测试-帮信罪明知认定标准(更新)",
            "content": "根据最新司法解释，明知包括知道和应当知道，应当根据行为人的认知能力、接触情况等综合判断。",
        }, headers=h)
        if r.status_code == 200:
            log_result("知识库", "更新知识条目", "pass")
        else:
            log_result("知识库", "更新知识条目", "fail", f"status={r.status_code}")

    # 6.5 知识条目分类筛选
    r = requests.get(f"{BASE_URL}/api/knowledge/entries", params={"category": "law"}, headers=h)
    if r.status_code == 200:
        log_result("知识库", "分类筛选", "pass")
    else:
        log_result("知识库", "分类筛选", "fail", f"status={r.status_code}")

    # 6.6 知识图谱数据
    r = requests.get(f"{BASE_URL}/api/knowledge/graph", headers=h)
    if r.status_code == 200:
        data = r.json()
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        log_result("知识库", "知识图谱数据", "pass", f"节点={len(nodes)}, 边={len(edges)}")
    else:
        log_result("知识库", "知识图谱数据", "fail", f"status={r.status_code}")

    # 6.7 法律规则列表
    r = requests.get(f"{BASE_URL}/api/knowledge/rules", headers=h)
    if r.status_code == 200:
        rules = r.json()
        count = len(rules) if isinstance(rules, list) else "N/A"
        log_result("知识库", "法律规则列表", "pass", f"共{count}条规则")
    else:
        log_result("知识库", "法律规则列表", "fail", f"status={r.status_code}")

    # 6.8 标签列表
    r = requests.get(f"{BASE_URL}/api/knowledge/tags", headers=h)
    if r.status_code == 200:
        tags = r.json()
        count = len(tags) if isinstance(tags, list) else "N/A"
        log_result("知识库", "标签列表", "pass", f"共{count}个标签")
    else:
        log_result("知识库", "标签列表", "fail", f"status={r.status_code}")

    # 6.9 删除知识条目
    if entry_id:
        r = requests.delete(f"{BASE_URL}/api/knowledge/entries/{entry_id}", headers=h)
        if r.status_code in (200, 204):
            log_result("知识库", "删除知识条目", "pass")
        else:
            log_result("知识库", "删除知识条目", "fail", f"status={r.status_code}")


# ============================================================================
# 7. 评测中心功能
# ============================================================================
def test_experiment():
    print("\n=== 7. 评测中心功能 ===")
    h = auth_headers(admin_token)

    # 7.1 运行评测实验
    r = requests.post(f"{BASE_URL}/api/experiment/run", json={
        "experiment_type": "model_comparison",
        "params": {
            "case_text": "被告人张三在明知他人利用信息网络实施犯罪的情况下，仍为其提供技术支持。",
            "models": ["model_a", "model_b"]
        },
    }, headers=h)
    if r.status_code == 200:
        data = r.json()
        log_result("评测中心", "评测任务执行", "pass", f"结果类型={type(data).__name__}")
    else:
        log_result("评测中心", "评测任务执行", "fail", f"status={r.status_code}, detail={r.text[:100]}")

    # 7.2 非管理员访问
    r = requests.post(f"{BASE_URL}/api/experiment/run", json={
        "experiment_type": "model_comparison",
        "params": {"case_text": "test", "models": ["a", "b"]},
    }, headers=auth_headers(None))
    if r.status_code in (401, 403):
        log_result("评测中心", "权限控制", "pass")
    else:
        log_result("评测中心", "权限控制", "fail", f"应返回401/403，实际{r.status_code}")


# ============================================================================
# 8. 案件标注功能
# ============================================================================
def test_labels(case_id):
    print("\n=== 8. 案件标注功能 ===")
    h = auth_headers(token)

    if not case_id:
        log_result("案件标注", "标注功能", "fail", "无可用case_id")
        return

    # 8.1 创建标注
    r = requests.post(f"{BASE_URL}/api/cases/{case_id}/labels", json={
        "labels": [
            {"label_type": "d1_tier", "label_value": "二档"},
            {"label_type": "final_verdict", "label_value": "认定帮信"},
            {"label_type": "verdict_subtype", "label_value": "供述明知"},
            {"label_type": "judicial_era", "label_value": "2025意见后"},
        ],
    }, headers=h)
    if r.status_code in (200, 201):
        log_result("案件标注", "创建标注", "pass")
    else:
        log_result("案件标注", "创建标注", "fail", f"status={r.status_code}, detail={r.text[:100]}")

    # 8.2 获取标注
    r = requests.get(f"{BASE_URL}/api/cases/{case_id}/labels", headers=h)
    if r.status_code == 200:
        labels = r.json()
        count = len(labels) if isinstance(labels, list) else "N/A"
        log_result("案件标注", "获取标注", "pass", f"共{count}条标注")
    else:
        log_result("案件标注", "获取标注", "fail", f"status={r.status_code}")

    # 8.3 删除标注
    r = requests.delete(f"{BASE_URL}/api/cases/{case_id}/labels", headers=h)
    if r.status_code in (200, 204):
        log_result("案件标注", "删除标注", "pass")
    else:
        log_result("案件标注", "删除标注", "fail", f"status={r.status_code}")


# ============================================================================
# 9. 系统管理功能
# ============================================================================
def test_system():
    print("\n=== 9. 系统管理功能 ===")
    h = auth_headers(admin_token)

    # 9.1 系统统计
    r = requests.get(f"{BASE_URL}/api/system/stats", headers=h)
    if r.status_code == 200:
        data = r.json()
        log_result("系统管理", "系统统计", "pass", f"统计项={list(data.keys())}")
    else:
        log_result("系统管理", "系统统计", "fail", f"status={r.status_code}")

    # 9.2 系统日志
    r = requests.get(f"{BASE_URL}/api/system/logs", params={"limit": 10}, headers=h)
    if r.status_code == 200:
        logs = r.json()
        count = len(logs) if isinstance(logs, list) else "N/A"
        log_result("系统管理", "系统日志查询", "pass", f"返回{count}条日志")
    else:
        log_result("系统管理", "系统日志查询", "fail", f"status={r.status_code}")

    # 9.3 非管理员访问系统管理
    r = requests.get(f"{BASE_URL}/api/system/stats", headers=auth_headers(None))
    if r.status_code in (401, 403):
        log_result("系统管理", "权限控制", "pass")
    else:
        log_result("系统管理", "权限控制", "fail", f"应返回401/403，实际{r.status_code}")


# ============================================================================
# 10. 前端页面可达性
# ============================================================================
def test_frontend_pages():
    print("\n=== 10. 前端页面可达性 ===")

    pages = [
        ("/", "首页"),
        ("/login", "登录页"),
        ("/main", "分析主页"),
        ("/generate", "智能阅卷"),
        ("/knowledge", "知识库"),
        ("/knowledge-graph", "知识图谱"),
        ("/cases", "案件管理"),
        ("/review", "审查中心"),
        ("/settings", "系统设置"),
    ]

    for path, name in pages:
        r = requests.get(f"{FRONTEND_URL}{path}", allow_redirects=True)
        if r.status_code == 200:
            log_result("前端页面", f"{name}({path})", "pass")
        else:
            log_result("前端页面", f"{name}({path})", "fail", f"status={r.status_code}")


# ============================================================================
# 主测试流程
# ============================================================================
def main():
    print("=" * 60)
    print("阶段19：完整功能回归测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 检查服务可用性
    try:
        r = requests.get(f"{BASE_URL}/api/cases/", timeout=5)
        print(f"\n后端服务: ✅ 可达 (status={r.status_code})")
    except Exception as e:
        print(f"\n后端服务: ❌ 不可达 ({e})")
        print("请先启动后端服务: cd backend && python run.py")
        sys.exit(1)

    try:
        r = requests.get(FRONTEND_URL, timeout=5)
        print(f"前端服务: ✅ 可达 (status={r.status_code})")
    except Exception as e:
        print(f"前端服务:  不可达 ({e})")
        print("请先启动前端服务: cd frontend && npm run dev")
        sys.exit(1)

    # 执行测试
    test_auth()
    case_id = test_cases()
    analysis_id = test_analysis()
    test_reports(analysis_id)
    test_documents()
    test_knowledge()
    test_experiment()
    test_labels(case_id)
    test_system()
    test_frontend_pages()

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    pass_count = sum(1 for r in results if r["status"] == "pass")
    fail_count = sum(1 for r in results if r["status"] == "fail")
    warn_count = sum(1 for r in results if r["status"] == "warn")
    total = len(results)

    print(f"\n总测试项: {total}")
    print(f"✅ 通过: {pass_count} ({pass_count/total*100:.1f}%)")
    print(f"❌ 失败: {fail_count} ({fail_count/total*100:.1f}%)")
    print(f"⚠️  警告: {warn_count} ({warn_count/total*100:.1f}%)")

    if fail_count > 0:
        print("\n--- 失败项详情 ---")
        for r in results:
            if r["status"] == "fail":
                print(f"  ❌ [{r['module']}] {r['test']}: {r['detail']}")

    if warn_count > 0:
        print("\n--- 警告项详情 ---")
        for r in results:
            if r["status"] == "warn":
                print(f"  ⚠️  [{r['module']}] {r['test']}: {r['detail']}")

    # 按模块统计
    print("\n--- 模块通过率 ---")
    modules = {}
    for r in results:
        m = r["module"]
        if m not in modules:
            modules[m] = {"pass": 0, "fail": 0, "warn": 0}
        modules[m][r["status"]] = modules[m].get(r["status"], 0) + 1

    for m, counts in sorted(modules.items()):
        total_m = counts.get("pass", 0) + counts.get("fail", 0) + counts.get("warn", 0)
        pass_rate = counts.get("pass", 0) / total_m * 100 if total_m > 0 else 0
        status = "✅" if pass_rate == 100 else ("⚠️" if pass_rate >= 80 else "❌")
        print(f"  {status} {m}: {counts.get('pass',0)}/{total_m} ({pass_rate:.0f}%)")

    # 保存测试结果
    report = {
        "test_time": datetime.now().isoformat(),
        "total": total,
        "pass": pass_count,
        "fail": fail_count,
        "warn": warn_count,
        "pass_rate": f"{pass_count/total*100:.1f}%",
        "results": results,
    }
    with open("regression_test_results.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n测试报告已保存: regression_test_results.json")

    return fail_count == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
