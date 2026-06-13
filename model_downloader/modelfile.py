"""模型下载与处理工具 - Ollama ModelFile 生成模块

功能:
- 生成符合 Ollama 规范的 Modelfile
- 包含模型参数、系统提示、模板
"""

from pathlib import Path

from .config import ModelFileConfig
from loguru import logger


class ModelFileGenerator:
    """Ollama ModelFile 生成器

    生成符合 Ollama 规范的 Modelfile，包含:
    - FROM 指令（基础模型路径）
    - 模型参数（temperature, top_p, top_k, num_ctx）
    - 系统提示
    - 聊天模板
    """

    def __init__(self, config: ModelFileConfig):
        """初始化生成器

        Args:
            config: ModelFile 配置
        """
        self.config = config

    def generate(self) -> Path:
        """生成 Modelfile

        Returns:
            生成的 Modelfile 路径
        """
        logger.info(f"生成 Ollama Modelfile: {self.config.output_path}")

        content = self._build_modelfile()

        # 写入文件
        output_path = self.config.output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

        logger.info(f"Modelfile 已生成: {output_path}")
        return output_path

    def generate_content(self) -> str:
        """生成 Modelfile 内容（不写入文件）

        Returns:
            Modelfile 内容字符串
        """
        return self._build_modelfile()

    def _build_modelfile(self) -> str:
        """构建 Modelfile 内容

        Returns:
            Modelfile 内容
        """
        lines = []

        # FROM 指令
        lines.append(f"FROM {self.config.base_model_path}")
        lines.append("")

        # 模型参数
        lines.append("# 模型参数")
        lines.append(f"PARAMETER temperature {self.config.temperature}")
        lines.append(f"PARAMETER top_p {self.config.top_p}")
        lines.append(f"PARAMETER top_k {self.config.top_k}")
        lines.append(f"PARAMETER num_ctx {self.config.num_ctx}")
        lines.append("")

        # 系统提示
        lines.append("# 系统提示")
        lines.append(f'SYSTEM """{self.config.system_prompt}"""')
        lines.append("")

        # 聊天模板
        lines.append("# 聊天模板")
        lines.append(f'TEMPLATE """{self.config.template}"""')
        lines.append("")

        return "\n".join(lines)
