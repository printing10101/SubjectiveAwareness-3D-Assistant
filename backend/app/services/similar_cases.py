"""类案检索服务模块.

使用 LLM 基于案件文本来查找相似案例。
"""

from dataclasses import dataclass
from typing import Any

from loguru import logger

from app.services.ollama_client import get_client
from app.services.prompts import SIMILAR_CASES_PROMPT


_MAX_CASE_TEXT_LENGTH: int = 1000


@dataclass
class SimilarCaseResult:
    """相似案例检索结果."""
    cases: list[dict[str, Any]]  # 相似案例列表
    error: bool = False  # 标记是否为错误降级结果
    error_message: str | None = None  # 错误信息（仅错误时有值）
    truncated: bool = False  # 标记是否截断了原文


async def find_similar_cases(
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
        >>> result = await find_similar_cases("被告人实施盗窃...")
        >>> if result.error:
        >>>     print("检索失败，无相似案例")
        >>> else:
        >>>     print(f"找到 {len(result.cases)} 个相似案例")
    """
    # 检查是否需要截断
    truncated = len(case_text) > _MAX_CASE_TEXT_LENGTH
    if truncated:
        logger.warning(
            "案件文本过长，截取前 {} 字符进行检索（原文 {} 字符）",
            _MAX_CASE_TEXT_LENGTH,
            len(case_text),
        )

    truncated_text = case_text[:_MAX_CASE_TEXT_LENGTH]
    prompt: str = SIMILAR_CASES_PROMPT.format(case_text=truncated_text)

    try:
        client = get_client()
        data = await client.generate_json(prompt, field="similar_cases")

        # 处理返回结果
        cases: list[dict[str, Any]] = []
        if isinstance(data, list):
            cases = data
        elif isinstance(data, dict):
            cases = data.get("similar_cases", [])

        # 验证每个案例的结构
        valid_cases: list[dict[str, Any]] = []
        for case in cases:
            if isinstance(case, dict) and ("case_id" in case or "title" in case):
                if "similarity" in case:
                    try:
                        sim = float(case["similarity"])
                        case["similarity"] = max(0.0, min(1.0, sim))
                    except (ValueError, TypeError):
                        case["similarity"] = 0.5  # 默认相似度
                valid_cases.append(case)

        # 限制返回数量
        valid_cases = valid_cases[:top_k]

        return SimilarCaseResult(
            cases=valid_cases,
            error=False,
            truncated=truncated,
        )

    except Exception as e:  # noqa: BLE001
        logger.error("查找相似案例失败: {}", e)
        return SimilarCaseResult(
            cases=[],
            error=True,
            error_message=str(e),
            truncated=truncated,
        )
