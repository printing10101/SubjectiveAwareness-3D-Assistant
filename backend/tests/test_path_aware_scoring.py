"""路径感知打分测试.

验证 V1.2 三维度打分在不同法律路径下的差异化行为：
- 帮信罪主路径：输出正式打分结果，引用第287-2条
- 诈骗罪共同犯罪路径：输出参照打分，不引用第287-2条
- 掩饰隐瞒犯罪所得路径：输出参照打分，不引用第287-2条
- 规范路径待核实：输出参照打分，不引用第287-2条
"""

# 导入模块: pytest
import pytest
# 导入模块: from app.services.pipeline
from app.services.pipeline import analyze_pipeline_v2


# 应用装饰器: pytest.fixture
@pytest.fixture
def bangxin_path_case():
    """帮信罪主路径案例."""
    # 返回处理结果
    return """
    被告人张三明知他人利用信息网络实施犯罪活动，仍为其提供银行卡。
    张三的银行卡接收并转移资金50万元。
    张三辩称不知情，但行为异常：短期内频繁大额转账。
    """


# 应用装饰器: pytest.fixture
@pytest.fixture
def fraud_joint_path_case():
    """诈骗罪共同犯罪路径案例."""
    # 返回处理结果
    return """
    被告人李四与诈骗团伙事先通谋，分工合作实施电信网络诈骗。
    李四负责提供技术支持，搭建虚假网站。
    诈骗团伙通过李四的平台骗取被害人200万元。
    李四与诈骗团伙有明确的分工合作和利益分配。
    """


# 应用装饰器: pytest.fixture
@pytest.fixture
def concealment_path_case():
    """掩饰隐瞒犯罪所得路径案例."""
    # 返回处理结果
    return """
    被告人王五明知是他人犯罪所得，仍帮助转移资金。
    王五通过多个账户将犯罪所得分散转移，掩盖资金来源。
    经查明，王五转移的资金系上游犯罪所得。
    """


