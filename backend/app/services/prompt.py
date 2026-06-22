"""提示词服务模块.

整合提示词常量定义和提示词管理器功能：
- 提示词常量：V1/V2 协议的硬编码提示词模板
- 提示词管理器：从 JSON 文件加载提示词、运行时热重载、使用统计追踪

V1 协议 (默认 / 向后兼容) — 输出 0-10 评分。
V2 协议 — 输出"三维度 × 四档 (T1-T4)" + 规则/标签/冲突整合。

V2 与 V1 同时导出，调用方根据 ``version`` 字段选择使用。
"""

from __future__ import annotations

import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger


# ===========================================================================
# 提示词管理器 - 从 JSON 文件加载提示词
# ===========================================================================


DEFAULT_PROMPTS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "prompts.json",
)


class PromptManager:
    """提示词管理器.

    从JSON配置文件加载系统提示词和维度提示词，
    支持运行时热重载和使用统计追踪。

    Attributes:
        _prompts: 当前加载的提示词字典
        _stats: 各提示词的使用统计信息
        _lock: 线程安全锁，保护提示词加载和统计更新
        _file_path: 提示词JSON文件的路径

    Example:
        >>> manager = PromptManager()
        >>> system_prompt = manager.get_system_prompt()
        >>> dim1 = manager.get_dimension_prompt("dimension1")
        >>> stats = manager.get_stats()
    """

    def __init__(self, prompts_file: str | None = None) -> None:
        """初始化提示词管理器.

        Args:
            prompts_file: 提示词JSON文件路径，默认使用项目内置配置

        Raises:
            FileNotFoundError: 提示词文件不存在且无法使用默认路径
        """
        self._prompts: dict[str, Any] = {}
        self._stats: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._file_path = prompts_file or DEFAULT_PROMPTS_FILE
        self._load_prompts()

    def _load_prompts(self) -> None:
        """从JSON文件加载提示词到内存.

        内部方法，不直接暴露给外部调用。
        加载过程包含完整的错误处理：
        - 文件不存在 → 记录错误并初始化为空字典
        - JSON格式错误 → 记录错误并初始化为空字典
        - 结构验证失败 → 记录警告日志

        Raises:
            不会向外抛出异常，所有异常在内部捕获并记录日志
        """
        try:
            file_path = Path(self._file_path)
            if not file_path.exists():
                logger.error(
                    "提示词文件不存在: {}，请检查配置路径",
                    self._file_path,
                )
                self._prompts = {}
                return

            if file_path.stat().st_size == 0:
                logger.error(
                    "提示词文件为空: {}",
                    self._file_path,
                )
                self._prompts = {}
                return

            with open(file_path, encoding="utf-8") as f:
                self._prompts = json.load(f)

            self._validate_prompts_structure()
            logger.info(
                "提示词加载成功 | 文件: {} | meta版本: {}",
                self._file_path,
                self._prompts.get("meta", {}).get("version", "未知"),
            )
        except json.JSONDecodeError as e:
            logger.error("提示词JSON解析失败: {} | 错误: {}", self._file_path, e)
            self._prompts = {}
        except PermissionError as e:
            logger.error("提示词文件权限不足: {} | 错误: {}", self._file_path, e)
            self._prompts = {}
        except OSError as e:
            logger.error("读取提示词文件失败: {} | 错误: {}", self._file_path, e)
            self._prompts = {}
        except Exception as e:  # noqa: BLE001
            logger.error(
                "加载提示词时发生未预期异常: {} | 错误: {}",
                self._file_path,
                e,
            )
            self._prompts = {}

    def _validate_prompts_structure(self) -> None:
        """验证提示词JSON结构的完整性.

        检查必需的顶层字段是否存在，记录缺少的字段。
        仅发出警告，不会中断加载流程。
        """
        required_top = ["meta", "system", "dimensions"]
        missing = [k for k in required_top if k not in self._prompts]
        if missing:
            logger.warning("提示词结构缺少顶层字段: {}", missing)

        if "system" in self._prompts:
            system = self._prompts["system"]
            if not isinstance(system, dict) or "content" not in system:
                logger.warning("system提示词缺少content字段")

        if "dimensions" in self._prompts:
            dims = self._prompts["dimensions"]
            if not isinstance(dims, dict):
                logger.warning("dimensions字段不是有效的字典对象")
            else:
                for dim_name in list(dims.keys()):
                    if "content" not in dims[dim_name]:
                        logger.warning("维度 {} 缺少content字段", dim_name)

    def reload_prompts(self) -> bool:
        """运行时重载提示词，无需重启应用.

        线程安全的重载操作，使用锁保护整个重载过程。
        重载前会保留旧提示词副本，若新提示词加载失败则回滚。

        Returns:
            True表示重载成功，False表示重载失败（已回滚到旧版本）

        Example:
            >>> manager = PromptManager()
            >>> success = manager.reload_prompts()
            >>> if success:
            ...     print("提示词已更新")
        """
        old_prompts = self._prompts

        with self._lock:
            logger.info("开始重载提示词 | 文件: {}", self._file_path)
            self._load_prompts()

            if not self._prompts:
                logger.warning(
                    "新提示词加载为空，回滚到旧版本 | 文件: {}",
                    self._file_path,
                )
                self._prompts = old_prompts
                return False

            logger.info("提示词重载成功 | 文件: {}", self._file_path)
            return True

    def _record_usage(self, key: str) -> None:
        """记录提示词使用信息.

        线程安全地更新指定提示词的调用次数和最近调用时间。

        Args:
            key: 提示词标识键，格式为 "category:name"
        """
        with self._lock:
            now = datetime.now(UTC).isoformat()
            if key not in self._stats:
                self._stats[key] = {
                    "call_count": 0,
                    "first_called_at": now,
                }
            self._stats[key]["call_count"] += 1
            self._stats[key]["last_called_at"] = now

    def get_system_prompt(
        self,
        default: str | None = None,
    ) -> str:
        """获取系统提示词.

        Args:
            default: 当系统提示词不存在时返回的默认值。
                     未提供时抛出ValueError。

        Returns:
            系统提示词文本

        Raises:
            ValueError: 系统提示词不存在且未提供默认值

        Example:
            >>> manager = PromptManager()
            >>> prompt = manager.get_system_prompt()
            >>> prompt = manager.get_system_prompt(default="默认提示词")
        """
        self._record_usage("system")
        try:
            return self._prompts["system"]["content"]
        except (KeyError, TypeError):
            if default is not None:
                logger.warning("系统提示词不存在，使用默认值")
                return default
            logger.error("系统提示词不存在且未提供默认值")
            msg = "系统提示词不存在，请检查 prompts.json 中 system.content 字段"
            raise ValueError(msg) from None

    def get_dimension_prompt(
        self,
        dimension: str = "dimension1",
        default: str | None = None,
    ) -> str:
        """获取指定维度的分析提示词.

        Args:
            dimension: 维度标识，可选 dimension1/dimension2/dimension3，
                       默认 dimension1
            default: 当维度提示词不存在时返回的默认值。
                     未提供时抛出ValueError。

        Returns:
            维度提示词文本

        Raises:
            ValueError: 维度值不在有效范围内（dimension1~3）
            ValueError: 维度提示词不存在且未提供默认值

        Example:
            >>> manager = PromptManager()
            >>> dim1 = manager.get_dimension_prompt("dimension1")
            >>> dim2 = manager.get_dimension_prompt("dimension2")
            >>> dim3 = manager.get_dimension_prompt("dimension3")
        """
        valid_dimensions = {"dimension1", "dimension2", "dimension3"}
        if dimension not in valid_dimensions:
            msg = (
                f"无效的维度参数: {dimension}，"
                f"有效值为: {', '.join(sorted(valid_dimensions))}"
            )
            raise ValueError(msg)

        self._record_usage(f"dimension:{dimension}")
        try:
            return self._prompts["dimensions"][dimension]["content"]
        except (KeyError, TypeError):
            if default is not None:
                logger.warning(
                    "维度提示词 {} 不存在，使用默认值",
                    dimension,
                )
                return default
            logger.error("维度提示词 {} 不存在且未提供默认值", dimension)
            msg = (
                f"维度提示词 {dimension} 不存在，"
                f"请检查 prompts.json 中 dimensions.{dimension}.content 字段"
            )
            raise ValueError(msg) from None

    def get_specialized_prompt(
        self,
        name: str,
        default: str | None = None,
    ) -> str:
        """获取专用提示词（如相似案例推荐、量刑建议等）.

        Args:
            name: 专用提示词名称，如 similar_cases、sentencing
            default: 当专用提示词不存在时返回的默认值。
                     未提供时抛出ValueError。

        Returns:
            专用提示词文本

        Raises:
            ValueError: 专用提示词不存在且未提供默认值

        Example:
            >>> manager = PromptManager()
            >>> prompt = manager.get_specialized_prompt("sentencing")
            >>> prompt = manager.get_specialized_prompt("similar_cases")
        """
        if not name or not isinstance(name, str):
            msg = "name参数必须是非空字符串"
            raise ValueError(msg)

        self._record_usage(f"specialized:{name}")
        try:
            return self._prompts["specialized"][name]["content"]
        except (KeyError, TypeError):
            if default is not None:
                logger.warning(
                    "专用提示词 {} 不存在，使用默认值",
                    name,
                )
                return default
            logger.error("专用提示词 {} 不存在且未提供默认值", name)
            msg = (
                f"专用提示词 {name} 不存在，"
                f"请检查 prompts.json 中 specialized.{name}.content 字段"
            )
            raise ValueError(msg) from None

    def get_stats(self) -> dict[str, dict[str, Any]]:
        """获取提示词使用统计信息.

        返回每个提示词的调用次数、首次调用时间和最近调用时间的快照。

        Returns:
            统计信息字典，键为提示词标识，值为包含调用统计的字典

        Example:
            >>> manager = PromptManager()
            >>> stats = manager.get_stats()
            >>> print(stats["system"]["call_count"])
        """
        with self._lock:
            return dict(self._stats)

    def get_prompt_info(self) -> dict[str, Any]:
        """获取提示词元信息.

        返回提示词配置的元信息，包括版本号、描述和更新时间。

        Returns:
            元信息字典，包含 version、description、updated_at 等字段

        Example:
            >>> manager = PromptManager()
            >>> info = manager.get_prompt_info()
            >>> print(info["version"])
        """
        return dict(self._prompts.get("meta", {}))

    def get_available_dimensions(self) -> list[str]:
        """获取所有可用的维度列表.

        Returns:
            维度名称列表

        Example:
            >>> manager = PromptManager()
            >>> dims = manager.get_available_dimensions()
            >>> print(dims)  # ['dimension1', 'dimension2', 'dimension3']
        """
        dims = self._prompts.get("dimensions", {})
        if isinstance(dims, dict):
            return list(dims.keys())
        return []

    def get_available_specialized(self) -> list[str]:
        """获取所有可用的专用提示词列表.

        Returns:
            专用提示词名称列表

        Example:
            >>> manager = PromptManager()
            >>> names = manager.get_available_specialized()
        """
        specialized = self._prompts.get("specialized", {})
        if isinstance(specialized, dict):
            return list(specialized.keys())
        return []

    def is_loaded(self) -> bool:
        """检查提示词是否已成功加载.

        Returns:
            True表示提示词已加载，False表示未加载或加载失败

        Example:
            >>> manager = PromptManager()
            >>> if manager.is_loaded():
            ...     print("提示词已就绪")
        """
        return bool(self._prompts)


