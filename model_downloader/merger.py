"""模型下载与处理工具 - LoRA 权重合并模块

功能:
- 调用 llama.cpp merge-lora 工具
- 合并 LoRA 权重到 GGUF 基础模型
- 验证合并结果
"""

import subprocess
from pathlib import Path

from .config import MergeConfig
from .utils import check_command_exists
from loguru import logger


class MergeError(Exception):
    """合并失败异常"""

    pass


class ModelMerger:
    """模型合并器

    使用 llama.cpp 的 merge-lora 工具将 LoRA 权重合并到 GGUF 基础模型
    """

    def __init__(self, config: MergeConfig):
        """初始化合并器

        Args:
            config: 合并配置
        """
        self.config = config

    def merge(self) -> Path:
        """执行合并操作

        Returns:
            合并后的模型路径

        Raises:
            MergeError: 合并失败
        """
        logger.info("开始合并 LoRA 权重到基础模型")
        logger.info(f"基础模型: {self.config.base_model}")
        logger.info(f"LoRA 适配器: {self.config.lora_adapter}")
        logger.info(f"输出路径: {self.config.output_path}")

        # 检查 llama.cpp 工具
        if not self._check_llama_cpp_tool():
            raise MergeError(
                f"找不到 merge-lora 工具: {self.config.llama_cpp_path}\n"
                f"请先编译 llama.cpp: https://github.com/ggerganov/llama.cpp"
            )

        # 执行合并
        try:
            self._run_merge()
        except Exception as e:
            raise MergeError(f"合并失败: {e}") from e

        # 验证输出
        output_path = Path(self.config.output_path)
        if not output_path.exists():
            raise MergeError(f"合并完成但输出文件不存在: {output_path}")

        logger.info(f"合并完成: {output_path}")
        return output_path

    def _check_llama_cpp_tool(self) -> bool:
        """检查 llama.cpp merge-lora 工具是否存在"""
        # 尝试在 PATH 中查找
        if check_command_exists(self.config.llama_cpp_path.name):
            return True

        # 尝试使用完整路径
        if self.config.llama_cpp_path.exists():
            return True

        # 尝试常见位置
        common_paths = [
            Path("llama.cpp/build/bin/merge-lora"),
            Path("llama.cpp/build/bin/merge-lora.exe"),  # Windows
            Path("llama.cpp/merge-lora"),
        ]

        for path in common_paths:
            if path.exists():
                self.config.llama_cpp_path = path
                return True

        return False

    def _run_merge(self) -> None:
        """运行合并命令"""
        cmd = [
            str(self.config.llama_cpp_path),
            "--model",
            str(self.config.base_model),
            "--lora",
            str(self.config.lora_adapter),
            "--model-out",
            str(self.config.output_path),
            "--scale",
            str(self.config.lora_scale),
        ]

        logger.debug(f"执行命令: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,  # 1小时超时
                check=True,
            )

            if result.stdout:
                logger.debug(f"merge-lora 输出: {result.stdout}")

        except subprocess.TimeoutExpired:
            raise MergeError("合并超时（超过1小时）")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else e.stdout
            raise MergeError(f"merge-lora 执行失败: {error_msg}")
