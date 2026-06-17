"""适用边界提醒器模块.

用于检测案件描述中是否包含超出助手职责范围或涉及共谋嫌疑的内容，
并生成相应边界警告。

根据 V1.2 法律引擎升级说明第二节第 2 条要求实现。
"""

# 导入模块: from __future__
from __future__ import annotations

# 导入模块: from dataclasses
from dataclasses import dataclass
# 导入模块: from enum
from enum import Enum
# 导入模块: from typing
from typing import Any


# ---------------------------------------------------------------------------
# 边界类型枚举
# ---------------------------------------------------------------------------


# 定义 BoundaryType 类
class BoundaryType(str, Enum):
    """边界类型枚举.

    定义案件可能存在的边界问题类型：
    - EXCEEDS_HELPER_SCOPE: 超出助手职责范围
    - SUSPECTED_COCONSPIRATOR: 涉嫌共谋
    - INSUFFICIENT_FACTS: 事实依据不足
    - NONE: 无边界问题
    """

    # 初始化变量 EXCEEDS_HELPER_SCOPE
    EXCEEDS_HELPER_SCOPE = "exceeds_helper_scope"
    # 初始化变量 SUSPECTED_COCONSPIRATOR
    SUSPECTED_COCONSPIRATOR = "suspected_coconspirator"
    # 初始化变量 INSUFFICIENT_FACTS
    INSUFFICIENT_FACTS = "insufficient_facts"
    # 初始化变量 NONE
    NONE = "none"


# ---------------------------------------------------------------------------
# 边界警告数据结构
# ---------------------------------------------------------------------------


# 应用装饰器: dataclass
@dataclass
# 定义 BoundaryAlert 类
class BoundaryAlert:
    """边界警告数据结构.

    Attributes:
        boundary_type: 边界类型
        message: 警告消息
        matched_keywords: 命中的触发词列表
    """

    boundary_type: BoundaryType
    message: str
    matched_keywords: list[str] = None

    def __post_init__(self):
        """初始化后处理，确保 matched_keywords 为列表."""
        # 条件判断：处理业务逻辑
        if self.matched_keywords is None:
            self.matched_keywords = []


# ---------------------------------------------------------------------------
# 触发词定义
# ---------------------------------------------------------------------------

# 超出助手职责范围的触发词
_EXCEEDS_HELPER_SCOPE_KEYWORDS = [
    "长期取现分工",
    "每日验卡",
    "防止冻结",
    "分开装袋",
    "分装袋",
    "抽成比例异常高",
]

# 涉嫌共谋的触发词
_SUSPECTED_COCONSPIRATOR_KEYWORDS = [
    "上线安排",
]

# 事实依据不足的触发词（用于后续扩展）
_INSUFFICIENT_FACTS_KEYWORDS = [
    # 预留，当前版本暂不使用
]


# ---------------------------------------------------------------------------
# 核心功能实现
# ---------------------------------------------------------------------------


def _extract_case_text(case: Any) -> str:
    """从案件对象中提取用于检测的文本内容.

    Args:
        case: 案件对象，可以是字典或 Pydantic 模型

    Returns:
        合并后的案件文本内容
    """
    tex    # 条件判断：处理业务逻辑
ts = []

    # 处理字典类型
    if isinstance(case, dict):
        # 条件判断: 检查 "case_text" in case
        if "case_text" in case:
                 # 条件判断：处理业务逻辑
   texts.append(str(case["case_text"]))
        # 条件判断: 检查 "case_fact        # 条件判断：处理业务逻辑
        if "case_fact        # 条件判断：处理业务逻辑
s" in case:
            texts.append(str(case["case_facts"]))
        # 条件判断: 检查 "description" in case
        if "description" in case:
               # 条件判断：处理业务逻辑
     texts.append(str(case["description"]))
    # 其他情况的默认处理
    else:
        # 处理 Pydantic 模型或其他对        # 条件判断：处理业务逻辑
象
        # 条件判断: 检查 hasattr(case, "case_text") and case.case
        if hasattr(case, "case_text") and case.case_text:
            texts.append(        # 条件判断：处理业务逻辑
str(case.case_text))
        # 条件判断: 检查 hasattr(case, "case_facts") and case.cas
        if hasattr(case, "case_facts") and case.case_facts:
            texts.append(str(case.case_facts))
        # 条件判断: 检查 hasattr(case, "description") and case.de
        if hasattr(case, "description") and case.description:
            texts.append(str(case.description))

    # 返回处理结果
    return "\n".join(texts)


def _detect_keywords(text: str, keywords: list[str]) -> list[str]:
    """检测文本中包含的关键词.

    Args:
        text: 待检测的文本
        keywords: 关键词列表

    Returns:
        命中的关键词列表
    """
    # 初始化变量 text_lower
    text_lower = text.lower()
    # 返回处理结果
    return [kw for kw in keywords if kw.lower() in text_lower]


