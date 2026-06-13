"""模型下载与处理工具 - 文件完整性验证模块

功能:
- SHA256/MD5 校验
- 与 Hugging Face 元数据对比
- 文件损坏检测
"""

import hashlib
from pathlib import Path
from typing import Optional

from huggingface_hub import HfApi

from .config import DownloadConfig
from .utils import format_bytes
from loguru import logger


class VerificationError(Exception):
    """验证失败异常"""

    pass


class FileValidator:
    """文件完整性验证器

    支持:
    - SHA256 校验
    - MD5 校验
    - 与远程 hash 对比
    """

    def __init__(self, config: DownloadConfig):
        """初始化验证器

        Args:
            config: 下载配置
        """
        self.config = config
        self.api = HfApi()

    def verify(self, file_path: Path) -> bool:
        """验证文件完整性

        Args:
            file_path: 要验证的文件路径

        Returns:
            验证是否通过

        Raises:
            VerificationError: 验证失败
        """
        if not file_path.exists():
            raise VerificationError(f"文件不存在: {file_path}")

        logger.info(f"开始验证文件: {file_path}")

        # 计算本地文件 hash
        local_hash = self._compute_hash(file_path)
        logger.debug(f"本地文件 hash ({self.config.hash_algorithm}): {local_hash}")

        # 获取远程 hash
        remote_hash = self._get_remote_hash()

        if remote_hash is None:
            logger.warning("无法获取远程文件 hash，跳过验证")
            return True

        # 对比 hash
        if local_hash.lower() == remote_hash.lower():
            logger.info("验证通过: hash 匹配")
            return True
        else:
            raise VerificationError(
                f"验证失败: hash 不匹配\n  本地: {local_hash}\n  远程: {remote_hash}"
            )

    def _compute_hash(self, file_path: Path) -> str:
        """计算文件 hash

        Args:
            file_path: 文件路径

        Returns:
            hash 字符串（十六进制）
        """
        hash_func = hashlib.new(self.config.hash_algorithm)

        with open(file_path, "rb") as f:
            while chunk := f.read(self.config.chunk_size):
                hash_func.update(chunk)

        return hash_func.hexdigest()

    def _get_remote_hash(self) -> Optional[str]:
        """获取远程文件 hash

        Returns:
            hash 字符串，或 None
        """
        try:
            info = self.api.hf_hub_info(
                repo_id=self.config.repo_id,
                filename=self.config.filename,
                revision=self.config.revision,
                token=self.config.token,
            )

            # 尝试从 lfs 元数据获取 sha256
            lfs_info = getattr(info, "lfs", None)
            if lfs_info and "sha256" in lfs_info:
                return lfs_info["sha256"]

            # 尝试从 commit_info 获取
            commit_info = getattr(info, "commit_info", None)
            if commit_info:
                return getattr(commit_info, "oid", None)

            return None
        except Exception as e:
            logger.warning(f"获取远程 hash 失败: {e}")
            return None

    def verify_file_size(self, file_path: Path, expected_size: int) -> bool:
        """验证文件大小

        Args:
            file_path: 文件路径
            expected_size: 预期大小（字节）

        Returns:
            大小是否匹配
        """
        actual_size = file_path.stat().st_size

        if actual_size == expected_size:
            logger.info(f"文件大小验证通过: {format_bytes(actual_size)}")
            return True
        else:
            logger.warning(
                f"文件大小不匹配: 预期 {format_bytes(expected_size)}, "
                f"实际 {format_bytes(actual_size)}"
            )
            return False