def get_prompt_manager(
    prompts_file: str | None = None,
) -> PromptManager:
    """获取PromptManager单例实例.

    创建或返回全局唯一的PromptManager实例，
    确保整个应用中提示词配置的一致性和统计数据的完整性。

    Args:
        prompts_file: 可选的提示词文件路径，仅在首次创建时生效

    Returns:
        全局唯一的PromptManager实例

    Example:
        >>> manager = get_prompt_manager()
    """
    return PromptManager(prompts_file)


# ===========================================================================
# 提示词常量 - V1 协议（保留 0-10 评分，向后兼容）
# ===========================================================================


ANALYSIS_SYSTEM_PROMPT = """你是一位专业的法律案件分析助手，精通刑事案件的要件分析与法律适用。

{legal_knowledge}
【重要】以上相关知识仅供参考。如果相关知识与你对案件的分析有冲突，以案件事实为准，但请在推理中说明你的判断依据。

【重要提示】在给出最终 JSON 结论之前，你必须进行完整的逐步推理分析。所有推理过程必须使用 <think/> 标签包裹，不得省略关键分析步骤。

推理步骤要求：

第一步：事实提取 — 从案件描述中系统提取所有关键事实要素，包括时间、地点、行为、主体、结果等，确保不遗漏任何具有法律意义的事实细节。

第二步：要件匹配 — 将提取的事实与相关法律条文的构成要件进行逐一对照分析，明确符合与不相符的要件，评估各要件的满足程度。

第三步：证据评估 — 评估案件证据的可靠性、完整性及证明力，分析证据链的优势与不足，指出关键证据的证明价值。

注意：前三步（事实提取、要件匹配、证据评估）是对案件事实和模式的系统性分析，其结论将为后续矛盾识别提供基础。

第四步：矛盾识别 — 基于前三步的事实和模式分析结果，识别案件事实、证据或法律适用中可能存在的矛盾点、模糊点或争议点，分析其对案件定性的影响程度。

第五步：法律适用 — 基于案件性质，准确引用相关法律法规、司法解释及指导案例，说明法律依据的适用性。

第六步：综合判断 — 综合前述分析，形成最终的法律分析结论，输出三维度评分及综合建议。

推理完成后，请严格按照以下 JSON 格式输出最终结论：
{
  "subjective_knowledge": "主观明知程度",
  "sentence": "量刑建议",
  "court": "建议法院",
  "ground_truth_analysis": {
    "dimension1": {
      "score": 数值(0-10),
      "reasoning": "分析理由",
      "key_indicators": ["关键指标"]
    },
    "dimension2": {
      "score": 数值(0-10),
      "reasoning": "分析理由",
      "pattern_match": "模式匹配结果"
    },
    "dimension3": {
      "score": 数值(0-10),
      "reasoning": "分析理由",
      "contradictions": ["矛盾点"]
    }
  }
}
"""

