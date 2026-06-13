"""运行所有任务要求的验证脚本."""
import subprocess
import sys
from pathlib import Path


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
    result = subprocess.run(  # noqa: S602
        cmd,
        shell=True,
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout, end='')
    if result.stderr:
        print(result.stderr, end='', file=sys.stderr)
    print(f"  --> exit code: {result.returncode}")
    return result.returncode


def main() -> int:
    """按顺序执行各验证步骤并汇总结果."""
    print(f"Backend dir: {BACKEND}\n")

    failures: list[str] = []

    if run("python -m py_compile app/services/case_service.py", "1. py_compile") != 0:
        failures.append("py_compile")

    if run("python -m pytest tests/test_cases.py -v", "2. pytest tests/test_cases.py") != 0:
        failures.append("pytest")

    run("grep -n \"selectinload\" app/services/case_service.py", "3. grep selectinload (imported & used)")
    run("grep -n \"creator.*relationship\" app/models/case.py", "4. grep creator relationship")

    print(f"\n{'=' * 60}")
    if failures:
        print(f"  FAILED: {failures}")
        return 1
    print("  ALL CHECKS PASSED")
    print('=' * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
