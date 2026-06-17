"""类案检索服务模块.

使用 LLM 基于案件文本来查找相似案例。
"""

# 导入模块: from dataclasses
from dataclasses import dataclass
# 导入模块: from typing
from typing import Any

# 导入模块: from loguru
from loguru import logger

# 导入模块: from app.services.ollama_client
from app.services.ollama_client import get_client
# 导入模块: from app.services.prompts
from app.services.prompts import SIMILAR_CASES_PROMPT


_MAX_CASE_TEXT_LENGTH: int = 1000


# 应用装饰器: dataclass
@dataclass
# 定义 SimilarCaseResult 类
class SimilarCaseResult:
    """相似案例检索结果."""
    cases: list[dict[str, Any]]  # 相似案例列表
    error: bool = False  # 标记是否为错误降级结果
    error_message: str | None = None  # 错误信息（仅错误时有值）
    truncated: bool = False  # 标记是否截断了原文


async def find_similar_cases(
    # 函数 find_similar_cases 的初始化逻辑
    case_text: str,
    top_k: int = 3,
) -> SimilarCaseResult:
    """使用 LLM 查找相似案例.

    将案件文本截取后作为提示词，调用 LLM 进行相似案例匹配。
    当检索失败时，返回带有 error=True 标记的降级结果，调用方可据此判断。

    Args:
        case_text: 案件事实文本
        top_k: 返回的最大相似案例数（默认 3）

    Returns:
        SimilarCaseResult: 包含 cases 列表和 error 标记的结果

    Example:
        # 异步等待操作完成
        >>> result = await find_similar_cases("被告人实施盗窃...")
        >>> if result.error:
        >>>     print("检索失败，无相似案例")
        >>> else:
        >>>     print(f"找到 {len(result.cases)} 个相似案例")
    """
    # 检查是否需要截断
    truncated = len(case_text) > _MAX_CASE_TEXT_LENGTH
    # 条件判断：处理业务逻辑
    if truncated:
        # 记录日志信息
        logger.warning(
            "案件文本过长，截取前 {} 字符进行检索（原文 {} 字符）",
            _MAX_CASE_TEXT_LENGTH,
            len(case_text),
        )

    # 初始化变量 truncated_text
    truncated_text = case_text[:_MAX_CASE_TEXT_LENGTH]
    prompt: str = SIMILAR_CASES_PROMPT.format(case_text=truncated_text)

    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 client
        client = get_client()
        # 初始化变量 data
        data = await client.generate_json(prompt, field="similar_cases")

        # 处理返回结果
        cases: list[dic        # 条件判断：处理业务逻辑
t[str, Any]] = []
        # 条件判断: 检查 isinstance(data, list)
        if isinstance(data, list):
            # 初始化变量 cases
            cases = data
        # 条件判断: 检查 elisinstance(data, dict)
        elif isinstance(data, dict):
            # 初始化变量 cases
            cases = data.get("similar_cases", [])

        # 验证每个案例的结构
        valid_cases: list[dict[str            # 条件判断：处理业务逻辑
, Any]] = []
        # 循环遍历：处理业务逻辑
        for case in cases:
            # 条件判断: 检查 i                # 条件判断：处理业务逻辑
            if i                # 条件判断：处理业务逻辑
sinstance(case, dict) and ("case_id" in case or "title" in case):
                # 条件判断: 检查 "similarity" in case
                if "similarity" in case:
                    # 异常处理：处理业务逻辑
                    try:
                        sim = float(case["similarity"])
                        case["similarity"] = max(0.0, min(1.0, sim))
                    # 捕获异常：处理业务逻辑
                    except (ValueError, TypeError):
                        case["similarity"] = 0.5  # 默认相似度
                valid_cases.append(case)

        # 限制返回数量
        valid_cases = valid_cases[:top_k]

        # 返回处理结果
        return SimilarCaseResult(
            # 初始化变量 cases
            cases=valid_cases,
            # 初始化变量 error
            error=False,
         
    # 捕获异常：处理业务逻辑
   truncated=truncated,
        )

    # 捕获并处理异常
    except Exception as e:  # noqa: BLE001
        logger.error("查找相似案例失败: {}", e)
        # 返回处理结果
        return SimilarCaseResult(
            # 初始化变量 cases
            cases=[],
            # 初始化变量 error
            error=True,
            # 初始化变量 error_message
            error_message=str(e),
            # 初始化变量 truncated
            truncated=truncated,
        )
