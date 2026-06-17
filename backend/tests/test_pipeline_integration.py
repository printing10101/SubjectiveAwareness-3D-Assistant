"""管线集成端到端测试.

验证 V1.2 新8步骤流程的完整性和正确性：
1. 标签提取
2. 规范路径识别
3. 多主体分层
4. 证据强度分层
5. 边界提醒
6. 三维度打分
7. 结论生成
8. 冲突校验
"""

# 导入模块: pytest
import pytest
# 导入模块: from app.services.pipeline
from app.services.pipeline import analyze_pipeline_v2
# 导入模块: from app.types.evidence_layer
from app.types.evidence_layer import EvidenceLayerReport


# 应用装饰器: pytest.fixture
@pytest.fixture
def bangxin_case_text():
    """帮信罪典型案例文本."""
    # 返回处理结果
    return """
    被告人张三明知他人利用信息网络实施犯罪活动，仍为其提供银行卡用于接收和转移资金。
    经查，张三的银行卡共接收诈骗资金50万元，并多次配合取现转账。
    张三辩称不知情，但其行为明显异常：短期内频繁大额转账，且无法说明合理用途。
    """


# 应用装饰器: pytest.fixture
@pytest.fixture
def fraud_joint_case_text():
    """诈骗罪共同犯罪案例文本."""
    # 返回处理结果
    return """
    被告人李四与诈骗团伙事先通谋，分工合作实施电信网络诈骗。
    李四负责提供技术支持，包括搭建虚假网站和维护服务器。
    诈骗团伙通过李四搭建的平台实施诈骗，共骗取被害人200万元。
    李四与诈骗团伙成员有明确的分工合作和利益分配。
    """


# 应用装饰器: pytest.fixture
@pytest.fixture
def concealment_case_text():
    """掩饰隐瞒犯罪所得案例文本."""
    # 返回处理结果
    return """
    被告人王五明知是他人犯罪所得，仍帮助转移资金。
    王五通过多个银行账户将犯罪所得资金分散转移，试图掩盖资金来源。
    经查明，王五转移的资金系上游犯罪所得，其主观上明知是犯罪所得。
    """


