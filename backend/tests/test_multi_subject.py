"""测试多主体场景下报告的主体信息分页展示.

测试目标：
1. 验证多主体情况下 subject_analyses 字段正确生成
2. 验证每个主体信息完整且独立
3. 验证导出文件中多主体信息正确展示
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from app.models.case import Case, CaseStatus
from app.services.report_generator import generate_report
from app.services.report_exporter import export_pdf, export_docx


def create_multi_subject_case():
    """创建多主体案件测试数据."""
    case = MagicMock(spec=Case)
    case.id = 2
    case.title = "多主体帮信罪案 - 张某、李某、王某"
    case.status = CaseStatus.completed
    case.description = "张某组织李某、王某等人出租银行卡用于电信网络诈骗"
    case.case_text = """
    被告人张某，男，1990年出生，无业。
    被告人李某，男，1995年出生，无业。
    被告人王某，女，1998年出生，无业。
    
    经审理查明：被告人张某组织李某、王某等人出租银行卡用于电信网络诈骗。
    张某负责联系诈骗团伙，李某提供本人银行卡3张，王某提供本人银行卡2张。
    银行工作人员曾明确告知三人银行卡不得出租，但三人仍继续实施上述行为。
    经统计，李某银行卡流入资金120余万元，王某银行卡流入资金80余万元。
    """
    return case


def create_multi_subject_analysis():
    """创建多主体分析结果."""
    return {
        "version": "v2",
        "timestamp": datetime.now().isoformat(),
        "fallback": False,
        "identified_path": "帮信罪主路径",
        "subjective_knowledge": "明知",
        "dimension1": {
            "reasoning": "三名被告人均被银行工作人员明确告知银行卡不得出租，仍继续实施出租行为，主观明知明显",
            "tier": "T2",
            "confidence": 0.95,
            "key_indicators": ["银行工作人员告知", "持续实施行为"],
            "triggered_rules": ["R001", "R002"],
        },
        "dimension2": {
            "reasoning": "三名被告人分工合作，张某组织，李某、王某提供银行卡，形成共同犯罪",
            "tier": "T2",
            "confidence": 0.90,
            "pattern_match": "组织+提供银行卡模式",
            "triggered_rules": ["R003"],
        },
        "dimension3": {
            "reasoning": "三名被告人供述一致，无矛盾",
            "tier": "T2",
            "confidence": 0.85,
            "contradictions": [],
            "triggered_rules": [],
        },
        "triggered_rule_ids": ["R001", "R002", "R003"],
        "matched_tag_ids": ["TAG01", "TAG02", "TAG03"],
        "conflicts": [],
        "final_verdict": {
            "final_tier": "T2",
            "final_label": "二档（情节一般）",
            "confidence": 0.90,
        },
        # 多主体分析
        "subject_analyses": [
            {
                "name": "张某",
                "role": "主犯/组织者",
                "objective_behavior": "组织李某、王某出租银行卡，联系诈骗团伙",
                "cognitive_evidence": [
                    "银行工作人员明确告知银行卡不得出租",
                    "主动联系诈骗团伙商议银行卡使用事宜",
                    "微信聊天记录显示其明知对方从事诈骗活动",
                ],
                "defense": "承认组织行为但辩称不知情",
                "disputes": ["主观明知程度", "在共同犯罪中的地位"],
            },
            {
                "name": "李某",
                "role": "从犯/参与者",
                "objective_behavior": "提供本人银行卡3张给张某用于出租",
                "cognitive_evidence": [
                    "银行工作人员明确告知银行卡不得出租",
                    "张某明确告知银行卡用于接收诈骗资金",
                    "微信聊天记录显示明知对方从事诈骗",
                ],
                "defense": "受张某蛊惑，不知情",
                "disputes": ["主观明知认定", "是否受胁迫"],
            },
            {
                "name": "王某",
                "role": "从犯/参与者",
                "objective_behavior": "提供本人银行卡2张给张某用于出租",
                "cognitive_evidence": [
                    "银行工作人员明确告知银行卡不得出租",
                    "张某明确告知银行卡用于接收诈骗资金",
                    "微信聊天记录显示明知对方从事诈骗",
                ],
                "defense": "受张某蛊惑，不知情",
                "disputes": ["主观明知认定", "是否受胁迫"],
            },
        ],
        "evidence_layers": [
            {
                "strength": "强",
                "facts": [
                    "银行交易流水明细显示李某银行卡120余万元资金流入",
                    "银行交易流水明细显示王某银行卡80余万元资金流入",
                    "微信聊天记录截图证明三人明知",
                    "银行工作人员证言",
                ],
                "legal_basis": "刑法第287条之二",
            },
            {
                "strength": "中",
                "facts": [
                    "三名被告人供述与辩解",
                    "证人证言",
                ],
                "legal_basis": "刑事诉讼法第50条",
            },
        ],
        "boundary_alerts": [
            {
                "alert_type": "罪名边界",
                "description": "张某可能构成诈骗罪共同犯罪，需进一步核实",
                "severity": "high",
            },
            {
                "alert_type": "主体区分",
                "description": "需明确区分主从犯地位",
                "severity": "medium",
            },
        ],
        "proof_gap": [
            "张某与诈骗团伙的具体沟通内容需进一步查证",
            "李某、王某是否受胁迫需进一步核实",
        ],
        "supplementary_advice": [
            "建议补充调取张某与诈骗团伙的通讯记录",
            "建议核实李某、王某的经济状况以排除受胁迫可能",
            "建议调取银行监控录像证明三人亲自办理银行卡出租手续",
        ],
        "review_checklist": [
            {
                "item": "主观明知认定",
                "status": "待核实",
                "notes": "需结合三名被告人客观行为综合判断",
            },
            {
                "item": "主从犯区分",
                "status": "待核实",
                "notes": "张某系组织者，李某、王某系参与者",
            },
            {
                "item": "罪名边界",
                "status": "待核实",
                "notes": "张某可能构成诈骗罪共犯",
            },
        ],
    }


def test_multi_subject_report():
    """测试多主体报告生成."""
    print("\n" + "=" * 80)
    print("多主体场景测试")
    print("=" * 80)
    
    # 1. 创建多主体案件和分析结果
    print("\n[1/5] 创建多主体案件数据...")
    case = create_multi_subject_case()
    analysis_result = create_multi_subject_analysis()
    print(f"  [OK] 案件标题: {case.title}")
    print(f"  [OK] 主体数量: {len(analysis_result['subject_analyses'])}")
    
    # 2. 生成报告
    print("\n[2/5] 生成多主体报告...")
    report = generate_report(analysis_result, case)
    print(f"  [OK] 报告版本: {report['version']}")
    print(f"  [OK] 主体分析数量: {len(report['subject_analyses'])}")
    
    # 3. 验证多主体信息完整性
    print("\n[3/5] 验证多主体信息完整性...")
    subject_names = ["张某", "李某", "王某"]
    for i, subject in enumerate(report["subject_analyses"]):
        assert subject["name"] == subject_names[i], f"主体{i+1}名称错误: {subject['name']}"
        assert "role" in subject, f"主体{i+1}缺少role字段"
        assert "objective_behavior" in subject, f"主体{i+1}缺少objective_behavior字段"
        assert "cognitive_evidence" in subject, f"主体{i+1}缺少cognitive_evidence字段"
        assert "defense" in subject, f"主体{i+1}缺少defense字段"
        assert "disputes" in subject, f"主体{i+1}缺少disputes字段"
        print(f"  [OK] 主体{i+1} ({subject['name']}) 信息完整")
    
    # 4. 验证边界警告
    print("\n[4/5] 验证边界警告...")
    assert len(report["boundary_alerts"]) == 2, f"边界警告数量错误: {len(report['boundary_alerts'])}"
    print(f"  [OK] 边界警告数量: {len(report['boundary_alerts'])}")
    for alert in report["boundary_alerts"]:
        print(f"    - {alert['alert_type']}: {alert['description']}")
    
    # 5. 导出文件
    print("\n[5/5] 导出多主体报告文件...")
    pdf_bytes = export_pdf(report, case.id)
    print(f"  [OK] PDF文件大小: {len(pdf_bytes)} 字节")
    
    docx_bytes = export_docx(report, case.id)
    print(f"  [OK] DOCX文件大小: {len(docx_bytes)} 字节")
    
    # 保存文件
    output_dir = Path(__file__).parent.parent.parent / "temp_extract" / "integration_test_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    pdf_file = output_dir / "report_multi_subject.pdf"
    with open(pdf_file, "wb") as f:
        f.write(pdf_bytes)
    print(f"  [OK] PDF文件已保存: {pdf_file}")
    
    docx_file = output_dir / "report_multi_subject.docx"
    with open(docx_file, "wb") as f:
        f.write(docx_bytes)
    print(f"  [OK] DOCX文件已保存: {docx_file}")
    
    print("\n" + "=" * 80)
    print("多主体场景测试通过！")
    print("=" * 80)
    
    return report


if __name__ == "__main__":
    test_multi_subject_report()
