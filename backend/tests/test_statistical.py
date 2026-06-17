"""统计功能模块单元测试.

测试所有核心统计函数的正确性和边界情况处理。
"""

# 导入模块: pytest
import pytest

# 导入模块: from backend.app.eval.statistical
from backend.app.eval.statistical import (
    ai_agreement_rate,
    cohens_kappa,
    confusion_matrix,
    descriptive_statistics,
    time_performance_analysis,
)


# 定义 TestCohensKappa 类
class TestCohensKappa:
    """Cohen's Kappa 系数计算测试."""

    def test_perfect_agreement(self):
        """测试完全一致的情况."""
        # 初始化变量 labels
        labels = ["A", "B", "C", "A", "B", "C", "A", "B", "C", "A"]
        # 初始化变量 kappa
        kappa = cohens_kappa(labels, labels)
        assert kappa == 1.0

    def test_high_agreement(self):
        """测试高一致性（90/100 一致，Kappa 应接近 0.85）."""
        # 构造 100 例样本，90 例一致
        y_true = ["A"] * 50 + ["B"] * 50
        # 初始化变量 y_pred
        y_pred = ["A"] * 45 + ["B"] * 45 + ["A"] * 5 + ["B"] * 5

        # 初始化变量 kappa
        kappa = cohens_kappa(y_true, y_pred)
        # Kappa 应在 0.75-0.90 范围
        assert 0.70 <= kappa <= 0.95

    def test_random_agreement(self):
        """测试随机一致性（Kappa 应接近 0）."""
        # 导入模块: random
        import random
        random.seed(42)
        # 初始化变量 all_labels
        all_labels = ["A", "B", "C"]
        # 初始化变量 y_true
        y_true = [random.choice(all_labels) for _ in range(1000)]
        # 初始化变量 y_pred
        y_pred = [random.choice(all_labels) for _ in range(1000)]
        # 初始化变量 kappa
        kappa = cohens_kappa(y_true, y_pred)
        # 随机情况下 Kappa 应接近 0
        assert -0.15 <= kappa <= 0.15

    def test_no_agreement(self):
        """测试完全不一致的情况（Kappa 应为负值）."""
        # 初始化变量 y_true
        y_true = ["A", "B", "C", "A", "B", "C"]
        # 初始化变量 y_pred
        y_pred = ["B", "C", "A", "C", "A", "B"]  # 完全错位
        kappa = cohens_kappa(y_true, y_pred)
        assert kappa < 0

    def test_binary_classification(self):
        """测试二分类情况."""
        # 初始化变量 y_true
        y_true = ["A", "A", "A", "A", "B", "B", "B", "B"]
        # 初始化变量 y_pred
        y_pred = ["A", "A", "A", "B", "B", "B", "B", "A"]
        # 初始化变量 kappa
        kappa = cohens_kappa(y_true, y_pred)
        assert 0.3 <= kappa <= 0.7

    def test_empty_input(self):
        """测试空输入."""
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="标签列表不能为空"):
            cohens_kappa([], [])

    def test_length_mismatch(self):
        """测试长度不匹配."""
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="长度必须相同"):
            cohens_kappa(["A", "B"], ["A"])


# 定义 TestDescriptiveStatistics 类
class TestDescriptiveStatistics:
    """描述性统计分析测试."""

    def test_normal_data(self):
        """测试正常数据."""
        # 初始化变量 data
        data = [10.0, 20.0, 30.0, 40.0, 50.0]
        # 初始化变量 stats
        stats = descriptive_statistics(data)

        assert stats["count"] == 5
        assert stats["mean"] == 30.0
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0
        assert 15.81 <= stats["std"] <= 15.82  # 样本标准差 (ddof=1)
        assert stats["median"] == 30.0

    def test_single_value(self):
        """测试单个值."""
        # 初始化变量 stats
        stats = descriptive_statistics([42.0])
        assert stats["count"] == 1
        assert stats["mean"] == 42.0
        assert stats["std"] == 0.0
        assert stats["median"] == 42.0

    def test_even_count_median(self):
        """测试偶数个数据的中位数."""
        # 初始化变量 data
        data = [1.0, 2.0, 3.0, 4.0]
        # 初始化变量 stats
        stats = descriptive_statistics(data)
        assert stats["median"] == 2.5

    def test_with_outliers(self):
        """测试包含异常值的数据."""
        # 初始化变量 data
        data = [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]
        # 初始化变量 stats
        stats = descriptive_statistics(data)
        assert stats["mean"] > stats["median"]  # 异常值拉高均值

    def test_empty_input(self):
        """测试空输入."""
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="数值列表不能为空"):
            descriptive_statistics([])


