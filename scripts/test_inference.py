"""
推理服务测试脚本
测试部署在 http://localhost:8001 的独立推理服务
包含3组不同类型的案件事实测试用例，验证响应格式正确性
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


INFERENCE_URL = "http://localhost:8001"
TIMEOUT = 60


TEST_CASES = [
    {
        "name": "test_case_01_obvious_knowledge",
        "description": "明显明知 - 异常低价、现金交易、使用暗语",
        "case_text": (
            "嫌疑人李某在2023年1月至6月期间，通过某二手交易平台，"
            "以每台500元的价格收购了200台全新iPhone 15 Pro手机"
            "（官方售价8999元），并通过自己的微信账号转卖给下线张某。\n\n"
            '聊天记录显示：\n- 李某："这批货你懂的，价格摆在这里，别问来源"\n'
            '张某："还是老规矩？现金交易？"\n- 李某："对，别留记录，老地方见"\n'
            '- 李某在微信中多次使用"水货"、"渠道货"等暗语\n\n'
            "交易特征：\n- 收购价格仅为官方价格的5.5%\n"
            "- 交易数量远超个人正常使用需求\n"
            "- 要求现金交易，刻意避免留下转账记录\n"
            "- 使用暗语交流，回避直接谈论货品来源"
        ),
    },
    {
        "name": "test_case_02_edge_knowledge",
        "description": "边缘情况 - 代购以低于市场价进货，有基础查验行为",
        "case_text": (
            "王某是一名兼职代购，通过朋友圈销售各类电子产品和化妆品。"
            '2023年3月，王某通过朋友介绍认识了一位"供货商"，'
            "开始以低于市场价约30%的价格进货并转卖。\n\n"
            "交易情况：\n"
            "- 王某通过微信向供货商下单，供货商直接发货到王某提供的地址\n"
            "- 王某在朋友圈正常宣传销售，价格比官方售价低约25%\n"
            '- 王某曾问过供货商"这些货是正品吧？"，供货商回复"当然是正品，放心卖"\n'
            "- 王某查看了部分商品，有完整包装和防伪标签\n\n"
            "后续调查：\n"
            "- 该批货物实际为走私品，涉及金额约50万元\n"
            "- 王某共销售了约30件商品，获利约2万元\n"
            "- 王某没有海关报关单、进口许可证等文件\n"
            "- 王某在得知货物为走私品后，立即停止了合作"
        ),
    },
    {
        "name": "test_case_03_no_knowledge",
        "description": "确实不明知 - 通过正规平台采购，有正规发票和验收流程",
        "case_text": (
            "赵某经营一家小型电子产品零售店。2023年5月，"
            '赵某通过正规的B2B平台"某东企业购"采购了一批耳机和充电器，'
            "供应商为平台认证商家。\n\n"
            "采购过程：\n"
            "- 赵某在某东企业购平台上下单，使用对公账户付款\n"
            "- 供应商开具了正规增值税发票\n"
            "- 商品通过平台物流配送到赵某店铺\n"
            "- 赵某验货后签收，商品外包装完整，有合格证和保修卡\n\n"
            "商品信息：\n"
            "- 耳机采购价150元/个（市场零售价约200元）\n"
            "- 充电器采购价30元/个（市场零售价约50元）\n"
            "- 价格浮动在正常批发折扣范围内\n\n"
            "后续情况：\n"
            "- 该批商品后被查出为假冒注册商标产品\n"
            "- 赵某在消费者投诉后才得知商品存在问题\n"
            "- 赵某立即下架了相关商品，并配合调查"
        ),
    },
    {
        "name": "test_case_04_short_text",
        "description": "短文本 - 简单明确的案件描述",
        "case_text": (
            "嫌疑人张某在2023年2月，将自己的银行卡以2000元的价格"
            "出售给他人。该银行卡后被用于电信诈骗资金转移，"
            "涉案金额达50万元。张某明知他人可能利用银行卡"
            "从事违法犯罪活动，仍然出售银行卡获利。"
        ),
    },
]


REQUIRED_FIELDS = [
    "behavior_assessment",
    "cognitive_assessment",
    "defense_assessment",
    "overall_summary",
    "evidence_refs",
    "knowledge_score",
]

NESTED_FIELDS = {
    "behavior_assessment": ["score", "reasoning", "key_indicators"],
    "cognitive_assessment": ["score", "reasoning", "pattern_match"],
    "defense_assessment": ["score", "reasoning", "contradictions"],
}


def check_service_health() -> bool:
    """检查推理服务健康状态"""
    url = f"{INFERENCE_URL}/health"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            status = data.get("status")
            print(f"  服务状态: {status}")
            print(f"  模型: {data.get('model', 'unknown')}")
            print(f"  运行时间: {data.get('uptime_seconds', 0)}秒")
            return status == "ok"
    except Exception as e:
        print(f"  ✗ 健康检查失败: {e}")
        return False


def call_inference(case_text: str) -> dict:
    """调用推理服务的 /api/chat 端点"""
    from app.services.prompts import ANALYSIS_SYSTEM_PROMPT

    payload = {
        "model": "qwen2.5:7b",
        "messages": [
            {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": f"请分析以下案件事实：\n\n{case_text}"},
        ],
        "stream": False,
        "options": {
            "temperature": 0.3,
            "top_p": 0.9,
        },
    }

    url = f"{INFERENCE_URL}/api/chat"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start_time = time.time()
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        response_data = json.loads(resp.read().decode())

    elapsed = time.time() - start_time
    message = response_data.get("message", {}).get("content", "")

    return _extract_json(message), elapsed


def _extract_json(text: str) -> dict:
    """从LLM响应中提取JSON"""
    import re

    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    code_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if code_match:
        text = code_match.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in response")
    json_str = text[start : end + 1]
    return json.loads(json_str)


def validate_response(result: dict) -> list[str]:
    """验证响应结果的字段完整性和格式正确性"""
    errors = []

    for field in REQUIRED_FIELDS:
        if field not in result:
            errors.append(f"缺失顶级字段: {field}")
            continue

    for field, sub_fields in NESTED_FIELDS.items():
        if field not in result:
            continue
        obj = result[field]
        if not isinstance(obj, dict):
            errors.append(f"字段 '{field}' 应为对象类型")
            continue
        for sub in sub_fields:
            if sub not in obj:
                errors.append(f"字段 '{field}' 缺失子字段: {sub}")

    if "behavior_assessment" in result:
        ba = result["behavior_assessment"]
        if isinstance(ba, dict) and "score" in ba:
            score = ba["score"]
            if not isinstance(score, (int, float)) or score < 0 or score > 10:
                errors.append(f"behavior_assessment.score 超出范围 [0,10]: {score}")
        if isinstance(ba, dict) and "key_indicators" in ba:
            if not isinstance(ba["key_indicators"], list):
                errors.append("behavior_assessment.key_indicators 应为数组")

    if "defense_assessment" in result:
        da = result["defense_assessment"]
        if isinstance(da, dict) and "contradictions" in da:
            if not isinstance(da["contradictions"], list):
                errors.append("defense_assessment.contradictions 应为数组")

    if "knowledge_score" in result:
        ks = result["knowledge_score"]
        if not isinstance(ks, (int, float)) or ks < 0 or ks > 10:
            errors.append(f"knowledge_score 超出范围 [0,10]: {ks}")

    if "overall_summary" in result:
        summary = result["overall_summary"]
        if not isinstance(summary, str) or len(summary) == 0:
            errors.append("overall_summary 应为非空字符串")

    if "evidence_refs" in result:
        refs = result["evidence_refs"]
        if not isinstance(refs, list):
            errors.append("evidence_refs 应为数组")

    return errors


def run_tests():
    """执行所有测试用例"""
    print("=" * 70)
    print("推理服务测试脚本")
    print("=" * 70)

    print("\n[步骤1] 检查服务健康状态...")
    print(f"  服务地址: {INFERENCE_URL}")
    print(f"  超时设置: {TIMEOUT}秒")

    if not check_service_health():
        print("\n⚠ 推理服务未就绪，请先启动服务:")
        print("  cd ml\\inference && python run.py")
        print("  或: uvicorn ml.inference.server:app --host 0.0.0.0 --port 8001")
        sys.exit(1)

    print("\n[步骤2] 执行推理测试...")
    total = len(TEST_CASES)
    passed = 0
    failed = 0
    total_time = 0

    for i, test_case in enumerate(TEST_CASES, 1):
        name = test_case["name"]
        desc = test_case["description"]

        print(f"\n  --- 测试用例 {i}/{total}: {name} ---")
        print(f"  描述: {desc}")
        print(f"  案件文本长度: {len(test_case['case_text'])} 字")

        try:
            result, elapsed = call_inference(test_case["case_text"])
            total_time += elapsed

            print(f"  响应时间: {elapsed:.2f}秒")

            if elapsed > 5.0:
                print("  ⚠ 响应时间超过5秒限制!")

            errors = validate_response(result)

            if errors:
                print(f"  ✗ 验证失败 ({len(errors)} 个错误):")
                for err in errors:
                    print(f"    - {err}")
                failed += 1
            else:
                print("  ✓ 字段验证通过")
                ks = result.get("knowledge_score", "N/A")
                ba = result.get("behavior_assessment", {})
                ca = result.get("cognitive_assessment", {})
                da = result.get("defense_assessment", {})
                summary = result.get("overall_summary", "N/A")[:80]
                print(f"  knowledge_score: {ks}")
                print(f"  behavior_assessment.score: {ba.get('score', 'N/A')}")
                print(f"  cognitive_assessment.score: {ca.get('score', 'N/A')}")
                print(f"  defense_assessment.score: {da.get('score', 'N/A')}")
                print(f"  overall_summary: {summary}...")
                passed += 1

        except json.JSONDecodeError as e:
            print(f"  ✗ JSON解析失败: {e}")
            failed += 1
        except urllib.error.HTTPError as e:
            print(f"  ✗ HTTP错误: {e.code} - {e.reason}")
            if hasattr(e, "read"):
                print(f"    响应: {e.read().decode()[:200]}")
            failed += 1
        except urllib.error.URLError as e:
            print(f"  ✗ 连接失败: {e.reason}")
            failed += 1
        except ValueError as e:
            print(f"  ✗ 值错误: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ 未知错误: {e}")
            failed += 1

    print("\n[步骤3] 测试结果汇总")
    print("  ========================================")
    print(f"  总计: {total} | 通过: {passed} | 失败: {failed}")
    if total > 0:
        print(f"  通过率: {passed / total * 100:.1f}%")
        print(f"  平均响应时间: {total_time / total:.2f}秒")
        print(f"  总耗时: {total_time:.2f}秒")

    if passed == total and total > 0:
        avg_time = total_time / total
        if avg_time <= 5.0:
            print("\n  ✓ 所有测试通过!")
            print(f"  ✓ 平均响应时间 ({avg_time:.2f}s) 在5秒限制内")
        else:
            print("\n  ✓ 所有测试通过!")
            print(f"  ⚠ 平均响应时间 ({avg_time:.2f}s) 超过5秒限制")
    else:
        print("\n  ✗ 部分测试失败，请检查服务配置")
        sys.exit(1)


def main():
    """主入口"""
    try:
        # 将backend目录加入路径以导入prompts模块
        backend_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "backend",
        )
        sys.path.insert(0, backend_dir)
    except NameError:
        pass

    if len(sys.argv) > 1 and sys.argv[1] == "--health-only":
        healthy = check_service_health()
        sys.exit(0 if healthy else 1)

    run_tests()


if __name__ == "__main__":
    import os

    main()
