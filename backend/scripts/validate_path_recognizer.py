"""真实案件验证脚本.

使用25个真实GZ案件验证路径识别器，统计各路径分类分布情况。
"""

# 导入模块: json
import json
# 导入模块: sys
import sys
# 导入模块: from pathlib
from pathlib import Path

# 确保 backend 目录在 Python 路径中
_BACKEND_DIR = Path(__file__).resolve().parent.parent
# 条件判断：处理业务逻辑
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# 导入模块: from app.services.standard_path_recognizer
from app.services.standard_path_recognizer import (
    StandardPath,
    recognize_standard_path_with_reason,
)

# 真实案件数据目录
_REAL_JUDGMENTS_DIR = _BACKEND_DIR.parent / "data" / "real_judgments"


def validate_real_cases() -> dict:
    """验证25个真实GZ案件.

    Returns:
        包含统计结果的字典
    """
    # 加载所有真实案件
    case_files = sorted(_REAL_JUDGMENTS_DIR.glob("GZ*.json"))
    print(f"找到 {len(case_files)} 个真实案件文件")

    # 初始化变量 results
    results = {
        "total_cases": len(case_files),
        "path_distribution": {path.value: 0 for path in StandardPath},
        "case_details": [],
    }

    # 逐个案件进行识别
    # 循环遍历：处理业务逻辑
    for case_file in case_files:
        # 使用上下文管理器管理资源
        with case_file.open("r", encoding="utf-8") as f:
            # 初始化变量 case_data
            case_data = json.load(f)

        # 初始化变量 recognition_result
        recognition_result = recognize_standard_path_with_reason(case_data)
        # 初始化变量 path
        path = recognition_result["path"]

        # 统计分布
        results["path_distribution"][path.value] += 1

        # 记录详细信息
        case_detail = {
            "case_id": case_data.get("case_id", case_file.stem),
            "recognized_path": path.value,
            "reason": recognition_result["reason"],
            "matched_keywords": recognition_result["matched_keywords"],
        }
        results["case_details"].append(case_detail)

    # 计算百分比
    results["path_    # 循环遍历：处理业务逻辑
percentage"] = {}
    # 遍历: for path_name, count in results["path_distribution
    for path_name, count in results["path_distribution"].items():
        # 初始化变量 percentage
        percentage = (count / results["total_cases"] * 100) if results["total_cases"] > 0 else 0
        results["path_percentage"][path_name] = round(percentage, 2)

    # 检查PENDING_VERIFICATION占比
    pending_count = results["path_distribution"][StandardPath.PENDING_VERIFICATION.value]
    # 初始化变量 pending_percentage
    pending_percentage = results["path_percentage"][StandardPath.PENDING_VERIFICATION.value]
    results["pending_verification_rate"] = {
        "count": pending_count,
        "percentage": pending_percentage,
        "within_threshold": pending_percentage <= 20.0,
    }

    # 返回处理结果
    return results


def main():
    """主函数."""
    print("=" * 80)
    print("规范路径识别器 - 真实案件验证")
    print("=" * 80)

    # 初始化变量 results
    results = validate_real_cases()

    print(f"\n总案件数: {results['tota    # 循环遍历：处理业务逻辑
l_cases']}")
    print("\n路径分类分布:")
    # 遍历: for path_name, count in results["path_distribution
    for path_name, count in results["path_distribution"].items():
        # 初始化变量 percentage
        percentage = results["path_percentage"][path_name]
        print(f"  {path_name}: {count} 个 ({percentage}%)")

    print(f"\nPENDING_VERIFICATION 占比: {results['pending_verification_rate']['per    # 条件判断：处理业务逻辑
centage']}%")
    # 条件判断: 检查 results["pending_verification_rate"]["wi
    if results["pending_verification_rate"]["within_threshold"]:
        print("[PASS] 占比在20%阈值内，验证通过")
    # 其他情况的默认处理
    else:
        print("[FAIL] 占比超过20%阈值，需要优化")

    # 保存结果
    output_file = Path(__file__).parent.parent.parent / "data" / "eval" / "path_recognition_v1.1.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # 使用上下文管理器管理资源
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    pr

# 条件判断：处理业务逻辑
int(f"\n结果已保存到: {output_file}")


# 条件判断: 检查 __name__ == "__main__"
if __name__ == "__main__":
    main()