# 定义 TestAiAgreementRate 类
class TestAiAgreementRate:
    """AI 一致率计算测试."""

    def test_perfect_agreement(self):
        """测试完全一致."""
        # 初始化变量 y_true
        y_true = ["A", "B", "C", "A", "B"]
        # 初始化变量 y_pred
        y_pred = ["A", "B", "C", "A", "B"]
        # 初始化变量 result
        result = ai_agreement_rate(y_true, y_pred)
        assert result["agreement_rate"] == 1.0
        assert result["consistent"] == 5
        assert result["inconsistent"] == 0

    def test_partial_agreement(self):
        """测试部分一致."""
        # 初始化变量 y_true
        y_true = ["A", "B", "C", "A", "B", "C", "A", "B", "C", "A"]
        # 初始化变量 y_pred
        y_pred = ["A", "B", "C", "A", "B", "C", "A", "B", "A", "A"]  # 9/10 一致
        result = ai_agreement_rate(y_true, y_pred)
        assert result["agreement_rate"] == 0.9
        assert result["consistent"] == 9
        assert result["inconsistent"] == 1

    def test_no_agreement(self):
        """测试完全不一致."""
        # 初始化变量 y_true
        y_true = ["A", "B", "C"]
        # 初始化变量 y_pred
        y_pred = ["B", "C", "A"]
        # 初始化变量 result
        result = ai_agreement_rate(y_true, y_pred)
        assert result["agreement_rate"] == 0.0
        assert result["consistent"] == 0

    def test_empty_input(self):
        """测试空输入."""
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="标签列表不能为空"):
            ai_agreement_rate([], [])

    def test_length_mismatch(self):
        """测试长度不匹配."""
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="长度必须相同"):
            ai_agreement_rate(["A", "B"], ["A"])

    def test_with_categories(self):
        """测试按类别统计."""
        # 初始化变量 y_true
        y_true = ["A", "A", "B", "B"]
        # 初始化变量 y_pred
        y_pred = ["A", "B", "B", "B"]
        # 初始化变量 result
        result = ai_agreement_rate(y_true, y_pred, categories=["A", "B"])
        assert "by_category" in result
        assert result["by_category"]["A"]["agreement_rate_pct"] == 50.0
        assert result["by_category"]["B"]["agreement_rate_pct"] == 100.0