# 应用装饰器: pytest.fixture
@pytest.fixture
def insufficient_evidence_case_text():
    """证据不足案例文本."""
    # 返回处理结果
    return """
    被告人赵六被指控帮助信息网络犯罪活动。
    现有证据仅显示赵六的银行卡有异常资金流动，但缺乏直接证据证明其主观明知。
    赵六辩称银行卡已遗失，对异常交易不知情。
    """


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_pipeline_v2_complete_flow(bangxin_case_text):
    """测试完整的8步骤流程."""
    # 初始化变量 result
    result = await analyze_pipeline_v2(bangxin_case_text)
    
    # 验证基础结构
    assert result["version"] == "v2"
    assert "dimension1" in result
    assert "dimension2" in result
    assert "dimension3" in result
    assert "final_verdict" in result
    
    # 验证 V1.2 新增字段
    assert "identified_path" in result
    assert "scoring_mode" in result
    assert "should_cite_article_287_2" in result
    assert "can_affirm_knowledge" in result
    assert "evidence_layer_count" in result
    assert "boundary_alert_count" in result
    
    # 验证帮信罪路径识别
    assert result["identified_path"] == "帮信罪主路径"
    assert result["scoring_mode"] == "definitive"
    assert result["should_cite_article_287_2"] is True
    
    # 验证管道元数据
    assert "pipeline_meta" in result
    assert "stage_durations_ms" in result["pipeline_meta"]
    assert "stage_status" in result["pipeline_meta"]


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_pipeline_v2_path_aware_scoring(fraud_joint_case_text):
    """测试路径感知打分 - 诈骗罪共同犯罪路径."""
    # 初始化变量 result
    result = await analyze_pipeline_v2(fraud_joint_case_text)
    
    # 验证路径识别
    assert result["identified_path"] == "诈骗罪共同犯罪路径"
    assert result["scoring_mode"] == "reference_only"
    assert result["should_cite_article_287_2"] is False
    
    # 验证三维度打分仍然执行
    assert "dimension1" in result
    assert "dimension2" in result
    assert "dimension3" in result


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_pipeline_v2_concealment_path(concealment_case_text):
    """测试掩饰隐瞒犯罪所得路径."""
    # 初始化变量 result
    result = await analyze_pipeline_v2(concealment_case_text)
    
    # 验证路径识别
    assert result["identified_path"] == "掩饰隐瞒犯罪所得路径"
    assert result["scoring_mode"] == "reference_only"
    assert result["should_cite_article_287_2"] is False


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_pipeline_v2_evidence_layering(bangxin_case_text):
    """测试证据强度分层."""
    # 初始化变量 result
    result = await analyze_pipeline_v2(bangxin_case_text)
    
    # 验证证据层计数
    assert result["evidence_layer_count"] >= 0
    
    # 验证 can_affirm_knowledge 字段
    assert isinstance(result["can_affirm_knowledge"], bool)


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_pipeline_v2_boundary_alerts(fraud_joint_case_text):
    """测试边界提醒."""
    # 初始化变量 result
    result = await analyze_pipeline_v2(fraud_joint_case_text)
    
    # 验证边界提醒计数
    assert result["boundary_alert_count"] >= 0


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_pipeline_v2_fallback_handling(insufficient_evidence_case_text):
    """测试降级处理."""
    # 初始化变量 result
    result = await analyze_pipeline_v2(insufficient_evidence_case_text)
    
    # 验证即使证据不足也能返回结果
    assert result["version"] == "v2"
    assert "final_verdict" in result
    
    # 验证路径识别为待核实
    assert result["identified_path"] == "规范路径待核实"


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_pipeline_v2_conclusion_generation(bangxin_case_text):
    """测试结论生成."""
    # 初始化变量 result
    result = await analyze_pipeline_v2(bangxin_case_text)
    
    # 验证结论文本存在
    assert "conclusion_text" in result
    assert isinstance(result["conclusion_text"], str)
    assert len(result["conclusion_text"]) > 0


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_pipeline_v2_conflict_detection(bangxin_case_text):
    """测试冲突校验."""
    # 初始化变量 result
    result = await analyze_pipeline_v2(bangxin_case_text)
    
    # 验证冲突字段存在
    assert "conflicts" in result
    assert isinstance(result["conflicts"], list)


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_pipeline_v2_confidence_calculation(bangxin_case_text):
    """测试置信度计算."""
    # 初始化变量 result
    result = await analyze_pipeline_v2(bangxin_case_text)
    
    # 验证置信度存在且在合理范围
    assert "confidence" in result
    assert 0.0 <= result["confidence"] <= 1.0


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_pipeline_v2_stage_durations(bangxin_case_text):
    """测试各阶段耗时记录."""
    # 初始化变量 result
    result = await analyze_pipeline_v2(bangxin_case_text)
    
    # 验证阶段耗时记录
    stage_durations = result["pipeline_meta"]["stage_durations_ms"]
    assert "_total" in stage_durations
    assert stage_durations["_total"] > 0
    
    # 验证关键阶段都有记录
    expected_stages = [
        "complexity", "knowledge", "tags", "path_identification",
        "subject_stratification", "evidence_layering", "boundary_check",
        "rules", "dimension1", "dimension2", "dimension3",
        "combine", "conclusion", "conflicts"
    ]
    
    # 遍历: for stage in expected_stages:
    for stage in expected_stages:
        assert stage in stage_durations, f"阶段 {stage} 的耗时未记录"


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_pipeline_v2_disclaimer(bangxin_case_text):
    """测试免责声明."""
    # 初始化变量 result
    result = await analyze_pipeline_v2(bangxin_case_text)
    
    # 验证免责声明存在
    assert "disclaimer" in result
    assert isinstance(result["disclaimer"], str)
    assert len(result["disclaimer"]) > 0
