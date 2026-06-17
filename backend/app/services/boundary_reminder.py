"""边界提醒模块 (B4).

V1.2 法律引擎升级 - 第四步：检查案件是否超出帮信罪评价范围。
"""

# 导入模块: from loguru
from loguru import logger

# 导入模块: from app.types.evidence_layer
from app.types.evidence_layer import BoundaryAlert

# 边界提醒规则
_BOUNDARY_RULES = [
    {
        "keywords": ["明确知道系诈骗钱款", "事先知道诈骗"],
        "alert_type": "超出帮信罪范围",
        "description": "案件事实显示被告人明确知道系诈骗钱款，可能构成诈骗罪共同犯罪",
        "severity": "high",
    },
    {
        "keywords": ["长期取现分工", "上线安排"],
        "alert_type": "分工合作特征",
        "description": "案件事实显示存在长期取现分工或上线安排，可能构成诈骗罪共同犯罪",
        "severity": "high",
    },
    {
        "keywords": ["每日验卡", "防止冻结"],
        "alert_type": "规避监管行为",
        "description": "案件事实显示存在每日验卡、防止冻结等规避监管行为，可能构成掩饰隐瞒犯罪所得",
        "severity": "medium",
    },
    {
        "keywords": ["分开装袋", "掩饰隐瞒"],
        "alert_type": "掩饰隐瞒行为",
        "description": "案件事实显示存在分开装袋等掩饰隐瞒行为，可能构成掩饰隐瞒犯罪所得罪",
        "severity": "high",
    },
]


def check_boundary_alerts(case_text: str) -> list[BoundaryAlert]:
    """检查案件是否超出帮信罪评价范围.

    当出现以下事实时触发提醒：
    - 明确知道系诈骗钱款
    - 长期取现分工
    - 上线安排
    - 每日验卡、防止冻结
    - 分开装袋等掩饰隐瞒行为

    Args:
        case_text: 案件事实文本

    Returns:
        list[BoundaryAlert]: 边界提醒列表
    """
    # 记录日志信息
    logger.info("开始边界提醒检查 (B4)")

    # 初始化变量 alerts
    alerts = []
    # 循环遍历：处理业务逻辑
    for rule in        # 循环遍历：处理业务逻辑
 _BOUNDARY_RULES:
        # 遍历: for keyword in rule["keywords"]:
        for keyword in rule["keywords"]:
            # 条件判断：处理业务逻辑
            if keyword in case_text:
                # 初始化变量 alert
                alert = BoundaryAlert(
                    # 初始化变量 alert_type
                    alert_type=rule["alert_type"],
                    # 初始化变量 description
                    description=rule["description"],
                    # 初始化变量 severity
                    severity=rule["severity"],
                )
                alerts.append(alert)
                # 记录日志信息
                logger.warning(f"触发边界提醒: {alert.alert_type} - {keyword}")
                break  # 每个规则只触发一次

    # 条件判断: 检查 not alerts
    if not alerts:
        # 记录日志信息
        logger.info("未触发边界提醒")

    # 返回处理结果
    return alerts