# 定义 TestConfusionMatrix 类
class TestConfusionMatrix:
    """混淆矩阵生成测试."""

    def test_binary_classification(self):
        """测试二分类混淆矩阵."""
        # 初始化变量 y_true
        y_true = ["A", "A", "A", "B", "B", "B"]
        # 初始化变量 y_pred
        y_pred = ["A", "A", "B", "B", "B", "A"]

        cm = confusion_matrix(y_true, y_pred)

        # 验证结构
        assert "matrix" in cm
        assert "labels" in cm
        assert "accuracy" in cm
        assert "per_class" in cm
        assert "total_samples" in cm
        assert cm["total_samples"] == 6

    def test_multiclass_classification(self):
        """测试多分类混淆矩阵."""
        # 初始化变量 y_true
        y_true = ["A", "A", "B", "B", "C", "C"]
        # 初始化变量 y_pred
        y_pred = ["A", "B", "B", "B", "C", "A"]

        cm = confusion_matrix(y_true, y_pred)

        assert len(cm["labels"]) == 3
        assert len(cm["matrix"]) == 3
        assert all(len(row) == 3 for row in cm["matrix"])

    def test_with_labels(self):
        """测试带标签的混淆矩阵."""
        # 初始化变量 y_true
        y_true = ["A", "B", "C"]
        # 初始化变量 y_pred
        y_pred = ["A", "B", "C"]
        # 初始化变量 labels
        labels = ["C", "B", "A"]  # 自定义顺序

        cm = confusion_matrix(y_true, y_pred, labels=labels)

        assert cm["labels"] == labels

    def test_per_class_metrics(self):
        """测试每类指标."""
        # 初始化变量 y_true
        y_true = ["A", "A", "B", "B"]
        # 初始化变量 y_pred
        y_pred = ["A", "A", "B", "B"]

        cm = confusion_matrix(y_true, y_pred)

        # 遍历: for lbl in cm["labels"]:
        for lbl in cm["labels"]:
            assert "precision" in cm["per_class"][lbl]
            assert "recall" in cm["per_class"][lbl]
            assert "f1" in cm["per_class"][lbl]
            assert "support" in cm["per_class"][lbl]
            # 完美分类时指标应为 1.0
            assert cm["per_class"][lbl]["precision"] == 1.0
            assert cm["per_class"][lbl]["recall"] == 1.0
            assert cm["per_class"][lbl]["f1"] == 1.0

    def test_accuracy(self):
        """测试准确率计算."""
        # 初始化变量 y_true
        y_true = ["A", "A", "B", "B"]
        # 初始化变量 y_pred
        y_pred = ["A", "A", "B", "B"]

        cm = confusion_matrix(y_true, y_pred)
        assert cm["accuracy"] == 1.0

    def test_empty_input(self):
        """测试空输入."""
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="标签列表不能为空"):
            confusion_matrix([], [])


# 定义 TestTimePerformanceAnalysis 类
class TestTimePerformanceAnalysis:
    """时间性能分析测试."""

    def test_normal_comparison(self):
        """测试正常的时间对比."""
        # 初始化变量 times_a
        times_a = [1.0, 2.0, 3.0, 4.0, 5.0]
        # 初始化变量 times_b
        times_b = [1.5, 2.5, 3.5, 4.5, 5.5]
        # 初始化变量 analysis
        analysis = time_performance_analysis(times_a, times_b)

        assert "group_a" in analysis
        assert "group_b" in analysis
        assert "mean_difference" in analysis
        assert "t_statistic" in analysis
        assert "p_value" in analysis
        assert "cohens_d" in analysis
        assert "is_significant" in analysis

    def test_identical_groups(self):
        """测试相同组."""
        # 初始化变量 times
        times = [1.0, 2.0, 3.0]
        # 初始化变量 analysis
        analysis = time_performance_analysis(times, times)
        assert analysis["mean_difference"] == 0.0
        assert analysis["cohens_d"] == 0.0

    def test_significant_difference(self):
        """测试显著差异."""
        # 初始化变量 times_a
        times_a = [1.0, 1.1, 0.9, 1.0, 1.05]
        # 初始化变量 times_b
        times_b = [5.0, 5.1, 4.9, 5.0, 5.05]
        # 初始化变量 analysis
        analysis = time_performance_analysis(times_a, times_b)

        # 均值差异应接近 -4.0
        assert analysis["mean_difference"] < -3.0
        # p 值应很小（显著）
        assert analysis["p_value"] < 0.05
        assert analysis["is_significant"] is True

    def test_empty_input(self):
        """测试空输入."""
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="时间列表不能为空"):
            time_performance_analysis([], [1.0])
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="时间列表不能为空"):
            time_performance_analysis([1.0], [])

    def test_group_statistics(self):
        """测试各组统计信息."""
        # 初始化变量 times_a
        times_a = [1.0, 2.0, 3.0]
        # 初始化变量 times_b
        times_b = [4.0, 5.0, 6.0]
        # 初始化变量 analysis
        analysis = time_performance_analysis(times_a, times_b)

        assert analysis["group_a"]["count"] == 3
        assert analysis["group_a"]["mean"] == 2.0
        assert analysis["group_b"]["count"] == 3
        assert analysis["group_b"]["mean"] == 5.0
