"""混淆矩阵模块单元测试.

测试混淆矩阵计算、JSON输出、PNG生成和文本降级功能。
"""

# 导入模块: json
import json
# 导入模块: from pathlib
from pathlib import Path

# 导入模块: pytest
import pytest

# 导入模块: from backend.app.eval.confusion_matrix
from backend.app.eval.confusion_matrix import (
    compute_confusion_matrix,
    compute_per_class_metrics,
    format_confusion_json,
    render_confusion_png,
    render_confusion_text,
    save_confusion_json,
    save_confusion_matrix,
)


# 定义 TestComputeConfusionMatrix 类
class TestComputeConfusionMatrix:
    """混淆矩阵计算测试."""

    def test_4x4_matrix(self):
        """测试4×4分类矩阵的计算准确性."""
        # 初始化变量 y_true
        y_true = [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3]
        # 初始化变量 y_pred
        y_pred = [0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 0]
        
        cm = compute_confusion_matrix(y_true, y_pred)
        
        assert cm["classes"] == 4
        assert cm["total_samples"] == 12
        assert len(cm["matrix"]) == 4
        assert all(len(row) == 4 for row in cm["matrix"])
        
        # 验证具体数值
        assert cm["matrix"][0][0] == 2  # 类别0正确预测
        assert cm["matrix"][0][1] == 1  # 类别0误判为1
        assert cm["matrix"][1][1] == 2  # 类别1正确预测
        assert cm["matrix"][1][2] == 1  # 类别1误判为2
        assert cm["matrix"][2][2] == 2  # 类别2正确预测
        assert cm["matrix"][2][3] == 1  # 类别2误判为3
        assert cm["matrix"][3][3] == 2  # 类别3正确预测
        assert cm["matrix"][3][0] == 1  # 类别3误判为0

    def test_binary_classification(self):
        """测试二分类情况."""
        # 初始化变量 y_true
        y_true = [0, 0, 0, 1, 1, 1]
        # 初始化变量 y_pred
        y_pred = [0, 0, 1, 1, 1, 0]
        
        cm = compute_confusion_matrix(y_true, y_pred)
        
        assert cm["classes"] == 2
        assert cm["matrix"][0][0] == 2  # TN
        assert cm["matrix"][0][1] == 1  # FP
        assert cm["matrix"][1][0] == 1  # FN
        assert cm["matrix"][1][1] == 2  # TP

    def test_with_custom_labels(self):
        """测试自定义标签."""
        # 初始化变量 y_true
        y_true = [0, 1, 2]
        # 初始化变量 y_pred
        y_pred = [0, 1, 2]
        # 初始化变量 labels
        labels = ["类别A", "类别B", "类别C"]
        
        cm = compute_confusion_matrix(y_true, y_pred, labels=labels)
        
        assert cm["labels"] == labels

    def test_accuracy_calculation(self):
        """测试准确率计算."""
        # 初始化变量 y_true
        y_true = [0, 0, 1, 1, 2, 2]
        # 初始化变量 y_pred
        y_pred = [0, 0, 1, 1, 2, 2]  # 完全正确
        
        cm = compute_confusion_matrix(y_true, y_pred)
        
        assert cm["correct_predictions"] == 6
        assert cm["accuracy"] == 1.0

    def test_empty_input(self):
        """测试空输入."""
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="输入数据不能为空"):
            compute_confusion_matrix([], [])

    def test_length_mismatch(self):
        """测试长度不匹配."""
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="真实标签和预测标签长度不匹配"):
            compute_confusion_matrix([0, 1], [0])


# 定义 TestComputePerClassMetrics 类
class TestComputePerClassMetrics:
    """每类别指标计算测试."""

    def test_per_class_metrics(self):
        """测试每类别的precision、recall、f1计算."""
        # 初始化变量 y_true
        y_true = [0, 0, 0, 1, 1, 1, 2, 2, 2]
        # 初始化变量 y_pred
        y_pred = [0, 0, 1, 1, 1, 2, 2, 2, 0]
        
        cm = compute_confusion_matrix(y_true, y_pred)
        # 初始化变量 metrics
        metrics = compute_per_class_metrics(cm)
        
        assert "class_0" in metrics
        assert "class_1" in metrics
        assert "class_2" in metrics
        
        # 验证每个类别都有precision、recall、f1_score、support
        # 循环遍历：处理业务逻辑
        for label in ["class_0", "class_1", "class_2"]:
            assert "precision" in metrics[label]
            assert "recall" in metrics[label]
            assert "f1_score" in metrics[label]
            assert "support" in metrics[label]

    def test_perfect_classification(self):
        """测试完美分类的指标."""
        # 初始化变量 y_true
        y_true = [0, 0, 1, 1, 2, 2]
        # 初始化变量 y_pred
        y_pred = [0, 0, 1, 1, 2, 2]
        
        cm = compute_confusion_matrix(y_true, y_pred)
        # 初始化变量 metrics
        metrics = compute_per_class_metrics(cm)
        
        # 完美分类时，所有指标应为1.0
        for label in metrics:
            assert metrics[label]["precision"] == 1.0
            assert metrics[label]["recall"] == 1.0
            assert metrics[label]["f1_score"] == 1.0