DIMENSION1_PROMPT = """{legal_knowledge}

请分析以下案件的事实知识维度：
1. 审查案件事实与法律要件的匹配度
2. 分析主观明知程度
3. 评估证据链条完整性

推理步骤：
第一步：关键事实提取 — 系统提取案件中的时间、地点、行为主体、行为方式、结果等所有关键事实要素，形成完整的事实清单。
第二步：要件逐一匹配 — 将提取的每个关键事实与相关法律条文的构成要件进行逐一对照，标注符合与不相符的要件。
第三步：证据链评估 — 评估现有证据能否支撑每个要件的事实认定，指出证据链的优势与不足。
第四步：综合判断 — 综合前述分析，给出事实维度的评分和关键指标。

返回JSON格式：
{
  "score": 数值(0-10),
  "reasoning": "详细分析理由",
  "key_indicators": ["关键指标列表"],
  "sentence_suggestion": "量刑建议"
}
"""

DIMENSION2_PROMPT = """{legal_knowledge}

请分析以下案件的模式匹配维度：
1. 匹配典型犯罪模式
2. 分析行为异常程度
3. 评估犯罪手法特征

推理步骤：
第一步：行为特征描述 — 从案件描述中提取犯罪嫌疑人的具体行为方式、手段、对象、结果等特征要素。
第二步：典型模式对比 — 将提取的行为特征与典型犯罪模式（如诈骗、盗窃、抢劫等）的结构性特征进行逐一对比。
第三步：异常程度评估 — 分析行为模式与典型模式的偏离程度，识别异常或特殊的犯罪手法特征。
第四步：综合判断 — 综合前述分析，给出模式匹配维度的评分和匹配结果。

返回JSON格式：
{
  "score": 数值(0-10),
  "reasoning": "详细分析理由",
  "pattern_match": "模式匹配结果"
}
"""

