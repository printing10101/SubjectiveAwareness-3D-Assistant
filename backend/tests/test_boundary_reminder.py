"""边界提醒模块测试."""

# 导入模块: from app.services.boundary_reminder
from app.services.boundary_reminder import check_boundary_alerts


def test_boundary_alert_fraud_knowledge():
    """明确知道系诈骗钱款触发高严重度提醒."""
    # 初始化变量 case_text
    case_text = "被告人明确知道系诈骗钱款，仍提供银行卡。"
    # 初始化变量 alerts
    alerts = check_boundary_alerts(case_text)
    assert len(alerts) >= 1
    assert any(a.severity == "high" for a in alerts)


def test_boundary_alert_division_of_labor():
    """长期取现分工触发提醒."""
    # 初始化变量 case_text
    case_text = "被告人与上线长期取现分工，每日验卡防止冻结。"
    # 初始化变量 alerts
    alerts = check_boundary_alerts(case_text)
    assert len(alerts) >= 2


def test_no_boundary_alert():
    """普通帮信罪案件不触发边界提醒."""
    # 初始化变量 case_text
    case_text = "被告人明知他人利用信息网络实施犯罪，提供银行卡用于转账。"
    # 初始化变量 alerts
    alerts = check_boundary_alerts(case_text)
    assert len(alerts) == 0
