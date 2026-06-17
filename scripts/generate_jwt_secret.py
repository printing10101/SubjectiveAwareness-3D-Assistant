#!/usr/bin/env python3
"""
JWT 密钥生成脚本

生成符合密码学安全要求的随机 JWT 密钥（至少 256 位 / 32 字节）。
使用 Python secrets 模块，确保密钥具有足够的熵值以抵抗暴力攻击。

使用方法:
    python scripts/generate_jwt_secret.py
"""

import secrets
import argparse
import sys


def generate_jwt_secret(key_length: int = 32) -> str:
    """生成密码学安全的随机密钥

    Args:
        key_length: 密钥字节数，默认 32（256 位）

    Returns:
        十六进制编码的密钥字符串
    """
    if key_length < 32:
        print("错误: 密钥长度不能少于 32 字节（256 位）", file=sys.stderr)
        sys.exit(1)

    return secrets.token_hex(key_length)


def main():
    parser = argparse.ArgumentParser(
        description="生成安全的 JWT 密钥（至少 256 位）",
        epilog="示例:\n"
        "  python scripts/generate_jwt_secret.py\n"
        "  python scripts/generate_jwt_secret.py --length 48\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--length",
        type=int,
        default=32,
        help="密钥字节数（默认 32，即 256 位）",
        metavar="BYTES",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="将密钥复制到剪贴板（需要 pyperclip 库）",
    )
    parser.add_argument(
        "--env-format",
        action="store_true",
        help="以 .env 文件格式输出（JWT_SECRET_KEY=...）",
    )

    args = parser.parse_args()

    if args.length < 32:
        print("错误: 密钥长度不能少于 32 字节（256 位）", file=sys.stderr)
        sys.exit(1)

    secret = generate_jwt_secret(args.length)

    if args.env_format:
        print(f"JWT_SECRET_KEY={secret}")
    else:
        print(secret)

    # 可选：复制到剪贴板
    if args.copy:
        try:
            import pyperclip

            pyperclip.copy(secret)
            print("密钥已复制到剪贴板！", file=sys.stderr)
        except ImportError:
            print(
                "警告: 未安装 pyperclip 库，无法复制到剪贴板。\n"
                "安装命令: pip install pyperclip",
                file=sys.stderr,
            )

    # 输出密钥信息
    print("\n密钥信息:", file=sys.stderr)
    print(f"  字节数: {args.length}", file=sys.stderr)
    print(f"  位数: {args.length * 8}", file=sys.stderr)
    print(f"  长度: {len(secret)} 字符", file=sys.stderr)
    print("\n安全提示:", file=sys.stderr)
    print("  - 请勿将密钥提交到版本控制系统", file=sys.stderr)
    print("  - 请将密钥添加到 .env 文件或环境变量中", file=sys.stderr)
    print("  - 生产环境建议使用至少 32 字节（256 位）的密钥", file=sys.stderr)


if __name__ == "__main__":
    main()