DIMENSION3_PROMPT = """请分析以下案件的矛盾分析维度：

{prior_analysis}

{legal_knowledge}

案件原文：
{case_text}

请基于上述前置分析结果，重点分析：
1. 识别嫌疑人辩解与证据的矛盾
2. 分析前置分析中可能存在的逻辑不一致之处
3. 评估辩解的可信度

推理步骤：
第一步：各方陈述提取 — 系统梳理嫌疑人辩解、被害人陈述、证人证言等各方叙述中的核心主张和关键事实。
第二步：逐对比较分析 — 将各方陈述进行两两对比，标注一致点和矛盾点，分析矛盾的性质和严重程度。
第三步：可信度评估 — 结合前置分析发现和案件证据，评估各方陈述的可信度，分析辩解的逻辑自洽性。
第四步：综合判断 — 综合前置分析和前述分析，给出矛盾分析维度的评分和具体矛盾点。

返回JSON格式：
{{
  "score": 数值(0-10),
  "reasoning": "详细分析理由",
  "contradictions": ["矛盾点列表"]
}}
"""


# ===========================================================================
# 提示词常量 - V2 协议（三维度 × 四档 T1-T4）
# ===========================================================================


#: 档级语义说明
TIER_LEGEND_V2 = """档级说明（必须严格按此判断，不得自创档级名）：
- T1  一档（情节较轻）：   三年以下有期徒刑、拘役或者管制，并处或者单处罚金
- T2  二档（情节一般）：   三年以下有期徒刑，并处罚金
- T3  三档（情节严重）：   三年以上七年以下有期徒刑，并处罚金
- T4  四档（情节特别严重）：七年以上有期徒刑，并处罚金或者没收财产
"""


