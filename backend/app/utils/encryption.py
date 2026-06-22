"""数据加密与脱敏工具模块.

提供基于 Fernet 的数据库字段加密 TypeDecorator 和
通用数据脱敏函数，确保敏感数据在存储和展示层面的安全。
"""

import base64
import hashlib
import re
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from loguru import logger
from sqlalchemy import Text, TypeDecorator

from app.config import settings


def _get_cipher() -> Fernet:
    """获取 Fernet 加密套件实例.

    密钥来源优先级：
    1. 环境变量 ENCRYPTION_KEY（推荐）
    2. 由 ENCRYPTION_KEY_DERIVE 派生（使用 SHA-256 哈希派生）

    所有密钥在使用前已通过 Settings._validate_encryption_key() 验证，
    确保长度和来源符合安全要求。

    Returns:
        Fernet 加密套件实例

    Raises:
        RuntimeError: 无法获取有效加密密钥
    """
    encryption_key = getattr(settings, "ENCRYPTION_KEY", None)

    if encryption_key:
        try:
            return Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        except (ValueError, TypeError):
            key_bytes = hashlib.sha256(encryption_key.encode()).digest()
            key_b64 = base64.urlsafe_b64encode(key_bytes)
            return Fernet(key_b64)

    derive_from = getattr(settings, "ENCRYPTION_KEY_DERIVE", None)
    if derive_from:
        key_bytes = hashlib.sha256(derive_from.encode()).digest()
        key_b64 = base64.urlsafe_b64encode(key_bytes)
        return Fernet(key_b64)

    msg = "无法获取加密密钥：请配置 ENCRYPTION_KEY 环境变量"
    raise RuntimeError(msg)


cipher_suite: Fernet = _get_cipher()


class EncryptedText(TypeDecorator):
    """加密文本字段类型.

    透明地加密/解密数据库中的文本字段：
    - process_bind_param: 存入前加密（str → 密文 str）
    - process_result_value: 读出后解密（密文 str → str）

    使用示例:
        class Case(Base):
            __tablename__ = "cases"
            case_text = Column(EncryptedText, nullable=False)
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Any:  # noqa: ARG002
        """将明文加密后存入数据库."""
        if value is not None:
            return cipher_suite.encrypt(value.encode()).decode()
        return value

    def process_result_value(self, value: Any, dialect: Any) -> Any:  # noqa: ARG002
        """将数据库中的密文解密为明文."""
        if value is not None:
            try:
                return cipher_suite.decrypt(value.encode()).decode()
            except InvalidToken:
                logger.error("解密失败: token 无效或密钥已更换")
                return None
            except Exception:  # noqa: BLE001
                logger.exception("解密过程中发生未预期错误")
                return None
        return value


def mask_sensitive_info(text: str) -> str:
    """对文本中的敏感信息进行脱敏处理.

    识别并脱敏以下敏感信息类型：
    - 中国大陆身份证号（18位）
    - 中国大陆手机号（11位）
    - 银行卡号（16-19位数字）
    - 电子邮箱地址

    Args:
        text: 原始文本

    Returns:
        脱敏后的文本
    """
    if not text:
        return text

    text = _mask_id_cards(text)
    text = _mask_phones(text)
    text = _mask_bank_cards(text)
    return _mask_emails(text)


def _mask_id_cards(text: str) -> str:
    """脱敏身份证号：保留前6位和后4位，中间替换为********."""
    return re.sub(
        r'(?<!\d)(\d{6})\d{8}(\d{4})(?!\d)',
        r'\1********\2',
        text,
    )


def _mask_phones(text: str) -> str:
    """脱敏手机号：保留前3位和后4位，中间替换为****."""
    return re.sub(
        r'(?<!\d)(1[3-9]\d)\d{4}(\d{4})(?!\d)',
        lambda m: m.group(1) + '****' + m.group(2),
        text,
    )


def _mask_bank_cards(text: str) -> str:
    """脱敏银行卡号：保留前4位和后4位，中间长度动态替换."""
    def _replace(m: re.Match) -> str:
        return m.group(1) + '*' * len(m.group(2)) + m.group(3)
    return re.sub(
        r'(?<!\d)(\d{4})(\d{8,15})(\d{4})(?!\d)',
        _replace,
        text,
    )


def _mask_emails(text: str) -> str:
    """脱敏邮箱地址：保留域名，本地部分替换为***."""
    return re.sub(
        r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        lambda m: f'***@{m.group(2)}',
        text,
    )