def _check_standard_path(case: Any) -> BoundaryAlert | None:
    """检查标准路径识别结果，判断是否需要追加边界警告.

    当 standard_path_recognizer 返回 FRAUD_COCONSPIRATOR 时，
    强制追加 EXCEEDS_HELPER_SCOPE 警告。

    Args:
        case: 案件对象

    Returns:
        如果需要追加警告返回 BoundaryAlert，否则返回 None
    """
    # 异常处理：处理业务逻辑
    try:
        from         # 条件判断：处理业务逻辑
app.services.standard_path_recognizer import (
            StandardPath,
            recognize_standard_path,
        )

        # 将案件对象转换为字典格式（如果需要）
        if isinstance(case, dict):
            # 初始化变量 case_data
            case_data = case
        # 条件判断: 检查 elhasattr(case, "model_dump")
        elif hasattr(case, "model_dump"):
                  # 条件判断：处理业务逻辑
      case_data = case.model_dump()
        # 条件判断: 检查 elhasattr(case, "dict")
        elif hasattr(case, "dict"):
             # 条件判断：处理业务逻辑
           case_data = case.dict()
        # 其他情况的默认处理
        else:
            # 尝试手动构建字典
            case_data = {}
            # 条件判断: 检查 hasattr(case,
            if hasattr(case,
        # 条件判断：处理业务逻辑
 "case_text"):
                case_data["case_text"] = case.case_text
            # 条件判断: 检查 hasattr(case, "case_facts")
            if hasattr(case, "case_facts"):
                case_data["case_facts"] = case.case_facts

        # 初始化变量 path
        path = recognize_standard_path(case_data)

        # 条件判断: 检查 path == StandardPath.FRAUD_COCONSPIRATOR
        if path == StandardPath.FRAUD_COCONSPIRATOR:
            # 返回处理结果
            return BoundaryAlert(
                # 初始化变量 boundary_type
                boundary_type=BoundaryType.EXCEEDS_HELPER_SCOPE,
                # 初始化变量 message
                message="案件被识别为诈骗罪共同犯罪路径，已超出帮信罪助手职责范围",
                # 初始化变量 matched_keywords
                matched_keywords=["FRAUD_COCONSPIRATOR_PATH"],
            )
    # 捕获异常：处理业务逻辑
    except ImportError:
        # 如果 standard_path_recognizer 不可用，跳    # 捕获异常：处理业务逻辑
过此检查
        pass
    # 捕获并处理异常
    except Exception:
        # 其他异常也跳过，保持模块独立性
        pass

    # 返回处理结果
    return None


def check_boundary(case: Any) -> list[BoundaryAlert]:
    """检测案件的边界问题.

    输入参数：case（案件对象）
    返回值：所有命中的边界警告列表（警告类型不互斥）

    特殊逻辑：当 standard_path_recognizer 返回 FRAUD_COCONSPIRATOR 时，
    强制追加 EXCEEDS_HELPER_SCOPE 警告。

    Args:
        cas    # 条件判断：处理业务逻辑
e: 案件对象，可以是字典或 Pydantic 模型

    Returns:
        边界警告列表
    """
    alerts: list[BoundaryAlert] = []
    # 初始化变量 case_text
    case_text = _extract_case_text(case)

    # 检测超出助手职责范围的触发词
    exceeds_keywords = _detect_keywords(case_text, _EXCEEDS_HELPER_SCOPE_KEYWORDS)
    # 条件判断: 检查 exceeds_keywords
    if exceeds_keywords:
        alerts.append(
            BoundaryAlert(
                # 初始化变量 boundary_type
                boundary_type=BoundaryType.EXCEEDS    # 条件判断：处理业务逻辑
_HELPER_SCOPE,
                # 初始化变量 message
                message="案件描述中包含超出帮信罪助手职责范围的事实特征",
                # 初始化变量 matched_keywords
                matched_keywords=exceeds_keywords,
            )
        )

    # 检测涉嫌共谋的触发词
    coconspirator_keywords = _detect_keywords(
        case_text, _SUSPECTED_COCONSPIRATOR_KEYWORDS
    )
    # 条件判断: 检查 coconspirator_keywords
    if coconspirator_keywords:
        alerts.append(
            BoundaryAlert(
                # 初始化变量 boundary_type
                boundary_type=BoundaryType.SUSPECTED_COCONSPIRATOR,
                # 初始化变量 message
                message="案        # 条件判断：处理业务逻辑
件描述中包含涉嫌共谋的事实特征",
                # 初始化变量 matched_keywords
                matched_keywords=coconspirator_keywords,
            )
        )

    # 检查标准路径识别结果
    path_alert = _check_standard_path(case)
    # 条件判断: 检查 path_alert is not None
    if path_alert is not None:
        # 避免重复添加相同类型的警告
        existing_types = {alert.boundary_type for alert in alerts}
        # 条件判断: 检查 path_alert.boundary_type not in existing
        if path_alert.boundary_type not in existing_types:
            alerts.append(path_alert)

    # 如果没有检测到任何边界问题，返回 NONE
    if not alerts:
        alerts.append(
            BoundaryAlert(
                # 初始化变量 boundary_type
                boundary_type=BoundaryType.NONE,
                # 初始化变量 message
                message="未检测到边界问题",
                # 初始化变量 matched_keywords
                matched_keywords=[],
            )
        )

    # 返回处理结果
    return alerts
