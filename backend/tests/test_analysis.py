"""分析模块测试.

测试案件分析 API 端点的功能。
使用 conftest.py 中统一的 client fixture 和 mock_ollama_response fixture。

阶段 4 重构后，API 走 V2 协议（"三维度×四档"），所以断言从 V1 的
``ground_truth_analysis`` 改为 V2 的 ``dimension1``/``final_verdict`` 等字段。
"""


# 注意：不再定义模块级别的 client fixture，使用 conftest.py 中的统一 fixture
# 这确保所有测试使用相同的数据库注入和依赖覆盖配置


def test_health_check(client):
    """测试健康检查端点."""
    # 初始化变量 response
    response = client.get("/health")
    assert response.status_code == 200
    # 初始化变量 data
    data = response.json()
    assert "status" in data
    assert "ollama" in data


def test_analyze_case(client, mock_ollama_response):  # noqa: ARG001
    """测试案件分析端点（single 模式）.

    V2 协议下，响应必须包含三维度档级与最终档级（final_verdict）字段。
    """
    # 初始化变量 response
    response = client.post(
        "/api/analyze",
        # 初始化变量 json
        json={
            "case_text": "嫌疑人张某在案发当晚出现在案发现场附近，被监控摄像头拍到。",
            "mode": "single",
        },
    )
    assert response.status_code == 200
    # 初始化变量 data
    data = response.json()
    # 调试：打印完整响应，确认字段结构
    print("RESPONSE_KEYS:", sorted(data.keys()))
    print("FULL_DATA:", data)
    # V2 协议核心字段
    assert "dimension1" in data
    assert "dimension2" in data
    assert "dimension3" in data
    assert "final_verdict" in data
    assert "confidence" in data


def test_analyze_case_with_mode(client, mock_ollama_response):  # noqa: ARG001
    """测试案件分析端点（auto 模式）.

    V2 协议下，auto 模式应同样返回 V2 字段。
    """
    # 初始化变量 response
    response = client.post(
        "/api/analyze",
        # 初始化变量 json
        json={
            "case_text": "这是关于一起简单的案件描述，用来测试系统功能。",
            "mode": "auto",
        },
    )
    assert response.status_code == 200
    # 初始化变量 data
    data = response.json()
    assert "version" in data
    # version 字段会标记 V2 协议
    assert data.get("version") == "v2" or "dimension1" in data
