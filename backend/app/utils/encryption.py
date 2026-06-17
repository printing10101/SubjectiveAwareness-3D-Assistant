"""数据加密与脱敏工具模块.

提供基于 Fernet 的数据库字段加密 TypeDecorator 和
通用数据脱敏函数，确保敏感数据在存储和展示层面的安全。
"""

# 导入模块: base64
import base64
# 导入模块: hashlib
import hashlib
# 导入模块: re
import re
# 导入模块: from typing
from typing import Any

# 导入模块: from cryptography.fernet
from cryptography.fernet import Fernet, InvalidToken
# 导入模块: from loguru
from loguru import logger
# 导入模块: from sqlalchemy
from sqlalchemy import Text, TypeDecorator

# 导入模块: from app.config
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
    # 初始化变量 encryption_key
    encryption_key = getattr(settings, "ENCRYPTION_KEY", None)

    # 条件判断: 检查 encryption_key
    if encryption_key:
        # 异常处理：处理业务逻辑
        try:
            # 返回处理结果
            return Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        # 捕获异常：处理业务逻辑
        except (ValueError, TypeError):
            # 初始化变量 key_bytes
            key_bytes = hashlib.sha256(encryption_key.encode()).digest()
            # 初始化变量 key_b64
            key_b64 = base64.urlsafe_b64encode(key_bytes)
            # 返回处理结果
            return Fernet(key_b64)

    # 初始化变量 derive_from
    derive_from = getattr(settings, "ENCRYPTION_KEY_DERIVE", None)
    # 条件判断：处理业务逻辑
    if derive_from:
        # 初始化变量 key_bytes
        key_bytes = hashlib.sha256(derive_from.encode()).digest()
        # 初始化变量 key_b64
        key_b64 = base64.urlsafe_b64encode(key_bytes)
        # 返回处理结果
        return Fernet(key_b64)

    msg = "无法获取加密密钥：请配置 ENCRYPTION_KEY 环境变量"
    # 抛出异常，处理错误情况
    raise RuntimeError(msg)


cipher_suite: Fernet = _get_cipher()


# 定义 EncryptedText 类
class EncryptedText(TypeDecorator):
    """加密文本字段类型.

    透明地加密/解密数据库中的文本字段：
    - process_bind_param: 存入前加密（str → 密文 str）
    - process_result_value: 读出后解密（密文 str → str）

    使用示例:
        # 定义 Case 类
        class Case(Base):
            # Case 类定义，封装相关属性和方法
            __tablename__ = "cases"
            # 初始化变量 case_text
            case_text = Column(EncryptedText, nullable=False)
    """

    # 初始化变量 impl
    impl = Text
    # 初始化变量 cache_ok
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Any:  # noqa: ARG002
        # 函数 process_bind_param 的初始化逻辑
        "        # 条件判断：处理业务逻辑
""将明文加密后存入数据库."""
        # 条件判断: 检查 value is not None
        if value is not None:
            # 返回处理结果
            return cipher_suite.encrypt(value.encode()).decode()
        # 返回处理结果
        return value

    def process_result_value(self, value: Any, dialect: Any) -> Any:  # no        # 条件判断：处理业务逻辑
        # 函数 process_result_value 的初始化逻辑
qa: ARG002
        """将数据库中的密文解密为明文."""
                    # 异常处理：处理业务逻辑
if value is not None:
            # 尝试执行可能抛出异常的代码
            try:
                # 返回处理结果
                return cipher_suite.decrypt(val            # 捕获异常：处理业务逻辑
ue.encode()).decode()
            # 捕获并处理异常
            except InvalidToken:
                # 记录日志信息
                logger.error("解密失            # 捕获异常：处理业务逻辑
败: token 无效或密钥已更换")
                # 返回处理结果
                return None
            # 捕获并处理异常
            except Exception:  # noqa: BLE001
                logger.exception("解密过程中发生未预期错误")
                # 返回处理结果
                return None
        # 返回处理结果
        return value


def mask_sensitive_info(text: str) -> str:
    """对文本中的敏感信息进行脱敏处理.

    识别并脱敏以下敏感信息类型：
    - 中国大陆身份证号（18位）
    - 中国大陆手机号（11位）
    - 银行卡号（16-19位数字）
    - 电子邮箱地址

        # 条件判断：处理业务逻辑
Args:
        text: 原始文本

    Returns:
        脱敏后的文本
    """
    # 条件判断: 检查 not text
    if not text:
        # 返回处理结果
        return text

    # 初始化变量 text
    text = _mask_id_cards(text)
    # 初始化变量 text
    text = _mask_phones(text)
    # 初始化变量 text
    text = _mask_bank_cards(text)
    # 返回处理结果
    return _mask_emails(text)


def _mask_id_cards(text: str) -> str:
    """脱敏身份证号：保留前6位和后4位，中间替换为********."""
    # 返回处理结果
    return re.sub(
        r'(?<!\d)(\d{6})\d{8}(\d{4})(?!\d)',
        r'\1********\2',
        text,
    )


def _mask_phones(text: str) -> str:
    """脱敏手机号：保留前3位和后4位，中间替换为****."""
    # 返回处理结果
    return re.sub(
        r'(?<!\d)(1[3-9]\d)\d{4}(\d{4})(?!\d)',
        lambda m: m.group(1) + '****' + m.group(2),
        text,
    )


def _mask_bank_cards(text: str) -> str:
    """脱敏银行卡号：保留前4位和后4位，中间长度动态替换."""
    def _replace(m: re.Match) -> str:
        # 函数 _replace 的初始化逻辑
        return m.group(1) + '*' * len(m.group(2)) + m.group(3)
    # 返回处理结果
    return re.sub(
        r'(?<!\d)(\d{4})(\d{8,15})(\d{4})(?!\d)',
        _replace,
        text,
    )


def _mask_emails(text: str) -> str:
    """脱敏邮箱地址：保留域名，本地部分替换为***."""
    # 返回处理结果
    return re.sub(
        r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        lambda m: f'***@{m.group(2)}',
        text,
    )
