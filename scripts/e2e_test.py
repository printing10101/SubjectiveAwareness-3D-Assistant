"""
端到端集成测试
验证后端通过推理服务进行完整的案件分析流程
"""

import json
import sys
import time
import urllib.request
import urllib.error


BACKEND_URL = "http://localhost:8000"
INFERENCE_URL = "http://localhost:8001"


def test_health(url: str, name: str) -> bool:
    print(f"\n=== 健康检查: {name} ===")
    try:
        resp = urllib.request.urlopen(f"{url}/health", timeout=10)
        data = json.loads(resp.read())
        status = data.get("status", "unknown")
        print(f"  Status: {status}")
        for k, v in data.items():
            print(f"  {k}: {v}")
        return status == "ok"
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def test_analysis(case_text: str, description: str, expected_min_score: float = None):
    print(f"\n=== 案件分析测试: {description} ===")
    payload = json.dumps(
        {"case_text": case_text, "mode": "auto"}, ensure_ascii=False
    ).encode("utf-8")

    req = urllib.request.Request(
        f"{BACKEND_URL}/api/analyze",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=120)
        result = json.loads(resp.read())
        elapsed = time.time() - start

        print(f"  Response time: {elapsed:.2f}s")
        print(f"  knowledge_score: {result.get('knowledge_score', 'N/A')}")

        ba_score = result.get("behavior_assessment", {}).get("score", "N/A")
        print(f"  behavior_assessment.score: {ba_score}")

        ca_score = result.get("cognitive_assessment", {}).get("score", "N/A")
        print(f"  cognitive_assessment.score: {ca_score}")

        da_score = result.get("defense_assessment", {}).get("score", "N/A")
        print(f"  defense_assessment.score: {da_score}")

        validate_fields(result)
        print("  PASSED")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def validate_fields(result: dict):
    required = [
        "behavior_assessment",
        "cognitive_assessment",
        "defense_assessment",
        "overall_summary",
        "evidence_refs",
        "knowledge_score",
    ]
    for field in required:
        if field not in result:
            raise ValueError(f"Missing field: {field}")

    ba = result.get("behavior_assessment", {})
    for sub in ["score", "reasoning", "key_indicators"]:
        if sub not in ba:
            raise ValueError(f"Missing behavior_assessment.{sub}")

    ca = result.get("cognitive_assessment", {})
    for sub in ["score", "reasoning", "pattern_match"]:
        if sub not in ca:
            raise ValueError(f"Missing cognitive_assessment.{sub}")

    da = result.get("defense_assessment", {})
    for sub in ["score", "reasoning", "contradictions"]:
        if sub not in da:
            raise ValueError(f"Missing defense_assessment.{sub}")


def main():
    print("=" * 60)
    print("端到端集成测试")
    print("=" * 60)

    tests_passed = 0
    tests_total = 0

    if test_health(INFERENCE_URL, "推理服务"):
        tests_passed += 1
    tests_total += 1

    if test_health(BACKEND_URL, "后端服务"):
        tests_passed += 1
    tests_total += 1

    test_cases = [
        (
            "嫌疑人张某在2023年2月，将自己的银行卡以2000元的价格出售给他人。"
            "该银行卡后被用于电信诈骗资金转移，涉案金额达50万元。"
            "张某明知他人可能利用银行卡从事违法犯罪活动，仍然出售银行卡获利。",
            "短期文本 - 出售银行卡案",
        ),
        (
            "嫌疑人李某在2023年1月至6月期间，通过某二手交易平台，"
            "以每台500元的价格收购了200台全新iPhone 15 Pro手机"
            "（官方售价8999元），并通过自己的微信账号转卖给下线张某。"
            "聊天记录显示李某使用暗语交流，要求现金交易。",
            "明显明知 - 异常交易案",
        ),
        (
            "赵某经营一家小型电子产品零售店。"
            "2023年5月，赵某通过正规的B2B平台采购了一批耳机和充电器，"
            "供应商为平台认证商家，开具了正规增值税发票。"
            "该批商品后被查出为假冒注册商标产品。",
            "确实不明知 - 正规采购案",
        ),
    ]

    for case_text, desc in test_cases:
        if test_analysis(case_text, desc):
            tests_passed += 1
        tests_total += 1

    print(f"\n{'=' * 60}")
    print(f"测试结果: {tests_passed}/{tests_total} 通过")
    print(f"{'=' * 60}")

    if tests_passed == tests_total:
        print("\n所有测试通过!")
        return 0
    else:
        print(f"\n{tests_total - tests_passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