#: V2 维1 prompt — 事实知识审查（构成要件 + 主观明知）
V2_DIMENSION1_PROMPT = """你是一位专业的帮信罪案件分析助手，正在审查案件的事实知识维度。
请严格按以下 5 步推理，每步用 1-2 句话清晰说明，最后输出 ``tier`` 字段。

""" + TIER_LEGEND_V2 + """

第一步：事实清单 — 系统提取案件中的时间、地点、行为主体、行为方式、结果等所有关键事实要素。
第二步：主观明知 — 判断嫌疑人是否"明知他人利用信息网络实施犯罪"；参考已抽取的标签与命中的规则。
第三步：客观行为 — 评估"提供互联网接入/服务器托管/网络存储/通讯传输/广告推广/支付结算"等帮助行为的有无与程度。
第四步：要件齐备 — 将上述事实对照刑法第 287 条之二的构成要件逐一匹配，给出齐备度评价。
第五步：档级判定 — 综合前三步的齐备度与严重程度，输出唯一 ``tier`` 档级（只能 T1/T2/T3/T4）。

【已抽取的事实标签】
{matched_tags}

【已命中的相关规则】
{triggered_rules}

{legal_knowledge}

案件原文：
{case_text}

【输出格式 — 严格 JSON】
{{
  "tier": "T1|T2|T3|T4",
  "reasoning": "上述 5 步推理的中文完整文本（不少于 200 字）",
  "key_indicators": ["关键事实1", "关键事实2", "..."],
  "triggered_rules": ["命中的规则ID列表，可为空"]
}}
"""


#: V2 维2 prompt — 模式匹配（情节严重程度评估）
V2_DIMENSION2_PROMPT = """你是一位专业的帮信罪案件分析助手，正在分析案件的模式匹配维度。
请严格按以下 5 步推理，每步用 1-2 句话清晰说明，最后输出 ``tier`` 字段。

""" + TIER_LEGEND_V2 + """

第一步：行为模式描述 — 描述嫌疑人具体的行为方式（开卡/提供支付接口/技术维护/广告推广等）。
第二步：典型模式对比 — 与帮信罪典型犯罪模式（大量开卡、跨地区、跨时段、配合转移资金等）对比。
第三步：数额/规模 — 评估涉案金额、被害人数量、流水规模等量化指标所对应的情节档级。
第四步：从重/从轻情节 — 列举可能的从重或从轻情节（自首、坦白、立功、累犯、未成年人、认罪认罚等）。
第五步：档级判定 — 综合前述分析，输出唯一 ``tier`` 档级（只能 T1/T2/T3/T4）。

【已抽取的事实标签】
{matched_tags}

【已命中的相关规则】
{triggered_rules}

{legal_knowledge}

案件原文：
{case_text}

【输出格式 — 严格 JSON】
{{
  "tier": "T1|T2|T3|T4",
  "reasoning": "上述 5 步推理的中文完整文本（不少于 200 字）",
  "pattern_match": "与典型模式的对比结论（不少于 80 字）",
  "triggered_rules": ["命中的规则ID列表，可为空"]
}}
"""


#: V2 维3 prompt — 矛盾分析（嫌疑人辩解 vs 证据）
V2_DIMENSION3_PROMPT = """你是一位专业的帮信罪案件分析助手，正在分析案件的矛盾维度。
请严格按以下 5 步推理，每步用 1-2 句话清晰说明，最后输出 ``tier`` 字段。

""" + TIER_LEGEND_V2 + """

第一步：各方陈述提取 — 嫌疑人辩解、被害人陈述、证人证言等各方的核心主张。
第二步：两两对比 — 将各方陈述两两对比，标注一致点与矛盾点。
第三步：可信度评估 — 结合前置维度 1（事实审查）与维度 2（模式匹配）的结论，评估辩解可信度。
第四步：抗辩影响 — 评估嫌疑人辩解对档级判定的影响方向（辩解有效→档级降低；辩解无效→档级维持或上升）。
第五步：档级判定 — 基于矛盾分析的最终抗辩强度，输出唯一 ``tier`` 档级（只能 T1/T2/T3/T4）。

【前置分析（维度 1 事实审查）】
{prior_dim1}

【前置分析（维度 2 模式匹配）】
{prior_dim2}

【已抽取的事实标签】
{matched_tags}

【已命中的相关规则】
{triggered_rules}

{legal_knowledge}

案件原文：
{case_text}

【输出格式 — 严格 JSON】
{{
  "tier": "T1|T2|T3|T4",
  "reasoning": "上述 5 步推理的中文完整文本（不少于 200 字）",
  "contradictions": ["具体矛盾点1", "具体矛盾点2", "..."],
  "triggered_rules": ["命中的规则ID列表，可为空"]
}}
"""