# 定义 TestJsonOutput 类
class TestJsonOutput:
    """JSON输出格式测试."""

    def test_format_confusion_json(self):
        """测试JSON格式输出的完整性."""
        # 初始化变量 y_true
        y_true = [0, 1, 2, 0, 1, 2]
        # 初始化变量 y_pred
        y_pred = [0, 1, 2, 0, 1, 0]
        
        cm = compute_confusion_matrix(y_true, y_pred)
        # 初始化变量 json_str
        json_str = format_confusion_json(cm)
        
        # 验证可以解析为JSON
        data = json.loads(json_str)
        
        # 验证所有必需字段
        assert "matrix" in data
        assert "labels" in data
        assert "classes" in data
        assert "total_samples" in data
        assert "correct_predictions" in data
        assert "accuracy" in data

    def test_save_confusion_json(self, tmp_path):
        """测试保存JSON文件."""
        # 初始化变量 y_true
        y_true = [0, 1, 2]
        # 初始化变量 y_pred
        y_pred = [0, 1, 2]
        
        cm = compute_confusion_matrix(y_true, y_pred)
        # 初始化变量 output_path
        output_path = tmp_path / "test_cm.json"
        
        save_confusion_json(cm, output_path)
        
        assert output_path.exists()
        
        # 验证文件内容
        with output_path.open("r", encoding="utf-8") as f:
            # 初始化变量 data
            data = json.load(f)
        assert data["classes"] == 3


# 定义 TestPngGeneration 类
class TestPngGeneration:
    """PNG图像生成测试."""

    def test_render_confusion_png(self, tmp_path):
        """测试PNG图像生成功能."""
        # 初始化变量 y_true
        y_true = [0, 1, 2, 0, 1, 2]
        # 初始化变量 y_pred
        y_pred = [0, 1, 2, 0, 1, 0]
        
        cm = compute_confusion_matrix(y_true, y_pred)
        # 初始化变量 output_path
        output_path = tmp_path / "test_cm.png"
        
        # 初始化变量 success
        success = render_confusion_png(cm, output_path, title="测试混淆矩阵")
        
        # 如果matplotlib可用，应该成功生成
        # 条件判断：处理业务逻辑
        if success:
            assert output_path.exists()
            # 验证文件大小大于0
            assert output_path.stat().st_size > 0

    def test_save_confusion_matrix_complete(self, tmp_path):
        """测试完整的保存流程."""
        # 初始化变量 y_true
        y_true = [0, 1, 2, 0, 1, 2]
        # 初始化变量 y_pred
        y_pred = [0, 1, 2, 0, 1, 0]
        
        # 初始化变量 result
        result = save_confusion_matrix(
            y_true,
            y_pred,
            tmp_path,
            # 初始化变量 labels
            labels=["A", "B", "C"],
            # 初始化变量 prefix
            prefix="test",
        )
        
        # 验证JSON文件总是生成
        assert "json_path" in result
        assert Path(result["json_path"]).exists()
        
        # 验证PNG或文本文件生成
        if result["png_generated"]:
            assert "png_path" in result
            assert Path(result["png_path"]).exists()
        # 其他情况的默认处理
        else:
            assert "text_path" in result
            assert Path(result["text_path"]).exists()


# 定义 TestTextFallback 类
class TestTextFallback:
    """文本降级机制测试."""

    def test_render_confusion_text(self):
        """测试文本格式输出."""
        # 初始化变量 y_true
        y_true = [0, 1, 2, 0, 1, 2]
        # 初始化变量 y_pred
        y_pred = [0, 1, 2, 0, 1, 0]
        
        cm = compute_confusion_matrix(y_true, y_pred)
        # 初始化变量 text
        text = render_confusion_text(cm)
        
        # 验证包含关键信息
        assert "混淆矩阵" in text
        assert "总样本数" in text
        assert "准确率" in text
        assert "class_0" in text or "0" in text
        assert "class_1" in text or "1" in text
        assert "class_2" in text or "2" in text

    def test_text_format_structure(self):
        """测试文本格式的结构."""
        # 初始化变量 y_true
        y_true = [0, 1]
        # 初始化变量 y_pred
        y_pred = [0, 1]
        
        cm = compute_confusion_matrix(y_true, y_pred)
        # 初始化变量 text
        text = render_confusion_text(cm)
        
        # 初始化变量 lines
        lines = text.split("\n")
        
        # 验证有分隔线
        assert any("=" in line for line in lines)
        assert any("-" in line for line in lines)
        
        # 验证包含准确率
        assert "100.00%" in text or "1.0000" in text
