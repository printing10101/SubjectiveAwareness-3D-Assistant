"""分析请求的数据验证模型.

定义案件分析 API 的请求和响应数据结构，
实现严格的输入验证、内容安全检查和恶意内容检测。
"""

# 导入模块: re
import re

# 导入模块: from pydantic
from pydantic import BaseModel, ConfigDict, Field, field_validator

# 导入模块: from app.config
from app.config import AnalysisConfig
# 导入模块: from app.models.analysis
from app.models.analysis import AnalysisMode


# 危险字符模式 - XSS 攻击
_XSS_PATTERNS: list[tuple[str, str]] = [
    (r"<script[^>]*>.*?</script>", "包含script标签"),
    (r"javascript\s*:", "包含javascript:协议"),
    (r"onerror\s*=", "包含onerror事件处理器"),
    (r"onload\s*=", "包含onload事件处理器"),
    (r"onclick\s*=", "包含onclick事件处理器"),
    (r"onmouseover\s*=", "包含onmouseover事件处理器"),
    (r"<iframe[^>]*>", "包含iframe标签"),
    (r"<embed[^>]*>", "包含embed标签"),
    (r"<object[^>]*>", "包含object标签"),
    (r"<svg[^>]*>.*?</svg>", "包含svg标签"),
    (r"expression\s*\(", "包含CSS表达式"),
    (r"vbscript\s*:", "包含vbscript:协议"),
    (r"data\s*:\s*text/html", "包含data:text/html协议"),
    (r"document\.cookie", "包含document.cookie引用"),
    (r"alert\s*\(", "包含alert函数调用"),
    (r"eval\s*\(", "包含eval函数调用"),
]

# 危险字符模式 - SQL 注入
_SQL_INJECTION_PATTERNS: list[tuple[str, str]] = [
    (r"'.*?(?:OR|or|Or|oR).*?=.*?(?:--|#)", "包含SQL注入语句（OR条件绕过）"),
    (r"'.*?(?:UNION|union|Union).*?SELECT", "包含SQL注入语句（UNION查询）"),
    (r"DROP\s+TABLE", "包含DROP TABLE语句"),
    (r"DELETE\s+FROM", "包含DELETE FROM语句"),
    (r"UPDATE\s+.*?\s+SET", "包含UPDATE语句"),
    (r"INSERT\s+INTO", "包含INSERT INTO语句"),
    (r"CREATE\s+TABLE", "包含CREATE TABLE语句"),
    (r"ALTER\s+TABLE", "包含ALTER TABLE语句"),
    (r"EXEC\s*\(", "包含EXEC函数调用"),
    (r"xp_cmdshell", "包含xp_cmdshell扩展"),
    (r"pg_sleep\s*\(", "包含pg_sleep延时函数"),
    (r"WAITFOR\s+DELAY", "包含WAITFOR延时语句"),
    (r"SELECT\s+.*?\s+FROM", "包含SELECT FROM查询语句"),
    (r"'\s*OR\s*'1'\s*='1", "包含SQL恒真条件"),
    (r"'\s*OR\s*1\s*=\s*1", "包含SQL恒真条件"),
]

# 危险字符模式 - 路径遍历
_PATH_TRAVERSAL_PATTERNS: list[tuple[str, str]] = [
    (r"\.\./", "包含路径遍历"),
    (r"\.\.\\", "包含路径遍历"),
    (r"~[\\/]", "包含用户目录引用"),
]

# 需要清洗的可疑但非恶意字符映射
_SANITIZE_MAP: dict[str, str] = {
    "\x00": "",  # 空字节
    "\r": " ",   # 回车符
}


def _sanitize_text(text: str) -> str:
    """对输入文本进行安全清洗.

    移除或替换可疑但非恶意的字符，保留合法的中文法律文本字符。

    Args:
        text: 原始输入文本

    Returns:
        清洗后的安全文本
    """
    # 循环遍历：处理业务逻辑
    for char, replacement in _SANITIZE_MAP.items():
        # 初始化变量 text
        text = text.replace(char, replacement)
    # 返回处理结果
    return text


