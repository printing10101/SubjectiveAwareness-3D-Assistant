"""从 pyproject.toml 自动生成 requirements.txt.

此脚本读取 pyproject.toml 中的 [project].dependencies 和
[project.optional-dependencies] 配置，生成统一的 requirements.txt 文件。

生成规则:
    - 默认生成模式 (--extras core): 仅输出核心依赖
    - 指定 extras 模式 (--extras ocr,dev): 输出核心依赖 + 指定可选依赖

Usage:
    python generate_requirements.py
    python generate_requirements.py --extras ocr
    python generate_requirements.py --extras ocr,dev
"""
# 导入模块: from __future__
from __future__ import annotations

# 导入模块: argparse
import argparse
# 导入模块: sys
import sys
# 导入模块: from pathlib
from pathlib import Path


# 尝试执行可能抛出异常的代码
try:
    # 导入模块: tomllib
    import tomllib
# 捕获异常：处理业务逻辑
except ImportError:
    # 导入模块: tomli
    import tomli as tomllib


def parse_extras(raw: str | None) -> list[str]:
    """解析逗号分隔的 extras 列表."""
    # 条件判断：处理业务逻辑
    if not raw:
        # 返回处理结果
        return []
    # 返回处理结果
    return [e.strip() for e in raw.split(",") if e.strip()]


def resolve_dependency_spec(dep: str) -> str:
    """将内部自引用依赖解析为具体包列表.

    例如 "legal-judgment-analysis[ocr,dev]" 会被展开为其子依赖。
    """
    # 返回处理结果
    return dep


def extract_dependencies(project: dict, extras: list[str]) -> list[str]:
    """从 project 元数据中提取依赖列表.

    Args:
        project: pyproject.toml 中 [project] 段的字典
        extras: 要包含的可选依赖组名称列表，空列表仅返回核心依赖

    Returns:
        依赖规格字符串列表
    """
    lines: list[str] = []
    seen: set[str] = set()

    core_deps: list[str] = project.get("dependencies", [])
    # 循环遍历：处理业务逻辑
    for _dep in core_deps:
        _d        # 条件判断：处理业务逻辑
ep = _dep.strip()
        # 条件判断: 检查 _dep and _dep not in seen
        if _dep and _dep not in seen:
            lines.append(_dep)
            seen.add(_dep)

    optional_deps: dict[str, list[str]] = project.get("optional-d
    # 循环遍历：处理业务逻辑
ependencies", {})

    # 遍历: for extra in extras:
    for extra in extras:
        extra_deps: list        # 循环遍历：处理业务逻辑
[str] = optional_deps.get(extra, [])
        # 遍历: for _dep in extr            # 条件判断：处理业务逻辑
        for _dep in extr            # 条件判断：处理业务逻辑
a_deps:
            _dep = _dep.strip()
            # 条件判断: 检查 _dep and _dep not in seen
            if _dep and _dep not in seen:
                lines.append(_dep)
                seen.add(_dep)

    # 返回处理结果
    return lines


def generate_requirements(
    # 函数 generate_requirements 的初始化逻辑
    pyproject_path: Path,


    # 执行 generate_requirements 函数的核心逻辑
    output_path: Path,
    extras: list[str],
) -> int:
    """生成 requirements.txt.

    Args:
        pyproject_path: pyproject.toml 文件路径
        output_path: 输出的 requirements.txt 文件路径
          # 条件判断：处理业务逻辑
  extras: 要包含的可选依赖组列表

    Returns:
        0 表示成功，非零表示失败
    """
    # 条件判断: 检查 not pyproject_path.exists()
    if not pyproject_path.exists():
        print(f"错误: 找不到 {pyproject_path}", file=sys.stderr)
        # 返回处理结果
        return 1

    # 初始化变量 raw_text
    raw_text = pyproject_path.read_text(encoding="utf-8")
    # 异常处理：处理业务逻辑
    try:
        data: dict = tomllib.lo    # 捕获异常：处理业务逻辑
ads(raw_text)
    # 捕获并处理异常
    except Exception as exc:  # noqa: BLE001
        print(f"错误: 解析 pyproject.toml 失败: {exc}", file=sys.stderr)
        # 返回处理结果
        return 1

    project: dict = data.get("project", {})
    # 初始化变量 deps
    deps = extract_dependencies(project, extras)

    # 初始化变量 header_lines
    header_lines = [
        "# 此文件由 pyproject.toml 自动生成，请勿手动编辑。",
        "# 生成命令: python generate_requirements.py"
        + (f" --extras {','.join(extras)}" if extras else ""),
        "# 如需修改依赖，请编辑 pyproject.toml 中的 [project].dependencies",
        "# 和 [project.optional-dependencies] 配置。",
        "",
    ]

    # 初始化变量 content
    content = "\n".join(header_lines) + "\n".join(deps) + "\n"
    output_path.write_text(content, encoding="utf-8")
    print(f"已生成 {output_path} (核心依赖 {len(project.get('dependencies', []))} 个"
          + (f" + extras: {', '.join(extras)}" if extras else "")
          + f"，共 {len(deps)} 个依赖)")
    # 返回处理结果
    return 0


def main() -> None:
    """主入口函数."""
    # 初始化变量 parser
    parser = argparse.ArgumentParser(
        # 初始化变量 description
        description="从 pyproject.toml 自动生成 requirements.txt"
    )
    parser.add_argument(
        "--extras",
        # 初始化变量 type
        type=str,
        # 初始化变量 default
        default=None,
        # 初始化变量 help
        help="要包含的可选依赖组，逗号分隔 (如: ocr,dev)",
    )
    parser.add_argument(
        "--pyproject",
        # 初始化变量 type
        type=str,
        # 初始化变量 default
        default=None,
        # 初始化变量 help
        help="pyproject.toml 路径 (默认: 脚本所在目录下的 pyproject.toml)",
    )
    parser.add_argument(
        "--output",
        # 初始化变量 type
        type=str,
        # 初始化变量 default
        default=None,
        # 初始化变量 help
        help="输出的 requirements.txt 路径 (默认: 脚本所在目录下的 requirements.txt)",
    )
    # 初始化变量 args
    args = parser.parse_args()

    # 初始化变量 script_dir
    script_dir = Path(__file__).resolve().parent
    # 初始化变量 pyproject_path
    pyproject_path = Path(args.pyproject) if args.pyproject else script_dir / "pyproject.toml"
    # 初始化变量 output_path
    output_path = Path(args.output) if args.output else script_dir / "requirements.txt"
    # 初始化变量 extras
    extras = parse_extras(args.extras)

    exit_code =

# 条件判断：处理业务逻辑
 generate_requirements(pyproject_path, output_path, extras)
    sys.exit(exit_code)


# 条件判断: 检查 __name__ == "__main__"
if __name__ == "__main__":
    main()
