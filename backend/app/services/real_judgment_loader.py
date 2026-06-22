"""真实判决书数据加载器.

负责解析 GZ 系列真实判决书 JSON 文件，将其标准化为统一的 Case 数据结构。
支持字段验证、类型检查和错误处理。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel, ConfigDict, field_validator

from app.config import AnalysisConfig
from app.models.case import CaseStatus


class RealJudgmentSchema(BaseModel):
    """真实判决书数据 Schema.

    定义从 GZ 系列 JSON 文件解析出的标准化数据结构。
    """

    model_config = ConfigDict(use_enum_values=True, validate_default=True)

    case_id: str
    court: str
    case_facts: str
    subjective_knowledge: str
    sentence: str
    reasoning: str
    dimension1_score: float
    dimension2_score: float
    dimension3_score: float
    dimension1_reasoning: str
    dimension2_reasoning: str
    dimension3_reasoning: str
    key_indicators: list[str]
    pattern_match: str
    contradictions: list[str]

    @field_validator("case_id")
    @classmethod
    def validate_case_id(cls, v: str) -> str:
        """验证案件 ID 格式."""
        if not v or not v.strip():
            msg = "case_id 不能为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        return v.strip()

    @field_validator("court")
    @classmethod
    def validate_court(cls, v: str) -> str:
        """验证法院名称."""
        if not v or not v.strip():
            msg = "court 不能为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        return v.strip()

    @field_validator("case_facts")
    @classmethod
    def validate_case_facts(cls, v: str) -> str:
        """验证案件事实文本."""
        if not v or not v.strip():
            msg ="case_facts 不能为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        if len(v.strip()) < AnalysisConfig.MIN_CASE_LENGTH:
            msg = f"case_facts 长度不能少于 {AnalysisConfig.MIN_CASE_LENGTH} 个字符"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        return v.strip()

    @field_validator("subjective_knowledge")
    @classmethod
    def validate_subjective_knowledge(cls, v: str) -> str:
        """验证主观明知认定."""
        if not v or not v.strip():
            msg = "subjective_knowledge 不能为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        return v.strip()

    @field_validator("sentence")
    @classmethod
    def validate_sentence(cls, v: str) -> str:
        """验证判决结果."""
        if not v or not v.strip():
            msg = "sentence 不能为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        return v.strip()

    @field_validator("reasoning")
    @classmethod
    def validate_reasoning(cls, v: str) -> str:
        """验证裁判理由."""
        if not v or not v.strip():
            msg = "reasoning 不能为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        return v.strip()

    @field_validator("dimension1_score", "dimension2_score", "dimension3_score")
    @classmethod
    def validate_dimension_score(cls, v: float) -> float:
        """验证维度评分."""
        if v < 0.0 or v > 10.0:
            msg = f"维度评分必须在 0-10 之间，当前值: {v}"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        return v


class RealJudgmentLoader:
    """真实判决书数据加载器.

    负责从 data/real_judgments/ 目录加载 GZ 系列 JSON 文件，
    解析并标准化为 Case 模型可接受的数据结构。
    """

    def __init__(self, judgments_dir: Path | None = None):
        """初始化加载器.

        Args:
            judgments_dir: 真实判决书 JSON 文件所在目录，默认为 data/real_judgments/
        """
        if judgments_dir is None:
            # 默认路径：项目根目录/data/real_judgments/
            project_root = Path(__file__).resolve().parents[3]
            judgments_dir = project_root /"data" / "real_judgments"
        self.judgments_dir = Path(judgments_dir)
        if not self.judgments_dir.exists() or not self.judgments_dir.is_dir():
            msg = f"判决书目录不存在: {self.judgments_dir}"
            # 抛出异常，处理错误情况
            raise FileNotFoundError(msg)

        # 记录日志信息
        logger.info("初始化真实判决书加载器，目录: {}", self.judgments_dir)

    def load_judgment(self, file_path: Path) -> RealJudgmentSchema:
        """加载单个判决书文件.

        Args:
            file_path: JSON 文件路径

        Returns:
            RealJudgmentSchema: 标准化后的判决书数据

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: JSON 解析失败或字段验证失败
        """
        if not file_path.exists():
            msg = f"文件不存在: {file_path}"
            # 抛出异常，处理错误情况
            raise FileNotFoundError(msg)
        try:
            raw_data = json.loads(file_path.read_text(encoding="utf-8"))
        # 捕获异常：处理业务逻辑
        except json.JSONDecodeError as e:
            msg = f"JSON 解析失败 {file_path.name}: {e}"
            # 抛出异常，处理错误情况
            raise ValueError(msg) from e
        if not isinstance(raw_data, dict):
            msg = f"JSON 顶层必须是对象: {file_path.name}"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        return self._parse_judgment(raw_data, file_path.name)

    def load_all_judgments(self) -> list[RealJudgmentSchema]:
        """批量加载目录下所有判决书文件.

        Returns:
            list[RealJudgmentSchema]: 标准化后的判决书数据列表
        """
        json_files = sorted(self.judgments_dir.glob("GZ*.json"))
        if not json_files:
            # 记录日志信息
            logger.warning("未找到任何 GZ 系列判决书文件: {}", self.judgments_dir)
            return []

        # 记录日志信息
        logger.info("发现 {} 个判决书文件待加载", len(json_files))

        judgments: list[RealJudgmentSchema] = []
        # 循环遍历：处理业务逻辑
        for file_path in json_files:
            # 尝试执行可能抛出异常的代码
            try:
                judgment = self.load_judgment(file_path)
                judgments.append(judgment)
                # 记录日志信息
                logger.debug("成功加载: {}", file_path.name)
            # 捕获并处理异常
            except (ValueError, FileNotFoundError) as e:
                # 记录日志信息
                logger.error("加载失败 {}: {}", file_path.name, e)
                continue

        # 记录日志信息
        logger.info("成功加载 {} / {} 个判决书", len(judgments), len(json_files))
        return judgments

    def _parse_judgment(
        self, raw_data: dict[str, Any], filename: str
    ) -> RealJudgmentSchema:
        """解析原始 JSON 数据为标准化 Schema.

        Args:
            raw_data: 原始 JSON 字典
            filename: 文件名（用于错误提示）

        Returns:
            RealJudgmentSchema: 标准化后的判决书数据

        Raises:
            ValueError: 字段缺失或类型错误
        """
        # 提取基础字段
        case_id = raw_data.get("case_id", "").strip()
        if not case_id:
            msg = f"{filename}: case_id 字段缺失或为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        court = raw_data.get("court", "").strip()
        if not court:
            msg = f"{filename}: court 字段缺失或为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        case_facts = raw_data.get("case_facts", "").strip()
        if not case_facts:
            msg = f"{filename}: case_facts 字段缺失或为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)

        # 提取 actual_judgment 嵌套对象
        actual_judgment = raw_data.get("actual_judgment")
        if not isinstance(actual_judgment, dict):
            msg = f"{filename}: actual_judgment 字段缺失或不是对象"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        subjective_knowledge = str(actual_judgment.get("subjective_knowledge", "")).strip()
        sentence = str(actual_judgment.get("sentence", "")).strip()
        reasoning = str(actual_judgment.get("reasoning", "")).strip()
        if not subjective_knowledge:
            msg = f"{filename}: actual_judgment.subjective_knowledge 字段缺失或为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        if not sentence:
            msg = f"{filename}: actual_judgment.sentence 字段缺失或为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        if not reasoning:
            msg = f"{filename}: actual_judgment.reasoning 字段缺失或为空"
            # 抛出异常，处理错误情况
            raise ValueError(msg)

        # 提取 ground_truth_analysis 嵌套对象
        ground_truth = raw_data.get("ground_truth_analysis")
        if not isinstance(ground_truth, dict):
            msg = f"{filename}: ground_truth_analysis 字段缺失或不是对象"
            # 抛出异常，处理错误情况
            raise ValueError(msg)

        # 维度 1
        dim1 = ground_truth.get("dimension1")
        if not isinstance(dim1, dict):
            msg = f"{filename}: ground_truth_analysis.dimension1 字段缺失或不是对象"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        dim1_score = self._extract_float(dim1, "score", filename, "dimension1.score")
        dim1_reasoning = str(dim1.get("reasoning", "")).strip()
        key_indicators = dim1.get("key_indicators", [])
        if not isinstance(key_indicators, list):
            key_indicators = []

        # 维度 2
        dim2 = ground_truth.get("dimension2")
        if not isinstance(dim2, dict):
            msg = f"{filename}: ground_truth_analysis.dimension2 字段缺失或不是对象"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        dim2_score = self._extract_float(dim2, "score", filename, "dimension2.score")
        dim2_reasoning = str(dim2.get("reasoning", "")).strip()
        pattern_match = str(dim2.get("pattern_match", "")).strip()

        # 维度 3
        dim3 = ground_truth.get("dimension3")
        if not isinstance(dim3, dict):
            msg = f"{filename}: ground_truth_analysis.dimension3 字段缺失或不是对象"
            # 抛出异常，处理错误情况
            raise ValueError(msg)
        dim3_score = self._extract_float(dim3, "score", filename, "dimension3.score")
        dim3_reasoning = str(dim3.get("reasoning", "")).strip()
        contradictions = dim3.get("contradictions", [])
        if not isinstance(contradictions, list):
            contradictions = []

        # 构造标准化 Schema
        try:
            return RealJudgmentSchema(
                case_id=case_id,
                court=court,
                case_facts=case_facts,
                subjective_knowledge=subjective_knowledge,
                sentence=sentence,
                reasoning=reasoning,
                dimension1_score=dim1_score,
                dimension2_score=dim2_score,
                dimension3_score=dim3_score,
                dimension1_reasoning=dim1_reasoning,
                dimension2_reasoning=dim2_reasoning,
                dimension3_reasoning=dim3_reasoning,
                key_indicators=key_indicators,
                pattern_match=pattern_match,
                contradictions=contradictions,
            )
        except Exception as e:
            msg = f"{filename}: 数据验证失败 - {e}"
            # 抛出异常，处理错误情况
            raise ValueError(msg) from e

    def _extract_float(
        self, data: dict[str, Any], field: str, filename: str, path: str
    ) -> float:
        """从字典中提取浮点数并验证.

        Args:
            data: 数据字典
            field: 字段名
            filename: 文件名（用于错误提示）
            path: 字段路径（用于错误提示）

        Returns:
            float: 提取的浮点数

        Raises:
            ValueError: 字段缺失或类型错误
        """
        value = data.get(field)
        if value is None:
            msg = f"{filename}: {path} 字段缺失"
            raise ValueError(msg)

        # 尝试执行可能抛出异常的代码
        try:
            return float(value)
        # 捕获并处理异常
        except (TypeError, ValueError) as e:
            msg = f"{filename}: {path} 必须是数字，当前值: {value}"
            # 抛出异常，处理错误情况
            raise ValueError(msg) from e

    def build_case_from_judgment(
        self, judgment: RealJudgmentSchema, admin_id: int | None = None
    ) -> tuple[Any, str, str]:
        """从标准化判决书构造 Case ORM 对象.

        Args:
            judgment: 标准化判决书数据
            admin_id: 创建者用户 ID（可选）

        Returns:
            tuple: (Case ORM 对象, 状态枚举字符串, 案件类型字符串)
        """
        # 构造标题：使用 case_id + 法院名称
        title = f"{judgment.case_id} - {judgment.court}"
        if len(title) > AnalysisConfig.MAX_TITLE_LENGTH:
            title = title[: AnalysisConfig.MAX_TITLE_LENGTH]

        # 构造描述：包含判决结果和主观明知认定
        description = (
            f"主观明知: {judgment.subjective_knowledge} | "
            f"判决结果: {judgment.sentence}"
        )

        # 构造案件事实文本：包含完整的案件信息
        case_text_parts = [
            f"【案件编号】{judgment.case_id}",
            f"【审理法院】{judgment.court}",
            "",
            "【案件事实】",
            judgment.case_facts,
            "",
            "【裁判理由】",
            judgment.reasoning,
            "",
            "【判决结果】",
            judgment.sentence,
            "",
            "【主观明知认定】",
            judgment.subjective_knowledge,
            "",
            "【维度分析】",
            f"维度1（行为异常程度）: {judgment.dimension1_score}/10",
            judgment.dimension1_reasoning,
            "",
            f"维度2（情节模式匹配）: {judgment.dimension2_score}/10",
            judgment.dimension2_reasoning,
            "",
            f"维度3（辩解合理性）: {judgment.dimension3_score}/10",
            judgment.dimension3_reasoning,
        ]
        case_text = "\n".join(case_text_parts)

        # 导入 Case 模型（延迟导入避免循环依赖）
        from app.models.case import Case

        case = Case(
            title=title,
            description=description,
            case_text=case_text,
            status=CaseStatus.completed,  # 真实判决书已判决完成
            source="real_gz2023",
            judgment_no=judgment.case_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        if admin_id is not None:
            case.created_by = admin_id
        return case, CaseStatus.completed.value, "帮助信息网络犯罪活动罪"
