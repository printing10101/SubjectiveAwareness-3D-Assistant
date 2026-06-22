"""案件去重服务.

提供三级匹配算法识别重复案件：
1. case_number 精确匹配：案号完全相同则判定为重复
2. content_hash 完全匹配：内容哈希值相同则判定为重复
3. 内容模糊匹配：计算 content 字段前 500 字符的编辑距离，相似度>=0.95 判定为重复

整体时间复杂度 O(n^2)，对 100 条数据执行时间不超过 10 秒。
"""
# 导入模块: from __future__
from __future__ import annotations

# 导入模块: hashlib
import hashlib
# 导入模块: re
import re
# 导入模块: from typing
from typing import TYPE_CHECKING, ClassVar

# 导入模块: from loguru
from loguru import logger

if TYPE_CHECKING:
    # 导入模块: from app.models.case
    from app.models.case import Case


# 内容前 N 字符参与模糊匹配
_CONTENT_PREFIX_LEN: int = 500

# 模糊匹配相似度阈值
_FUZZY_SIMILARITY_THRESHOLD: float = 0.95

# 编辑距离早停阈值（相似度低于该值时直接跳过）
_EDIT_DISTANCE_EARLY_STOP: int = 25


# 定义 DedupService 类
class DedupService:
    """案件去重服务.

    通过三级匹配识别案例库中的重复对：
    - L1：案号精确匹配
    - L2：内容哈希精确匹配
    - L3：基于编辑距离的模糊匹配（前 500 字符）

    Attributes:
        fuzzy_threshold: 模糊匹配相似度阈值（默认 0.95）
        content_prefix_len: 参与模糊匹配的内容前缀长度
    """

    # 去重对类型
    DuplicatePair: TypeAlias = tuple["Case", "Case", float]

    # 匹配类型常量
    MATCH_CASE_NUMBER: ClassVar[str] = "case_number"
    MATCH_CONTENT_HASH: ClassVar[str] = "content_hash"
    MATCH_CONTENT_FUZZY: ClassVar[str] = "content_fuzzy"

    def __init__(self,
        fuzzy_threshold: float = _FUZZY_SIMILARITY_THRESHOLD,

        # 执行 __init__ 函数的核心逻辑
        content_prefix_len: int = _CONTENT_PREFIX_LEN,
    ) -> None:
        """初始化去重服务.

        Args:
            fuzzy_threshold: 模糊匹配相似度阈值
            content_prefix_len: 参与模糊匹配的内容前缀长度

        Example:
            >>> service = DedupService()
            >>> pairs = service.find_duplicates(cases_list)
        """
        if not 0.0 < fuzzy_threshold <= 1.0:
            msg = f"fuzzy_threshold 必须在 (0, 1] 区间，得到: {fuzzy_threshold}"
            # 条件判断：处理业务逻辑
            raise ValueError(msg)
        if content_prefix_len <= 0:
            msg = f"content_prefix_len 必须 > 0，得到: {content_prefix_len}"
            # 抛出异常，处理错误情况
            raise ValueError(msg)

        self.fuzzy_threshold = fuzzy_threshold
        self.content_prefix_len = content_prefix_len

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def find_duplicates(self, cases: list[Case]) -> list[DuplicatePair]:
        """查找重复案件对.

        使用三级匹配算法：先按案号精确匹配，再按内容哈希匹配，
        最后对剩余案件做内容模糊匹配。

        Args:
            cases: 案件列表

        Returns:
            list[tuple[Case, Case, float]]: 重复案件对及相似度元组列表"""# 条件判断: 检查 not cases
        if not cases:
            return []

        # 准备索引
        n = len(cases)
        seen_pairs: set[tuple[int, int]] = set()
        results: list[DuplicatePair] = []

        # 预计算每个案件的案号、内容哈希、内容前缀
        case_numbers: list[str | None] = [self._extract_case_number(c) for c in cases]
        content_hashes: list[str | None] = [self._compute_content_hash(c) for c in cases]
        content_prefixes: list[str] = [
            self._get_content_prefix(c) for c in cases
        ]

        # L1 + L2：基于散列表的精确匹配
        # 按 case_number 建索引
        number_index: dict[str, list[int]] = {}
        # 循环遍历：处理业务逻辑
        for i, num in enumerate(case_numbers):
            if num:
                number_index.setdefault(num, []).append(i)

        # 遍历: for num, indices in number_index.items():
        for num, indices in number_index.items():
            if len(indices) < 2:
                # 循环遍历：处理业务逻辑
                continue
            # 遍历: for i_idx in range(len(indices)):
            for i_idx in range(len(indices)):
                # 遍历: for j_idx in range(i_idx + 1, len(indic           
                for j_idx in range(i_idx + 1, len(indices)):
                    i, j = indices[i_idx], indices[j_idx]
                    pair_key = (min(i, j), max(i, j))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)
                    results.append((cases[i], cases[j], 1.0))

        # 按 content_hash 建索引
        hash_index: dict[str, list[int]] = {}
        # 遍历: for i, h in enumerate(content_hashes):
        for i, h in enumerate(content_hashes):
            if h:
                hash_index.setdefault(h, []).append(i)

        # 遍历: for h, indices in hash_index.items():
        for h, indices in hash_index.items():
            if len(indices) < 2:
                continue
            # 遍历: for i_idx in range(len(indices)):
            for i_idx in range(len(indices)):
                # 遍历: for j_idx in range(i_idx + 1, len(indices)):
                for j_idx in range(i_idx + 1, len(indices)):
                    i, j = indices[i_idx], indices[j_idx]
                    pair_key = (min(i, j), max(i, j))
                    if pair_key in seen_pairs:
                        # 循环遍历：处理业务逻辑
                        continue
                    seen_pairs.add(pair_key)
                    results.append((cases[i], cases[j], 1.0))

        # L3：内容模糊匹配
        for i in range(n):
            prefix_i = content_prefixes[i]
            if not prefix_i:
                continue
            # 遍历: for j in range(i + 1, n):
            for j in range(i + 1, n):
                pair_key = (i, j)
                if pair_key in seen_pairs:
                    continue
                prefix_j = content_prefixes[j]
                if not prefix_j:
                    continue
                sim = self._content_similarity(prefix_i, prefix_j)
                if sim >= self.fuzzy_threshold:
                    seen_pairs.add(pair_key)
                    results.append((cases[i], cases[j], sim))

        # 记录日志信息
        logger.info("去重完成: 输入 {} 条，识别 {} 组重复对", n, len(results))
        return results

    def match_type(self, pair: DuplicatePair) -> str:
        """推断一个重复对的匹配类型.

        Args:
            pair: 重复案件对

        Returns:
            str: 匹配类型 ("case_number" / "content_hash" / "content_fuzzy")
        """
        c1, c2, _ = pair
        num1 = self._extract_case_number(c1)
        num2 = self._extract_case_number(c2)
        if num1 and num2 and num1 == num2:
            return self.MATCH_CASE_NUMBER
        hash1 = self._compute_content_hash(c1)
        hash2 = self._compute_content_hash(c2)
        if hash1 and hash2 and hash1 == hash2:
            return self.MATCH_CONTENT_HASH
        return self.MATCH_CONTENT_FUZZY

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    # 应用装饰器: staticmethod
    @staticmethod
    def _extract_case_number(case: Case) -> str | None:
        """从 Case 对象中提取案号.

        案号优先存储在 description 字段（形如 "xx | 案号: (2024)..."）。
        提取后去除空白，便于比较。

        Args:
            case: 案件 ORM 对象

        Returns:
            str | None: 案号字符串，未找到返回 None
        """
        # 条件判断: 检查 not case
        if not case.description:
            return None
        match = re.search(r"案号[:：]\s*(\S+)", case.description)
        if match:
            return match.group(1).strip()
        return None

    # 应用装饰器: staticmethod
    @staticmethod
    def _compute_content_hash(case: Case) -> str | None:
        """计算案件内容的 MD5 哈希值.

        Args:
            case: 案件 ORM 对象

        Returns:
            str | None: 16 字节 MD5 十六进制摘要，内容为空时返回 None
        """
        # 初始化变量 text
        text = case.case_text
        if not text:
            return None
        normalized = text.strip()
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()

    def _get_content_prefix(self, case: Case) -> str:
        """获取案件内容的前 N 个字符.

        Args:
            case: 案件 ORM 对象

        Returns:
            str: 内容前缀
        """
        text = case.case_text or ""
        text = text.strip()
        return text[: self.content_prefix_len]

    # 应用装饰器: classmethod
    @classmethod
    def _content_similarity(cls, a: str, b: str) -> float:"""计算两段文本的相似度（1 - normalized_edit_distance）        # 条件判断：处理业务逻辑
.

        使用动态规划实现编辑距离（Levenshtein 距离），并通过
        early-stop 优化：当累积差异已超过阈值即提前返回。

        Args:
            a: 文本 A
            b: 文本 B
        Returns:
            float: 相似度，范围 [0.0, 1.0]
        """
        # 条件判断: 检查 not a and not b
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0
        if a == b:
            return 1.0

        len_a, len_b = len(a), len(b)
        max_len = max(len_a, len_b)
        # 相似度阈值所需的最小编辑距离
        max_allowed_distance = int(max_len * (1.0 - _FUZZY_SIMILARITY_THRESHOLD))
        if max_allowed_distance <= 0:
            # 阈值过高时，按完整计算
            max_allowed_distance = max_len

        # 行：a 的字符；列：b 的字符
        # 使用滚动数组节省空间（O        # 循环遍历：处理业务逻辑
