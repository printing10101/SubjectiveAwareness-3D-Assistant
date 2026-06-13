"""用户相关的 Pydantic 数据验证模型.

定义用户创建、更新和响应的数据结构，
实现角色枚举约束和用户名格式验证。
"""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user import UserRole


# 用户名格式正则：仅允许字母、数字、下划线，长度3-100
_USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]{3,100}$")
_MIN_PASSWORD_LENGTH = 10
_MIN_PASSWORD_CATEGORIES = 3


class UserBase(BaseModel):
    """用户基础模型."""

    # 启用 use_enum_values + validate_default，让 role 以字符串形式存储，
    # 且默认值 UserRole.user 也被序列化为字符串。
    model_config = ConfigDict(use_enum_values=True, validate_default=True)

    username: str
    role: UserRole = UserRole.user


class UserCreate(UserBase):
    """创建用户请求模型，含字段级验证.

    Attributes:
        username: 用户名（字母、数字、下划线，3-100字符）
        password: 明文密码（创建时必填）
        role: 用户角色（默认user）
    """

    # 注意：不在此处声明 min_length。Pydantic 内置的 min_length 校验会先于
    # 我们的 field_validator 触发，并抛出英文错误信息；将长度检查统一
    # 交给 validate_password 可保证中文错误信息能被测试断言。
    password: str = Field(..., max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """验证用户名格式.

        用户名只能包含字母（大小写）、数字和下划线，
        长度限制在3到100个字符之间。

        Args:
            v: 原始用户名字符串

        Returns:
            str: 去除首尾空格后的用户名

        Raises:
            ValueError: 用户名格式不符合要求
        """
        if not v or not v.strip():
            msg = "用户名不能为空"
            raise ValueError(msg)
        username = v.strip()
        if not _USERNAME_PATTERN.match(username):
            msg = "用户名只能包含字母、数字和下划线，且长度为3-100个字符。例如：user_admin_123"
            raise ValueError(msg)
        return username

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """验证密码复杂度.

        密码必须同时满足以下两项要求：
        1. 长度至少为 10 个字符；
        2. 至少包含以下四类字符中的三类：
           - 小写字母（a-z）
           - 大写字母（A-Z）
           - 数字（0-9）
           - 特殊字符（如!@#$%^&*()_+-=等）
        """
        if len(v) < _MIN_PASSWORD_LENGTH:
            msg = (
                f"密码长度至少为 {_MIN_PASSWORD_LENGTH} 个字符，"
                "建议使用 10 个以上字符的强密码。"
            )
            raise ValueError(msg)
        categories = 0
        if re.search(r"[a-z]", v):
            categories += 1
        if re.search(r"[A-Z]", v):
            categories += 1
        if re.search(r"\d", v):
            categories += 1
        if re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", v):
            categories += 1
        if categories < _MIN_PASSWORD_CATEGORIES:
            msg = (
                f"密码必须包含以下四类字符中的至少 {_MIN_PASSWORD_CATEGORIES} 类："
                "小写字母(a-z)、大写字母(A-Z)、数字(0-9)、"
                "特殊字符(如!@#$%^&*()_+-=等)。"
                f"当前密码仅包含 {categories} 类字符，请重新设置。"
            )
            raise ValueError(msg)
        return v


class UserUpdate(BaseModel):
    """更新用户请求模型，所有字段可选."""

    username: str | None = None
    password: str | None = Field(default=None, min_length=10, max_length=128)
    role: UserRole | None = None
    is_active: bool | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        """验证用户名格式（更新时可选）.

        Args:
            v: 用户名字符串或None

        Returns:
            str | None: 验证后的用户名或None

        Raises:
            ValueError: 用户名格式不符合要求
        """
        if v is not None:
            if not v.strip():
                msg = "用户名不能为空"
                raise ValueError(msg)
            username = v.strip()
            if not _USERNAME_PATTERN.match(username):
                msg = "用户名只能包含字母、数字和下划线，且长度为3-100个字符。例如：user_admin_123"
                raise ValueError(msg)
            return username
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        """验证密码复杂度（更新时可选）.

        当 password 为 None 时跳过验证（表示不更新密码）；
        否则要求与 UserCreate 一致：长度至少 10 个字符，
        且至少包含以下四类字符中的三类：
        小写字母(a-z)、大写字母(A-Z)、数字(0-9)、特殊字符。
        """
        if v is None:
            return v
        if len(v) < _MIN_PASSWORD_LENGTH:
            msg = (
                f"密码长度至少为 {_MIN_PASSWORD_LENGTH} 个字符，"
                "建议使用 10 个以上字符的强密码。"
            )
            raise ValueError(msg)
        categories = 0
        if re.search(r"[a-z]", v):
            categories += 1
        if re.search(r"[A-Z]", v):
            categories += 1
        if re.search(r"\d", v):
            categories += 1
        if re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", v):
            categories += 1
        if categories < _MIN_PASSWORD_CATEGORIES:
            msg = (
                f"密码必须包含以下四类字符中的至少 {_MIN_PASSWORD_CATEGORIES} 类："
                "小写字母(a-z)、大写字母(A-Z)、数字(0-9)、"
                "特殊字符(如!@#$%^&*()_+-=等)。"
                f"当前密码仅包含 {categories} 类字符，请重新设置。"
            )
            raise ValueError(msg)
        return v


class UserResponse(BaseModel):
    """用户响应模型，用于API返回."""

    id: int
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