# ===========================================================================
# 提示词常量 - V2 协议（标签抽取 / 规则注入 prompt）
# ===========================================================================


#: 标签抽取 prompt — 从案件文本抽取最相关的若干 tag
TAG_EXTRACTION_PROMPT = """你是一位专业的帮信罪案件标签抽取助手。
请从以下 40 个候选标签中，挑选**与案件最相关**的 5-12 个标签。

【候选标签列表（tag_id = 名称 = 含义）】
{tag_candidates}

【匹配要求】
1. 只输出**案件原文确实支持**的标签，不要强行匹配无关项。
2. 至少 1 个客观行为类标签，至少 1 个认知线索类标签（如适用）。
3. 互斥标签只能选其一（同一互斥组中选 confidence 最高者）。
4. 案件文本简短或证据不足时，宁可少选不要凑数。

【输出格式 — 严格 JSON 数组】
{{
  "selected_tags": [
    {{
      "tag_id": "F001",
      "name": "标签名",
      "category": "客观行为/认知线索/辩解模式/情节",
      "matched_text": "案件原文中支持该标签的片段",
      "confidence": 0.85
    }}
  ]
}}
"""


#: 规则注入 prompt — 把 56 条规则按相关度排序，取 top-N 注入
RULE_INJECTION_PROMPT = """你是一位专业的帮信罪案件规则匹配助手。
请从以下 56 条候选规则中，挑选**与案件最相关**的 5-10 条规则。

【候选规则列表（rule_id = 名称 = 条件 + 结论）】
{rule_candidates}

【匹配要求】
1. 规则应当与案件事实**确实匹配**（满足 conditions 字段中描述的触发条件）。
2. 优先匹配 weight ≥ 0.7 的高权重规则。
3. 优先匹配 applicable_scenarios 与案件行为模式一致的规则。
4. 互斥规则（conflicting_rules 字段）不同时选择。
5. 5-10 条为宜，证据不足宁可少选。

【输出格式 — 严格 JSON 数组】
{{
  "matched_rules": [
    {{
      "rule_id": "R005",
      "name": "规则名",
      "match_reason": "为何本案件匹配该规则（引用案件事实，1-2 句）",
      "confidence": 0.85
    }}
  ]
}}
"""


#: 结论生成 prompt — 三段论：事实→规则→结论
CONCLUSION_GENERATION_PROMPT = """你是一位专业的帮信罪案件结论生成助手。
请使用"三段论"结构（**事实认定** → **法律适用** → **结论**）生成最终结论。

【案件事实】
{case_text}

【事实标签命中】
{matched_tags}

【触发的法律规则】
{triggered_rules}

【档级组合结论】
- 最终档级：{final_tier}（{final_label}）
- 建议量刑区间：{sentence_band}
- 维度档级：事实审查 {dim1_tier} | 模式匹配 {dim2_tier} | 矛盾分析 {dim3_tier}
- 检测到的冲突：{conflicts}

【生成要求】
1. 必须按"事实认定 → 法律适用 → 结论"三段结构组织文本。
2. 引用具体法条（刑法第 287 条之二、帮信解释等）与本案件命中的规则编号。
3. 事实部分简明扼要（200 字内），不要复述案件全文。
4. 法律适用部分应包含：触发的规则、对应法条、为什么匹配该档级。
5. 结论部分明确说明档级与量刑区间，并强调"辅助参考"属性。
6. 总长度 400-800 字，避免堆砌。

【输出格式 — 严格文本（非 JSON）】
直接输出三段论结论文本，不要包裹在 JSON 或 Markdown 中。
"""


# ===========================================================================
# 提示词常量 - V1 协议（其他辅助 prompt）
# ===========================================================================


SIMILAR_CASES_PROMPT = """请根据以下案件描述，推荐3个相似的案例：

案件：{case_text}

返回JSON格式：
{{
  "similar_cases": [
    {{
      "case_id": "案例ID",
      "similarity": 相似度(0-1),
      "title": "案例标题",
      "summary": "简要摘要"
    }}
  ]
}}
"""