def _check_patterns(
    # 函数 _check_patterns 的初始化逻辑
    text: str,


    # 执行 _check_patterns 函数的核心逻辑
    patterns: list[tuple[str, str]],
    category: str,
) -> list[str]:
    """检查文本是否匹配危险模式列表.

    Args:
        text: 待检查文本
        patterns: (正则表达式, 违规描述) 元组列表
        category: 安全类别名称
        category: 违规类别名称

    Returns:
        违规描述列表，无违规时返回空列表
    """
    violation    # 循环遍历：处理业务逻辑
s: list[str] = []
    # 遍历: for pattern, description in patterns:
    for pattern, description in patterns:
        # 条件判断：处理业务逻辑
        if re.search(pattern, text, re.IGNORECASE):
            violations.append(f"[{category}] {description}")
    # 返回处理结果
    return violations


# 定义 AnalyzeRequest 类
class AnalyzeRequest(BaseModel):
    """分析请求模型，含严格输入验证.

    Attributes:
        case_text: 案件事实文本（长度限制10-50000字符，含安全检测）
        mode: 分析模式（auto/single/multi）
        case_id: 关联案件ID（可选）
    """

    # 启用 use_enum_values + validate_default，枚举字段以字符串形式存储，
    # 既保留类型校验，又避免 .mode == "auto" 这类字符串断言失败。
    # validate_default 让默认值（AnalysisMode.auto）也走序列化路径。
    model_config = ConfigDict(use_enum_values=True, validate_default=True)

    case_text: str = Field(
        ...,
        # 初始化变量 min_length
        min_length=AnalysisConfig.MIN_CASE_TEXT_LENGTH,
        # 初始化变量 max_length
        max_length=AnalysisConfig.MAX_CASE_TEXT_LENGTH,
    )
    mode: AnalysisMode = Field(default=AnalysisMode.auto)
    case_id: int | None = Field(default=None, ge=1)

    # 应用装饰器: field_validator
    @field_validator("case_text")
    # 应用装饰器: classmethod
    @classmethod
    def validate_case_text_safety(cls, v: str) -> str:
        """验证案件文本安全性.

        检测并阻止包含 XSS、SQL注入、路径遍历等潜在危险字符的输入。

        Args:
            v: 原始案件文本

        Returns:
            清洗后的安全文本

        Raises:
            ValueError: 包含高危恶意内容时抛出详细错误
        """
   
        # 条件判断：处理业务逻辑
     text = v.strip()

        # 条件判断: 检查 len(text) < AnalysisConfig.MIN_CASE_TEXT
        if len(text) < AnalysisConfig.MIN_CASE_TEXT_LENGTH:
            msg = (
                f"案件事实文本不能少于"
                f"{AnalysisConfig.MIN_CASE_TEXT_LENGTH}个字符，"
                f"当前{len(text)}个字符"
            )
            # 抛出异常，处理错误情况
            raise ValueError(msg)

        all_violations: list[str] = []
        all_violations.extend(
            _check_patterns(text, _XSS_PATTERNS, "XSS")
        )
        all_violations.extend(
            _check_patterns(
                text, _SQL_INJECTION_PATTERNS, "SQL注入"
            )
        )
        all_violations.extend(
            _check_patterns(
                text, _PATH_TRAVER
        # 条件判断：处理业务逻辑
SAL_PATTERNS, "路径遍历"
            )
        )

        # 条件判断: 检查 all_violations
        if all_violations:
            # 初始化变量 detail
            detail = "; ".join(all_violations)
            msg = f"输入内容包含安全风险：{detail}"
            # 抛出异常，处理错误情况
            raise ValueError(msg)

        # 返回处理结果
        return _sanitize_text(text)
