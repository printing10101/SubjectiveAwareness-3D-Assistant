"""
tests/test_real_judgment_loader.py
真实判决书数据加载器测试
"""
import json
import pytest
from pathlib import Path

from backend.app.services.real_judgment_loader import (
    RealJudgmentLoader,
    RealJudgmentSchema,
    load_real_judgment,
    load_all_real_judgments,
)


@pytest.fixture
def sample_judgment_data() -> dict:
    """样本真实判决书数据"""
    return {
        "case_id": "GZ2023BX001",
        "court": "贵州省贵阳市中级人民法院",
        "case_facts": "被告人张某明知他人利用信息网络实施犯罪，仍为其提供银行卡用于支付结算。",
        "subjective_knowledge": "被告人供述明知对方用于违法犯罪活动",
        "sentence": "判处有期徒刑一年，并处罚金人民币五千元",
        "reasoning": "本院认为，被告人明知他人利用信息网络实施犯罪，仍为其提供帮助，情节严重，构成帮助信息网络犯罪活动罪。",
        "dimension1_score": 0.85,
        "dimension2_score": 0.72,
        "dimension3_score": 0.68,
        "dimension1_reasoning": "被告人明确供述明知行为的非法性",
        "dimension2_reasoning": "提供银行卡属于典型的客观帮助行为",
        "dimension3_reasoning": "存在直接供述与客观行为的一致性",
        "key_indicators": ["明知", "提供银行卡", "支付结算"],
        "pattern_match": "直接供述 + 客观行为匹配",
        "contradictions": [],
    }


@pytest.fixture
def judgments_dir(tmp_path: Path) -> Path:
    """创建临时判决书目录并写入样本文件"""
    judgment_dir = tmp_path / "real_judgments"
    judgment_dir.mkdir()

    for i in range(1, 4):
        data = {
            "case_id": f"GZ2023BX00{i}",
            "court": "贵州省贵阳市中级人民法院",
            "case_facts": f"案件事实描述 {i}",
            "subjective_knowledge": f"主观明知描述 {i}",
            "sentence": f"判决结果 {i}",
            "reasoning": f"裁判理由 {i}",
            "dimension1_score": 0.8,
            "dimension2_score": 0.7,
            "dimension3_score": 0.6,
            "dimension1_reasoning": f"维度1推理 {i}",
            "dimension2_reasoning": f"维度2推理 {i}",
            "dimension3_reasoning": f"维度3推理 {i}",
            "key_indicators": ["明知", "帮助"],
            "pattern_match": "模式匹配",
            "contradictions": [],
        }
        file_path = judgment_dir / f"GZ2023BX00{i}.json"
        file_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    return judgment_dir


class TestRealJudgmentSchema:
    """测试数据模型验证"""

    def test_valid_schema(self, sample_judgment_data: dict):
        """测试有效数据通过验证"""
        schema = RealJudgmentSchema(**sample_judgment_data)
        assert schema.case_id == "GZ2023BX001"
        assert schema.dimension1_score == 0.85
        assert isinstance(schema.key_indicators, list)

    def test_missing_required_field(self, sample_judgment_data: dict):
        """测试缺失必填字段时抛出异常"""
        del sample_judgment_data["case_id"]
        with pytest.raises(Exception):
            RealJudgmentSchema(**sample_judgment_data)

    def test_invalid_score_type(self, sample_judgment_data: dict):
        """测试分数类型错误时抛出异常"""
        sample_judgment_data["dimension1_score"] = "invalid"
        with pytest.raises(Exception):
            RealJudgmentSchema(**sample_judgment_data)

    def test_score_range_validation(self, sample_judgment_data: dict):
        """测试分数范围验证"""
        sample_judgment_data["dimension1_score"] = 1.5  # 超出 0-1 范围
        with pytest.raises(Exception):
            RealJudgmentSchema(**sample_judgment_data)


class TestRealJudgmentLoader:
    """测试加载器功能"""

    def test_load_single_judgment(self, judgments_dir: Path):
        """测试加载单个判决书文件"""
        loader = RealJudgmentLoader(judgments_dir)
        file_path = judgments_dir / "GZ2023BX001.json"
        judgment = loader.load_judgment(file_path)
        assert judgment.case_id == "GZ2023BX001"
        assert judgment.court == "贵州省贵阳市中级人民法院"

    def test_load_all_judgments(self, judgments_dir: Path):
        """测试批量加载所有判决书"""
        loader = RealJudgmentLoader(judgments_dir)
        judgments = loader.load_all_judgments()
        assert len(judgments) == 3
        case_ids = {j.case_id for j in judgments}
        assert case_ids == {"GZ2023BX001", "GZ2023BX002", "GZ2023BX003"}

    def test_load_nonexistent_file(self, judgments_dir: Path):
        """测试加载不存在的文件"""
        loader = RealJudgmentLoader(judgments_dir)
        file_path = judgments_dir / "nonexistent.json"
        with pytest.raises(FileNotFoundError):
            loader.load_judgment(file_path)

    def test_load_invalid_json(self, judgments_dir: Path):
        """测试加载格式错误的 JSON 文件"""
        invalid_file = judgments_dir / "invalid.json"
        invalid_file.write_text("{invalid json content", encoding="utf-8")
        loader = RealJudgmentLoader(judgments_dir)
        with pytest.raises(json.JSONDecodeError):
            loader.load_judgment(invalid_file)

    def test_load_missing_fields(self, judgments_dir: Path):
        """测试加载缺失字段的文件"""
        incomplete_file = judgments_dir / "incomplete.json"
        incomplete_data = {"case_id": "GZ2023BX999"}  # 缺失大量必填字段
        incomplete_file.write_text(json.dumps(incomplete_data), encoding="utf-8")
        loader = RealJudgmentLoader(judgments_dir)
        with pytest.raises(Exception):
            loader.load_judgment(incomplete_file)


class TestModuleLevelFunctions:
    """测试模块级函数"""

    def test_load_real_judgment(self, judgments_dir: Path):
        """测试模块级单文件加载函数"""
        file_path = judgments_dir / "GZ2023BX001.json"
        judgment = load_real_judgment(file_path)
        assert judgment.case_id == "GZ2023BX001"

    def test_load_all_real_judgments(self, judgments_dir: Path):
        """测试模块级批量加载函数"""
        judgments = load_all_real_judgments(judgments_dir)
        assert len(judgments) == 3