SENTENCING_PROMPT = """请根据以下案件分析结果，给出量刑建议：

案件分析：
{analysis_result}

参考法律规则：
{legal_rules}

返回JSON格式：
{{
  "suggested_sentence": "量刑建议",
  "reasoning": "量刑理由",
  "legal_basis": ["法律依据"],
  "aggravating_factors": ["加重情节"],
  "mitigating_factors": ["从轻情节"]
}}
"""

EXTRACT_METADATA_PROMPT = """你是一个专业的知识管理助手。请从输入的文档或案件文本中提取结构化元数据信息。

输入内容：
{document_text}

提取要求：
1. 标题：准确反映文档核心内容，简洁明了，不超过20字
2. 摘要：200字以内，包含关键信息和主要结论，准确概括核心内容
3. 关键概念：提取3-5个文档中出现的核心术语和重要概念
4. 建议标签：提取5个以内具有代表性和检索价值的描述性标签
5. 建议分类：判断最匹配的知识分类类别

请严格遵循以下JSON格式返回结果，不要输出任何额外内容：
{{
  "title": "文档标题（简洁明了，不超过20字）",
  "summary": "文档摘要（200字以内，准确概括核心内容）",
  "key_concepts": ["关键概念1", "关键概念2", "关键概念3"],
  "suggested_tags": ["标签1", "标签2"],
  "suggested_category": "最匹配的知识分类"
}}

质量要求：
- 标题需准确反映文档核心内容，避免空泛描述
- 摘要需覆盖关键信息和主要结论，保持原文逻辑结构
- 关键概念需使用准确的术语表达，具有代表性
- 标签需具有检索价值，避免过于宽泛或重复
- 分类需符合法律知识体系分类标准，确保分类准确性
"""

GENERATE_SUMMARY_PROMPT = """你是一个专业的知识摘要生成助手。请为以下知识条目正文生成简洁准确的摘要。

知识条目正文：
{entry_content}

摘要要求：
1. 突出核心观点和关键信息，确保读者能快速把握内容主旨
2. 保持原文的逻辑结构，按原文的论述层次进行概括
3. 语言精炼，避免冗余，不使用填充词和套话
4. 准确反映原文含义和立场，不曲解或遗漏重要信息
5. 不添加原文未包含的信息或个人观点，保持客观中立

请直接返回纯文本摘要，不超过200字。不要包含任何格式标记或额外说明。
"""

EXTRACT_KEY_CONCEPTS_PROMPT = """你是一个专业的知识概念提取助手。请从以下知识条目正文中提取关键概念及其相关信息。

知识条目正文：
{entry_content}

提取要求：
1. 重点识别法律概念、分析框架和关键专业术语
2. 每个概念的名称需使用准确的术语表达
3. 对每个概念提供100字以内的清晰描述，解释其含义和在条目中的角色
4. 基于概念在条目中的实际重要程度，给出"高/中/低"重要性评级
5. 确保提取3-5个最核心的概念，按重要性从高到低排列

请严格遵循以下JSON格式返回结果，不要输出任何额外内容：
{{
  "concepts": [
    {{
      "name": "概念名称（准确的术语表达）",
      "description": "概念描述（100字以内，清晰解释概念含义）",
      "importance": "高"
    }}
  ]
}}

质量要求：
- 概念名称需使用领域内公认的标准术语
- 描述需准确完整，能够独立解释该概念的核心含义
- 重要性评级需客观反映概念在知识条目中的实际重要程度
- 避免提取过于泛化或与条目主题关联度低的概念
"""

SUGGEST_RELATIONS_PROMPT = """你是一个专业的知识关联分析助手。请分析当前知识条目与现有知识库中其他条目的关联关系。

当前知识条目摘要：
{entry_summary}

现有知识库条目列表（每个条目包含标题和摘要）：
{existing_entries}

分析要求：
1. 比较当前条目与每个现有条目的内容和主题
2. 识别条目间的逻辑关系，包括但不限于：
   - references：当前条目引用了某现有条目的内容
   - contradicts：当前条目与某现有条目存在观点冲突
   - extends：当前条目扩展或深化了某现有条目的内容
   - supports：当前条目支持或佐证了某现有条目的观点
   - similar：当前条目与某现有条目主题和观点高度相似
3. 对每个识别到的关联关系提供100字以内的具体理由
4. 优先识别强关联关系，最多返回5个最相关的关联关系

请严格遵循以下JSON格式返回结果，不要输出任何额外内容：
{{
  "relations": [
    {{
      "target_title": "关联条目标题",
      "relation_type": "references",
      "reason": "关联理由（100字以内，说明关联关系的具体依据）"
    }}
  ]
}}

质量要求：
- 关联关系需基于内容的具体分析，而非表面相似度
- 关联理由需具体明确，指出两篇条目的具体关联点
- 仅返回确实存在关联的条目，不编造不存在的关联
- 关联类型需使用标准术语，确保一致性
"""

