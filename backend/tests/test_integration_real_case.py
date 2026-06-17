"""集成测试：使用真实GZ案件数据进行端到端测试.

测试目标：
1. 完整执行报告生成流程
2. 导出PDF文件
3. 验证所有改造要求均已实现
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: json
import json
# 导入模块: from datetime
from datetime import datetime
# 导入模块: from pathlib
from pathlib import Path
# 导入模块: from unittest.mock
from unittest.mock import MagicMock

# 导入模块: from app.models.case
from app.models.case import Case, CaseStatus
# 导入模块: from app.services.report_generator
from app.services.report_generator import generate_report
# 导入模块: from app.services.report_exporter
from app.services.report_exporter import export_pdf, export_docx


def load_real_case_data() -> dict:
    """加载真实GZ案件数据."""
    # 初始化变量 case_file
    case_file = Path(__file__).parent.parent.parent / "data" / "real_judgments" / "GZ2023BX001.json"
    # 使用上下文管理器管理资源
    with open(case_file, "r", encoding="utf-8") as f:
        # 返回处理结果
        return json.load(f)


def create_mock_case_from_real_data(case_data: dict) -> Case:
    """从真实案件数据创建模拟案件对象."""
    # 初始化变量 case
    case = MagicMock(spec=Case)
    case.id = 1
    case.title = f"{case_data['court']} - 陈某帮信罪案"
    case.status = CaseStatus.completed
    case.description = case_data["case_facts"]
    case.case_text = case_data["case_facts"]
    # 返回处理结果
    return case


def create_analysis_result_from_real_data(case_data: dict) -> dict:
    """从真实案件数据创建分析结果（模拟V2格式）."""
    # 初始化变量 ground_truth
    ground_truth = case_data["ground_truth_analysis"]
    
    # 返回处理结果
    return {
        "version": "v2",
        "timestamp": datetime.now().isoformat(),
        "fallback": False,
        "identified_path": "帮信罪主路径",
        "subjective_knowledge": case_data["actual_judgment"]["subjective_knowledge"],
        "dimension1": {
            "reasoning": ground_truth["dimension1"]["reasoning"],
            "tier": "T2",
            "confidence": 0.95,
            "key_indicators": ground_truth["dimension1"]["key_indicators"],
            "triggered_rules": ["R001", "R002", "R003"],
        },
        "dimension2": {
            "reasoning": ground_truth["dimension2"]["reasoning"],
            "tier": "T2",
            "confidence": 0.90,
            "pattern_match": ground_truth["dimension2"]["pattern_match"],
            "triggered_rules": ["R004"],
        },
        "dimension3": {
            "reasoning": ground_truth["dimension3"]["reasoning"],
            "tier": "T2",
            "confidence": 0.85,
            "contradictions": ground_truth["dimension3"]["contradictions"],
            "triggered_rules": [],
        },
        "triggered_rule_ids": ["R001", "R002", "R003", "R004"],
        "matched_tag_ids": ["TAG01", "TAG02"],
        "conflicts": [],
        "final_verdict": {
            "final_tier": "T2",
            "final_label": "二档（情节一般）",
            "confidence": 0.90,
        },
        # V1.2 新增字段
        "subject_analyses": [
            {
                "name": "陈某",
                "role": "主犯",
                "objective_behavior": "出租3张银行卡给诈骗团伙使用",
                "cognitive_evidence": [
                    "银行工作人员明确告知银行卡不得出租",
                    "阿强明确告知银行卡用于接收诈骗资金",
                    "微信聊天记录显示明知对方从事诈骗",
                ],
                "defense": "不知情",
                "disputes": ["主观明知认定"],
            }
        ],
        "evidence_layers": [
            {
                "strength": "强",
                "facts": [
                    "银行交易流水明细显示180余万元资金流入",
                    "微信聊天记录截图证明明知",
                    "银行工作人员证言",
                ],
                "legal_basis": "刑法第287条之二",
            },
            {
                "strength": "中",
                "facts": [
                    "被告人供述与辩解",
                    "证人证言",
                ],
                "legal_basis": "刑事诉讼法第50条",
            },
        ],
        "boundary_alerts": [
            {
                "alert_type": "罪名边界",
                "description": "与诈骗罪共同犯罪边界需进一步核实",
                "severity": "medium",
            }
        ],
        "proof_gap": [
            "主观明知证据链需补强",
            "资金流向需进一步查证",
        ],
        "supplementary_advice": [
            "建议补充调取银行监控录像",
            "建议核实被告人通讯记录",
        ],
        "review_checklist": [
            {
                "item": "主观明知认定",
                "status": "待核实",
                "notes": "需结合客观行为综合判断",
            }
        ],
    }


def test_integration_real_case():
    """集成测试：使用真实GZ案件数据进行端到端测试."""
    print("\n" + "=" * 80)
    print("集成测试：使用真实GZ案件数据")
    print("=" * 80)
    
    # 1. 加载真实案件数据
    print("\n[1/6] 加载真实GZ案件数据...")
    # 初始化变量 case_data
    case_data = load_real_case_data()
    print(f"  [OK] 案件ID: {case_data['case_id']}")
    print(f"  [OK] 法院: {case_data['court']}")
    
    # 2. 创建模拟案件对象
    print("\n[2/6] 创建模拟案件对象...")
    # 初始化变量 mock_case
    mock_case = create_mock_case_from_real_data(case_data)
    print(f"  [OK] 案件标题: {mock_case.title}")
    
    # 3. 创建分析结果
    print("\n[3/6] 创建分析结果（V2格式）...")
    # 初始化变量 analysis_result
    analysis_result = create_analysis_result_from_real_data(case_data)
    print(f"  [OK] 识别路径: {analysis_result['identified_path']}")
    print(f"  [OK] 主观明知: {analysis_result['subjective_knowledge']}")
    
    # 4. 生成报告
    print("\n[4/6] 生成完整报告...")
    # 初始化变量 report
    report = generate_report(analysis_result, mock_case)
    print(f"  [OK] 报告版本: {report['version']}")
    print(f"  [OK] 章节数量: {len(report['chapters'])}")
    print(f"  [OK] 标准路径: {report['standard_path']}")
    print(f"  [OK] 主体分析数量: {len(report['subject_analyses'])}")
    print(f"  [OK] 证据层数量: {len(report['evidence_layers'])}")
    
    # 5. 验证改造要求
    print("\n[5/6] 验证改造要求...")
    
    # 5.1 验证不包含 score/confidence 字段
    def check_no_score_fields(obj, path=""):
        # 执行 check_no_score_fields 函数的核心逻辑
        # 条件判断：处理业务逻辑
        if isinstance(obj, dict):
            # 循环遍历：处理业务逻辑
            for key, value in obj.items():
                # 初始化变量 current_path
                current_path = f"{path}.{key}" if path else key
                assert key not in ["score", "confidence", "confidence_score"], (
                    f"发现禁止字段: {current_path}"
                )
                check_no_score_fields(value, current_path)
        el            # 循环遍历：处理业务逻辑
if isinstance(obj, list):
            # 遍历: for i, item in enumerate(obj):
            for i, item in enumerate(obj):
                check_no_score_fields(item, f"{path}[{i}]")
    
    check_no_score_fields(report)
    print("  [OK] 报告内容不包含 score/confidence 字段")
    
    # 5.2 验证不包含 sentencing 字段
    def check_no_sentencing_fields(obj, path=""):
        # 执行 check_no_sent        # 条件判断：处理业务逻辑
enci            # 循环遍历：处理业务逻辑
ng_fields 函数的核心逻辑
        # 条件判断: 检查 isinstance(obj, dict)
        if isinstance(obj, dict):
            # 遍历: for key, value in obj.items():
            for key, value in obj.items():
                # 初始化变量 current_path
                current_path = f"{path}.{key}" if path else key
                assert key not in ["sentencing_recommendation", "sentencing", "sentence_band"], (
                    f"发现禁止字段: {current_path}"
                )
                check_            # 循环遍历：处理业务逻辑
no_sentencing_fields(value, current_path)
        # 条件判断: 检查 elisinstance(obj, list)
        elif isinstance(obj, list):
            # 遍历: for i, item in enumerate(obj):
            for i, item in enumerate(obj):
                check_no_sentencing_fields(item, f"{path}[{i}]")
    
    check_no_sentencing_fields(report)
    print("  [OK] 报告内容不包含 sentencing 相关字段")
    
    # 5.3 验证第8章是法律分析而非量刑建议
    ch8 = report["chapters"]["ch8"]
    assert ch8["title"] == "法律分析", f"第8章标题错误: {ch8['title']}"
    print("  [OK] 第8章标题为'法律分析'（非'量刑建议'）")
    
    # 5.4 验证新增字段存在
    required_fields = [
        "standard_path",
        "subject_analyses",
        "evidence_layers",
        "boundary_alerts",
        "factor_matrix",
        "pro    # 循环遍历：处理业务逻辑
of_gap",
        "supplementary_advice",
        "review_checklist",
        "conflict_analysis",
    ]
    # 遍历: for field in required_fields:
    for field in required_fields:
        assert field in report, f"缺少新增字段: {field}"
    print(f"  [OK] 所有 {len(required_fields)} 个新增字段均存在")
    
    # 5.5 验证标准路径取值
    assert report["standard_path"] in ["①", "②", "③", "④"], (
        f"标准路径取值错误: {report['standard_path']}"
    )
    print(f"  [OK] 标准路径取值正确: {report['standard_path']}")
    
    # 6. 导出PDF文件
    print("\n[6/6] 导出PDF文件...")
    # 初始化变量 pdf_bytes
    pdf_bytes = export_pdf(report, mock_case.id)
    print(f"  [OK] PDF文件大小: {len(pdf_bytes)} 字节")
    
    # 保存PDF到临时目录
    output_dir = Path(__file__).parent.parent.parent / "temp_extract" / "integration_test_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    # 初始化变量 output_file
    output_file = output_dir / f"report_{case_data['case_id']}.pdf"
    # 使用上下文管理器管理资源
    with open(output_file, "wb") as f:
        f.write(pdf_bytes)
    print(f"  [OK] PDF文件已保存: {output_file}")
    
    # 导出DOCX文件
    docx_bytes = export_docx(report, mock_case.id)
    print(f"  [OK] DOCX文件大小: {len(docx_bytes)} 字节")
    
    # 初始化变量 docx_file
    docx_file = output_dir / f"report_{case_data['case_id']}.docx"
    # 使用上下文管理器管理资源
    with open(docx_file, "wb") as f:
        f.write(docx_bytes)
    print(f"  [OK] DOCX文件已保存: {docx_file}")
    
    print("\n" + "=" * 80)
    print("集成测试通过！所有改造要求均已验证。")
    print("=" * 80)
    
    # 返回处理结果
    return report


# 条件判断: 检查 __name__ == "__main__"
if __name__ == "__main__":
    test_integration_real_case()