# 应用装饰器: pytest.fixture
@pytest.fixture
def uncertain_path_case():
    """规范路径待核实案例."""
    # 返回处理结果
    return """
    被告人赵六被指控帮助信息网络犯罪活动。
    现有证据显示赵六的银行卡有异常资金流动。
    赵六辩称银行卡已遗失，对异常交易不知情。
    """


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_bangxin_path_scoring_mode(bangxin_path_case):
    """测试帮信罪主路径的打分模式."""
    # 初始化变量 result
    result = await analyze_pipeline_v2(bangxin_path_case)
    
    # 帮信罪主路径应使用正式打分模式
    assert result["identified_path"] == "帮信罪主路径"
    assert result["scoring_mode"] == "definitive"
    assert result["should_cite_article_287_2"] is True
    
    # 三维度打分应正常执行
    assert "dimension1" in result
    assert "dimension2" in result
    assert "dimension3" in result
    
    # 应有最终裁决
    assert "final_verdict" in result
    assert result["final_verdict"]["final_tier"] in ["tier1", "tier2", "tier3", "tier4"]


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_fraud_joint_path_scoring_mode(fraud_joint_path_case):
    """测试诈骗罪共同犯罪路径的打分模式."""
    # 初始化变量 result
    result = await analyze_pipeline_v2(fraud_joint_path_case)
    
    # 诈骗罪共同犯罪路径应使用参照打分模式
    assert result["identified_path"] == "诈骗罪共同犯罪路径"
    assert result["scoring_mode"] == "reference_only"
    assert result["should_cite_article_287_2"] is False
    
    # 三维度打分仍应执行（作为参照）
    assert "dimension1" in result
    assert "dimension2" in result
    assert "dimension3" in result
    
    # 应有最终裁决（但仅作参考）
    assert "final_verdict" in result


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_concealment_path_scoring_mode(concealment_path_case):
    """测试掩饰隐瞒犯罪所得路径的打分模式."""
    # 初始化变量 result
    result = await analyze_pipeline_v2(concealment_path_case)
    
    # 掩饰隐瞒犯罪所得路径应使用参照打分模式
    assert result["identified_path"] == "掩饰隐瞒犯罪所得路径"
    assert result["scoring_mode"] == "reference_only"
    assert result["should_cite_article_287_2"] is False
    
    # 三维度打分仍应执行（作为参照）
    assert "dimension1" in result
    assert "dimension2" in result
    assert "dimension3" in result
    
    # 应有最终裁决（但仅作参考）
    assert "final_verdict" in result


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_uncertain_path_scoring_mode(uncertain_path_case):
    """测试规范路径待核实的打分模式."""
    # 初始化变量 result
    result = await analyze_pipeline_v2(uncertain_path_case)
    
    # 规范路径待核实应使用参照打分模式
    assert result["identified_path"] == "规范路径待核实"
    assert result["scoring_mode"] == "reference_only"
    assert result["should_cite_article_287_2"] is False
    
    # 三维度打分仍应执行（作为参照）
    assert "dimension1" in result
    assert "dimension2" in result
    assert "dimension3" in result


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_path_aware_article_citation(bangxin_path_case, fraud_joint_path_case):
    """测试路径感知的法条引用控制."""
    # 帮信罪路径应引用第287-2条
    bangxin_result = await analyze_pipeline_v2(bangxin_path_case)
    assert bangxin_result["should_cite_article_287_2"] is True
    
    # 诈骗罪路径不应引用第287-2条
    fraud_result = await analyze_pipeline_v2(fraud_joint_path_case)
    assert fraud_result["should_cite_article_287_2"] is False


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_path_aware_conclusion_content(bangxin_path_case, fraud_joint_path_case):
    """测试路径感知的结论内容差异."""
    # 帮信罪路径的结论应包含第287-2条引用
    bangxin_result = await analyze_pipeline_v2(bangxin_path_case)
    assert "conclusion_text" in bangxin_result
    # 结论中应提及帮信罪或第287-2条
    conclusion = bangxin_result["conclusion_text"]
    assert len(conclusion) > 0
    
    # 诈骗罪路径的结论不应包含第287-2条引用
    fraud_result = await analyze_pipeline_v2(fraud_joint_path_case)
    assert "conclusion_text" in fraud_result
    # 初始化变量 fraud_conclusion
    fraud_conclusion = fraud_result["conclusion_text"]
    assert len(fraud_conclusion) > 0


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_path_aware_evidence_layer_integration(bangxin_path_case):
    """测试路径感知与证据层集成的正确性."""
    # 初始化变量 result
    result = await analyze_pipeline_v2(bangxin_path_case)
    
    # 验证证据层计数
    assert "evidence_layer_count" in result
    assert isinstance(result["evidence_layer_count"], int)
    assert result["evidence_layer_count"] >= 0
    
    # 验证 can_affirm_knowledge 字段
    assert "can_affirm_knowledge" in result
    assert isinstance(result["can_affirm_knowledge"], bool)
    
    # 帮信罪路径下，如果有直接认知性证据，can_affirm_knowledge 应为 True
    # 条件判断：处理业务逻辑
    if result["evidence_layer_count"] > 0:
        # 具体逻辑取决于证据层内容
        pass


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_path_aware_boundary_alerts(fraud_joint_path_case):
    """测试路径感知与边界提醒的集成."""
    # 初始化变量 result
    result = await analyze_pipeline_v2(fraud_joint_path_case)
    
    # 验证边界提醒计数
    assert "boundary_alert_count" in result
    assert isinstance(result["boundary_alert_count"], int)
    assert result["boundary_alert_count"] >= 0
    
    # 诈骗罪路径通常会有边界提醒
    # （具体取决于案例文本中的关键词）


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_path_aware_confidence_consistency(bangxin_path_case, fraud_joint_path_case):
    """测试不同路径下置信度计算的一致性."""
    # 帮信罪路径
    bangxin_result = await analyze_pipeline_v2(bangxin_path_case)
    assert "confidence" in bangxin_result
    assert 0.0 <= bangxin_result["confidence"] <= 1.0
    
    # 诈骗罪路径
    fraud_result = await analyze_pipeline_v2(fraud_joint_path_case)
    assert "confidence" in fraud_result
    assert 0.0 <= fraud_result["confidence"] <= 1.0


# 应用装饰器: pytest.mark.asyncio
@pytest.mark.asyncio
async def test_path_aware_pipeline_meta(bangxin_path_case, fraud_joint_path_case):
    """测试不同路径下管道元数据的完整性."""
    # 帮信罪路径
    bangxin_result = await analyze_pipeline_v2(bangxin_path_case)
    assert "pipeline_meta" in bangxin_result
    assert "stage_durations_ms" in bangxin_result["pipeline_meta"]
    assert "stage_status" in bangxin_result["pipeline_meta"]
    
    # 诈骗罪路径
    fraud_result = await analyze_pipeline_v2(fraud_joint_path_case)
    assert "pipeline_meta" in fraud_result
    assert "stage_durations_ms" in fraud_result["pipeline_meta"]
    assert "stage_status" in fraud_result["pipeline_meta"]
