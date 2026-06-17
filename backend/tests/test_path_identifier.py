"""规范路径识别模块测试."""

# 导入模块: from app.services.path_identifier
from app.services.path_identifier import identify_legal_path


def test_identify_bangxin_path():
    """识别帮信罪主路径."""
    # 初始化变量 case_text
    case_text = "被告人明知他人利用信息网络实施犯罪，为其提供支付结算帮助。"
    # 初始化变量 result
    result = identify_legal_path(case_text)
    assert result == "帮信罪主路径"


def test_identify_fraud_joint_crime_path():
    """识别诈骗罪共同犯罪路径."""
    # 初始化变量 case_text
    case_text = "被告人与诈骗团伙事先通谋，分工合作实施电信网络诈骗。"
    # 初始化变量 result
    result = identify_legal_path(case_text)
    assert result == "诈骗罪共同犯罪路径"


def test_identify_concealment_path():
    """识别掩饰隐瞒犯罪所得路径."""
    # 初始化变量 case_text
    case_text = "被告人明知是犯罪所得及其收益，予以窝藏、转移、收购。"
    # 初始化变量 result
    result = identify_legal_path(case_text)
    assert result == "掩饰隐瞒犯罪所得路径"


def test_identify_uncertain_path():
    """识别规范路径待核实."""
    # 初始化变量 case_text
    case_text = "被告人提供银行卡，具体用途不明。"
    # 初始化变量 result
    result = identify_legal_path(case_text)
    assert result == "规范路径待核实"