SUGGEST_RELATED_ENTRIES_PROMPT = """你是一个专业的知识推荐助手。请分析当前知识条目，从现有的知识库中推荐最相关的内容条目。

当前知识条目详情：
- 标题：{entry_title}
- 分类：{entry_category}
- 摘要：{entry_summary}
- 内容片段：{entry_content_snippet}

现有知识库条目列表（每个条目包含ID、标题和摘要，你必须从中选择）：
{existing_entries}

推荐要求：
1. 基于当前条目的主题、内容和分类，从上述列表中推荐最相关的知识条目
2. 关系类型从以下选择：references（引用）、extends（扩展）、similar（相似）、supports（支持）
3. 对每个推荐条目给出0.0-1.0的相似度评分，综合评估主题、内容和分类的相关性
4. 提供100字以内的推荐理由，说明推荐的具体依据
5. 最多推荐{top_k}个最相关的条目，按相似度从高到低排列
6. 推荐的条目ID必须来自上述列表中的条目，严禁编造不存在的ID

请严格遵循以下JSON格式返回结果，不要输出任何额外内容：
{{
  "related_entries": [
    {{
      "entry_id": 条目ID（整数）,
      "relation_type": "similar",
      "similarity": 0.85,
      "reason": "推荐理由（100字以内）"
    }}
  ]
}}

质量要求：
- 推荐的条目必须真实存在于提供的列表中
- 相似度评分需客观反映内容相关性，避免随意给分
- 推荐理由需具体明确，指出两篇条目的具体关联点
"""

KNOWLEDGE_QA_PROMPT = """你是一个专业的知识问答助手。请基于提供的相关知识条目内容回答用户问题。

用户问题：
{user_question}

相关知识条目内容：
{relevant_entries}

回答要求：
1. 严格基于提供的知识库内容回答，不编造或推测信息
2. 回答需逻辑清晰、准确完整，确保充分解答用户疑问
3. 所有引用内容需明确标注来源条目，格式为：【来源：条目标题】
4. 当多个条目内容存在冲突时，需明确指出冲突点并分别说明各方观点
5. 回答长度根据问题复杂度适当调整，避免过度简化或冗长
6. 若提供的知识条目不足以回答问题，应明确指出信息缺失，不强行给出答案
7. 保持专业、中立的语言风格，不添加主观评论

请直接返回结构化的自然语言回答，包含明确的引用标注。不要输出JSON格式。
"""


# ===========================================================================
# 版本常量与导出列表
# ===========================================================================


PROMPTS_VERSION_V1: str = "1.0"
PROMPTS_VERSION_V2: str = "2.0"


__all__ = [
    # 提示词管理器
    "PromptManager",
    "get_prompt_manager",
    "DEFAULT_PROMPTS_FILE",
    # 版本常量
    "PROMPTS_VERSION_V1",
    "PROMPTS_VERSION_V2",
    # V1 协议提示词
    "ANALYSIS_SYSTEM_PROMPT",
    "DIMENSION1_PROMPT",
    "DIMENSION2_PROMPT",
    "DIMENSION3_PROMPT",
    "SIMILAR_CASES_PROMPT",
    "SENTENCING_PROMPT",
    "EXTRACT_METADATA_PROMPT",
    "GENERATE_SUMMARY_PROMPT",
    "EXTRACT_KEY_CONCEPTS_PROMPT",
    "SUGGEST_RELATIONS_PROMPT",
    "SUGGEST_RELATED_ENTRIES_PROMPT",
    "KNOWLEDGE_QA_PROMPT",
    # V2 协议提示词
    "TIER_LEGEND_V2",
    "V2_DIMENSION1_PROMPT",
    "V2_DIMENSION2_PROMPT",
    "V2_DIMENSION3_PROMPT",
    "TAG_EXTRACTION_PROMPT",
    "RULE_INJECTION_PROMPT",
    "CONCLUSION_GENERATION_PROMPT",
]