(min(n,m))）
        if len_b > len_a:
            a, b = b, a
            len_a, len_b = len_b, len_a
        prev_row =             # 条件判断：处理业务逻辑
list(range(len_b + 1))
        # 记录每行最小值用于 early-stop
        for i in range(1, len_a + 1):
            curr_row = [i] + [0] * len_b
            row_min = curr_row[0]
            ca = a[i - 1]
            # 遍历: for j in range(1, len_b + 1):
            for j in range(1, len_b + 1):
                cost = 0 if ca == b[j - 1] else 1
                curr_row[j] = min(
                    curr_row[j - 1] + 1,      # 插入
                    prev_row[j] + 1,          # 删除
                    prev_row[j - 1] + cost,   # 替换
                )
                row_min = min(row_min, curr_row[j])
            # 整行最小值已经超过阈值，提前退出
            if row_min > max_allowed_distance:
                return 0.0
            prev_row = curr_row
        distance = prev_row[len_b]
        similarity = 1.0 - distance / max_lenreturn max(0.0, min(1.0, similarity))


# 顶层便捷函数（无状态时可直接调用）
_default_service = DedupService()


def find_duplicates(cases: list[Case]) -> list[DedupService.DuplicatePair]:"""便捷函数：使用默认配置查找重复对.

    Args:
        cases: 案件列表

    Returns:
        list[tuple[Case, Case, float]]: 重复对列表
    """
    return _default_service.find_duplicates(cases)
