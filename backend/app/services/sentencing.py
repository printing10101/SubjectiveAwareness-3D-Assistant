"""量刑建议服务模块.

调用 LLM 根据分析结果和法律规则生成量刑建议。
"""

# 导入模块: json
import json
# 导入模块: from dataclasses
from dataclasses import dataclass

# 导入模块: from loguru
from loguru import logger

# 导入模块: from app.services.ollama_client
from app.services.ollama_client import get_client
# 导入模块: from app.services.prompts
from app.services.prompts import SENTENCING_PROMPT
# 导入模块: from app.types.analysis
from app.types.analysis import AnalysisResult


# 应用装饰器: dataclass
@dataclass
# 定义 SentencingSuggestion 类
class SentencingSuggestion:
    """量刑建议结果."""
    suggested_sentence: str
    reasoning: str
    error: bool = False  # 标记是否为错误降级结果
    raw_response: str | None = None  # 原始响应（仅错误时有值）


async def get_sentencing_suggestion(
    # 函数 get_sentencing_suggestion 的初始化逻辑
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
        # 异步等待操作完成
        >>> result = await get_sentencing_suggestion({"crime": "theft"})
        >>> if result.error:
        >>>     print("分析失败，使用降级结果")
        >>> else:
        >>>     print(f"建议刑期: {result.suggested_sentence}")
    """
    # 条件判断：处理业务逻辑
    if legal_rules:
        rules_text: str = "\n".join([str(r) for r in legal_rules])
    # 其他情况的默认处理
    else:
        # 初始化变量 rules_text
        rules_text = "无"

    prompt: str = SENTENCING_PROMPT.format(
        # 初始化变量 analysis_result
        analysis_result=json.dumps(analysis_result, ensure_ascii=False),
        # 初始化变量 legal_rules
        legal_rules=rules_text,
    )

    # 尝试执行可能抛出异常的代码
    try:
        # 初始化变量 client
        client = get_client()
        # 初始化变量 result
        result = await client.generate_json(prompt)

        # 验证返回结果结构
        if isinstance(result, dict):
            # 初始化变量 suggested_sentence
            suggested_sentence = result.get("suggested_sentence", "待定")
            # 初始化变量 reasoning
            reasoning = result.get("reasoning", "未提供理由")

            # 验证必需字段存在
            if not suggested_sentence or not reasoning:
                # 记录日志信息
                logger.warning(
                    "量刑建议缺少必需字段: suggested_sentence={}, reasoning={}",
                    suggested_sentence,
                    reasoning,
                )
                # 返回处理结果
                return SentencingSuggestion(
                    # 初始化变量 suggested_sentence
                    suggested_sentence="待定",
                    # 初始化变量 reasoning
                    reasoning="LLM 返回结果缺少必需字段",
                    # 初始化变量 error
                    error=True,
                    # 初始化变量 raw_response
                    raw_response=json.dumps(result, ensure_ascii=False),
                )

            # 返回处理结果
            return SentencingSuggestion(
                # 初始化变量 suggested_sentence
                suggested_sentence=str(suggested_sentence),
                # 初始化变量 reasoning
                reasoning=str(reasoning),
                # 初始化变量 error
                error=False,
            )

        # LLM 返回非 dict 类型
        logger.warning("LLM 返回非预期的类型: {}", type(result).__name__)
        # 返回处理结果
        return SentencingSuggestion(
            # 初始化变量 suggested_sentence
            suggested_sentence="待定",
            # 初始化变量 reasoning
            reasoning="LLM 返回格式错误",
            # 初始化变量 error
            error=True,
            # 初始化变量 raw_response
            raw_response=str(result),
        )

    # 捕获并处理异常
    except json.JSONDecodeError as e:
        # 记录日志信息
        logger.error("量刑建议 JSON 解析失败: {}", e)
        # 返回处理结果
        return SentencingSuggestion(
            # 初始化变量 suggested_sentence
            suggested_sentence="待定",
            # 初始化变量 reasoning
            reasoning=f"JSON 解析失败: {e}",
            # 初始化变量 error
            error=True,
        )

    # 捕获并处理异常
    except Exception as e:  # noqa: BLE001
        logger.error("获取量刑建议失败: {}", e)
        # 返回处理结果
        return SentencingSuggestion(
            # 初始化变量 suggested_sentence
            suggested_sentence="待定",
            # 初始化变量 reasoning
            reasoning=f"分析失败: {e}",
            # 初始化变量 error
            error=True,
        )
