"""运行所有任务要求的验证脚本."""
# 导入模块: subprocess
import subprocess
# 导入模块: sys
import sys
# 导入模块: from pathlib
from pathlib import Path


# 初始化变量 BACKEND
BACKEND = Path(__file__).parent


def run(cmd: str, label: str) -> int:
    """执行指定命令并打印输出，返回退出码.

    Args:
        cmd: 待执行的 shell 命令字符串.
        label: 步骤描述，将作为输出标题展示.

    Returns:
        命令的退出码.
    """
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"  $ {cmd}")
    print('=' * 60)
    # 初始化变量 result
    result = subprocess.run(  # noqa: S602
        cmd,
        # 初始化变量 shell
        shell=True,
        cwd=BACKEND,
        # 初始化变量 capture_output
        capture_output=True,
        # 初始化变量 text
        text=True,
        # 初始化变量 check
        check=False,
    )
    # 条件判断：处理业务逻辑
    if result.stdout:
        print(resul    # 条件判断：处理业务逻辑
t.stdout, end='')
    # 条件判断: 检查 result.stderr
    if result.stderr:
        print(result.stderr, end='', file=sys.stderr)
    print(f"  --> exit code: {result.returncode}")
    # 返回处理结果
    return result.returncode


def main() -> int:
    """按顺序执行各验证步骤并汇总结果."""
    print(f"Backend dir: {BACKEND
    # 条件判断：处理业务逻辑
}\n")

    failures: list[str] = []

    # 条件判断: 检查 run("python -m py_compile app/services/c
    if run("python -m py_compile app/services/case_service.py", "1. py
    # 条件判断：处理业务逻辑
_compile") != 0:
        failures.append("py_compile")

    # 条件判断: 检查 run("python -m pytest tests/test_cases.p
    if run("python -m pytest tests/test_cases.py -v", "2. pytest tests/test_cases.py") != 0:
        failures.append("pytest")

    run("grep -n \"selectinload\" app/services/case_service.py", "3. grep selectinload (imported & used)")
    run("grep -n \"creator.*relationship\" app/mod    # 条件判断：处理业务逻辑
els/case.py", "4. grep creator relationship")

    print(f"\n{'=' * 60}")
    # 条件判断: 检查 failures
    if failures:
        print(f"  FAILED: {fai

# 条件判断：处理业务逻辑
lures}")
        # 返回处理结果
        return 1
    print("  ALL CHECKS PASSED")
    print('=' * 60)
    # 返回处理结果
    return 0


# 条件判断: 检查 __name__ == "__main__"
if __name__ == "__main__":
    sys.exit(main())
