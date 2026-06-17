"""模型下载与处理工具 - 配置管理模块"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .utils import ensure_directory


@dataclass
class DownloadConfig:
    """下载配置"""

    # Hugging Face 仓库信息
    repo_id: str = ""  # 如 "username/model-name"
    revision: str = "main"  # 分支或标签

    # 文件配置
    filename: str = ""  # 要下载的文件名（如 "adapter_model.safetensors"）
    token: Optional[str] = None  # HF token（私有仓库需要）

    # 下载路径
    output_dir: Path = Path("./downloads")

    # 下载参数
    max_retries: int = 3  # 最大重试次数
    retry_delay: float = 2.0  # 初始重试延迟（秒）
    timeout: int = 300  # 下载超时时间（秒）
    chunk_size: int = 8192  # 下载块大小（字节）

    # 验证配置
    verify_hash: bool = True  # 是否验证文件 hash
    hash_algorithm: str = "sha256"  # hash 算法 (sha256, md5)

    def __post_init__(self):
        """初始化后确保输出目录存在"""
        if self.output_dir:
            ensure_directory(self.output_dir)


@dataclass
class MergeConfig:
    """合并配置"""

    # 基础模型路径（GGUF 格式）
    base_model: Path = Path("")

    # LoRA 适配器路径
    lora_adapter: Path = Path("")

    # 输出路径
    output_path: Path = Path("")

    # llama.cpp 工具路径
    llama_cpp_path: Path = Path("merge-lora")

    # 合并参数
    lora_scale: float = 1.0  # LoRA 缩放因子

    def __post_init__(self):
        """验证路径"""
        if self.base_model and not self.base_model.exists():
            raise FileNotFoundError(f"基础模型不存在: {self.base_model}")

        if self.lora_adapter and not self.lora_adapter.exists():
            raise FileNotFoundError(f"LoRA 适配器不存在: {self.lora_adapter}")


@dataclass
class ModelFileConfig:
    """Ollama ModelFile 配置"""

    # 模型信息
    model_name: str = ""  # Ollama 模型名称
    base_model_path: str = ""  # 合并后的 GGUF 路径

    # 模型参数
    temperature: float = 0.8
    top_p: float = 0.9
    top_k: int = 40
    num_ctx: int = 4096

    # 系统提示
    system_prompt: str = "You are a helpful assistant."

    # 模板
    template: str = """{{ if .System }}<|system|>
{{ .System }}<|end|>
{{ end }}{{ if .Prompt }}<|user|>
{{ .Prompt }}<|end|>
{{ end }}<|assistant|>
{{ .Response }}<|end|>"""

    # 输出路径
    output_path: Path = Path("./Modelfile")


@dataclass
class AppConfig:
    """应用总配置"""

    download: DownloadConfig = field(default_factory=DownloadConfig)
    merge: Optional[MergeConfig] = None
    modelfile: Optional[ModelFileConfig] = None

    # 全局设置
    verbose: bool = False
    log_file: Optional[Path] = None

    def setup_download(
        self,
        repo_id: str,
        filename: str,
        output_dir: Path = None,
        token: str = None,
        revision: str = "main",
        **kwargs,
    ) -> None:
        """设置下载配置

        Args:
            repo_id: Hugging Face 仓库 ID
            filename: 要下载的文件名
            output_dir: 输出目录
            token: HF token
            revision: 分支或标签
            **kwargs: 其他下载参数
        """
        self.download = DownloadConfig(
            repo_id=repo_id,
            filename=filename,
            output_dir=output_dir or self.download.output_dir,
            token=token,
            revision=revision,
            **kwargs,
        )

    def setup_merge(
        self,
        base_model: Path,
        lora_adapter: Path,
        output_path: Path,
        llama_cpp_path: Path = None,
        lora_scale: float = 1.0,
    ) -> None:
        """设置合并配置"""
        self.merge = MergeConfig(
            base_model=base_model,
            lora_adapter=lora_adapter,
            output_path=output_path,
            llama_cpp_path=llama_cpp_path or Path("merge-lora"),
            lora_scale=lora_scale,
        )

    def setup_modelfile(
        self,
        model_name: str,
        base_model_path: str,
        output_path: Path = None,
        **kwargs,
    ) -> None:
        """设置 ModelFile 配置"""
        self.modelfile = ModelFileConfig(
            model_name=model_name,
            base_model_path=base_model_path,
            output_path=output_path or Path("./Modelfile"),
            **kwargs,
        )
