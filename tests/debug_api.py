#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""调试脚本：获取API详细错误信息"""

import sys
import io
import requests

# 强制UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_URL = "http://localhost:8000"

def test_endpoint(method, url, json=None, headers=None):
    """测试单个端点并打印详细信息"""
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=5)
        elif method == "POST":
            r = requests.post(url, json=json, headers=headers, timeout=5)
        
        print(f"\n{'='*60}")
        print(f"URL: {url}")
        print(f"Method: {method}")
        print(f"Status: {r.status_code}")
        print(f"Headers: {dict(r.headers)}")
        print(f"Response: {r.text[:500]}")
        print(f"{'='*60}\n")
        
        return r.status_code, r.json() if r.status_code != 500 else None
    except Exception as e:
        print(f"Error: {e}")
        return None, None

# 1. 测试案件列表（无认证）
print("\n### 测试1: 案件列表（无认证）")
test_endpoint("GET", f"{BASE_URL}/api/cases/")

# 2. 登录获取token
print("\n### 测试2: 登录")
r = requests.post(
    f"{BASE_URL}/api/auth/login",
    data={"username": "admin", "password": "admin123"},
)
if r.status_code == 200:
    token = r.json().get("access_token")
    print(f"Login OK, token: {token[:20]}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. 测试案件列表（带认证）
    print("\n### 测试3: 案件列表（带认证）")
    test_endpoint("GET", f"{BASE_URL}/api/cases/", headers=headers)
    
    # 4. 测试系统统计
    print("\n### 测试4: 系统统计")
    test_endpoint("GET", f"{BASE_URL}/api/system/stats", headers=headers)
    
    # 5. 测试知识库标签列表
    print("\n### 测试5: 知识库标签列表")
    test_endpoint("GET", f"{BASE_URL}/api/knowledge/tags", headers=headers)
    
    # 6. 测试创建知识条目
    print("\n### 测试6: 创建知识条目")
    test_endpoint("POST", f"{BASE_URL}/api/knowledge/entries", json={
        "title": "测试知识条目",
        "content": "测试内容",
        "category": "law",
        "tags": ["测试"],
        "source_type": "manual"
    }, headers=headers)
    
else:
    print(f"Login failed: {r.status_code} - {r.text}")
