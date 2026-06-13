"""量刑建议服务模块.

调用 LLM 根据分析结果和法律规则生成量刑建议。
"""

import json
from dataclasses import dataclass

from loguru import logger

from app.services.ollama_client import get_client
from app.services.prompts import SENTENCING_PROMPT
from app.types.analysis import AnalysisResult


@dataclass
class SentencingSuggestion:
    """量刑建议结果."""
    suggested_sentence: str
    reasoning: str
    error: bool = False  # 标记是否为错误降级结果
    raw_response: str | None = None  # 原始响应（仅错误时有值）


async def get_sentencing_suggestion(
    analysis_result: AnalysisResult,
    legal_rules: list | None = None,
) -> SentencingSuggestion:
    """从 LLM 获取量刑建议.

    将案件分析结果和适用法律规则组合为提示词，调用 LLM 生成量刑建议。
    当分析失败时，返回带有 error=True 标记的降级结果，调用方可据此判断。

    Args:
        analysis_result: 案件分析结果字典
        legal_rules: 适用法律规则列表（可选）

    Returns:
        SentencingSuggestion: 包含 suggested_sentence、reasoning 和 error 标记的建议

    Example:
        >>> result = await get_sentencing_suggestion({"crime": "theft"})
        >>> if result.error:
        >>>     print("分析失败，使用降级结果")
        >>> else:
        >>>     print(f"建议刑期: {result.suggested_sentence}")
    """
    if legal_rules:
        rules_text: str = "\n".join([str(r) for r in legal_rules])
    else:
        rules_text = "无"

    prompt: str = SENTENCING_PROMPT.format(
        analysis_result=json.dumps(analysis_result, ensure_ascii=False),
        legal_rules=rules_text,
    )

    try:
        client = get_client()
        result = await client.generate_json(prompt)

        # 验证返回结果结构
        if isinstance(result, dict):
            suggested_sentence = result.get("suggested_sentence", "待定")
            reasoning = result.get("reasoning", "未提供理由")

            # 验证必需字段存在
            if not suggested_sentence or not reasoning:
                logger.warning(
                    "量刑建议缺少必需字段: suggested_sentence={}, reasoning={}",
                    suggested_sentence,
                    reasoning,
                )
                return SentencingSuggestion(
                    suggested_sentence="待定",
                    reasoning="LLM 返回结果缺少必需字段",
                    error=True,
                    raw_response=json.dumps(result, ensure_ascii=False),
                )

            return SentencingSuggestion(
                suggested_sentence=str(suggested_sentence),
                reasoning=str(reasoning),
                error=False,
            )

        # LLM 返回非 dict 类型
        logger.warning("LLM 返回非预期的类型: {}", type(result).__name__)
        return SentencingSuggestion(
            suggested_sentence="待定",
            reasoning="LLM 返回格式错误",
            error=True,
            raw_response=str(result),
        )

    except json.JSONDecodeError as e:
        logger.error("量刑建议 JSON 解析失败: {}", e)
        return SentencingSuggestion(
            suggested_sentence="待定",
            reasoning=f"JSON 解析失败: {e}",
            error=True,
        )

    except Exception as e:  # noqa: BLE001
        logger.error("获取量刑建议失败: {}", e)
        return SentencingSuggestion(
            suggested_sentence="待定",
            reasoning=f"分析失败: {e}",
            error=True,
        )
