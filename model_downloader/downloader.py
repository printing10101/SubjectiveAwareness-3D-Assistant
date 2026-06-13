"""模型下载与处理工具 - 核心下载器模块

功能:
- 从 Hugging Face Hub 下载文件
- 断点续传支持
- 自动重试（指数退避）
- 实时进度显示
"""

import time
from pathlib import Path

from huggingface_hub import hf_hub_download, HfApi

from .config import DownloadConfig
from loguru import logger


class DownloadError(Exception):
    """下载异常"""

    pass


class RetryExhaustedError(DownloadError):
    """重试次数用尽"""

    pass


class ModelDownloader:
    """模型下载器

    支持从 Hugging Face Hub 下载文件，具备:
    - 断点续传
    - 自动重试（指数退避）
    - 实时进度显示
    """

    def __init__(self, config: DownloadConfig):
        """初始化下载器

        Args:
            config: 下载配置
        """
        self.config = config
        self.api = HfApi()

    def download(self) -> Path:
        """执行下载

        Returns:
            下载文件的本地路径

        Raises:
            DownloadError: 下载失败
            RetryExhaustedError: 重试次数用尽
        """
        output_path = self.config.output_dir / self.config.filename

        logger.info(f"开始下载: {self.config.repo_id}/{self.config.filename}")
        logger.info(f"输出路径: {output_path}")

        # 使用 huggingface_hub 下载（内置断点续传）
        try:
            result_path = self._download_with_retry()
            logger.info(f"下载完成: {result_path}")
            return Path(result_path)
        except Exception as e:
            logger.error(f"下载失败: {e}")
            raise DownloadError(f"下载失败: {e}") from e

    def _download_with_retry(self) -> str:
        """带重试的下载

        Returns:
            下载文件路径
        """
        last_error = None

        for attempt in range(1, self.config.max_retries + 1):
            try:
                return self._do_download()
            except Exception as e:
                last_error = e
                logger.warning(
                    f"下载失败 (尝试 {attempt}/{self.config.max_retries}): {e}"
                )

                if attempt < self.config.max_retries:
                    # 指数退避
                    delay = self.config.retry_delay * (2 ** (attempt - 1))
                    logger.info(f"等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)

        raise RetryExhaustedError(
            f"下载失败，已重试 {self.config.max_retries} 次: {last_error}"
        )

    def _do_download(self) -> str:
        """执行实际下载

        Returns:
            下载文件路径
        """
        # 使用 hf_hub_download，它内置了断点续传功能
        result = hf_hub_download(
            repo_id=self.config.repo_id,
            filename=self.config.filename,
            revision=self.config.revision,
            token=self.config.token,
            cache_dir=str(self.config.output_dir),
            local_dir=str(self.config.output_dir),
            local_dir_use_symlinks=False,
        )

        return result

    def get_file_info(self) -> dict:
        """获取远程文件信息

        Returns:
            文件信息字典（大小、hash等）
        """
        try:
            info = self.api.hf_hub_info(
                repo_id=self.config.repo_id,
                filename=self.config.filename,
                revision=self.config.revision,
                token=self.config.token,
            )

            return {
                "size": info.size,
                "sha256": getattr(info, "lfs", {}).get("sha256", None),
                "oid": info.oid,
            }
        except Exception as e:
            logger.warning(f"获取文件信息失败: {e}")
            return {}
