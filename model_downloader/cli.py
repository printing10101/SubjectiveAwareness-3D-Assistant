"""模型下载与处理工具 - 命令行接口模块

使用 typer 构建现代化 CLI，支持子命令:
- download: 下载模型权重
- validate: 验证文件完整性
- merge: 合并 LoRA 权重
- generate-modelfile: 生成 Ollama Modelfile
- all: 执行完整流程（下载 -> 验证 -> 合并 -> 生成 Modelfile）
"""

from pathlib import Path
from typing import Optional

import typer
from loguru import logger

from .config import AppConfig
from .downloader import ModelDownloader
from .validator import FileValidator, VerificationError
from .merger import ModelMerger
from .modelfile import ModelFileGenerator
from .utils import setup_logging

app = typer.Typer(
    name="model-downloader",
    help="模型权重下载与处理工具",
    add_completion=False,
)


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="输出详细日志"),
    log_file: Optional[Path] = typer.Option(None, "--log-file", help="日志文件路径"),
) -> None:
    """CLI 全局配置"""
    setup_logging(verbose=verbose, log_file=log_file)


@app.command()
def download(
    repo_id: str = typer.Argument(
        ..., help="Hugging Face 仓库 ID (如 username/model-name)"
    ),
    filename: str = typer.Argument(..., help="要下载的文件名"),
    output_dir: Path = typer.Option(
        Path("./downloads"), "--output", "-o", help="输出目录"
    ),
    revision: str = typer.Option("main", "--revision", "-r", help="分支或标签"),
    token: Optional[str] = typer.Option(
        None, "--token", "-t", help="HF token (私有仓库)"
    ),
    max_retries: int = typer.Option(3, "--max-retries", help="最大重试次数"),
    no_verify: bool = typer.Option(False, "--no-verify", help="跳过文件验证"),
) -> None:
    """下载模型权重文件"""
    config = AppConfig()
    config.setup_download(
        repo_id=repo_id,
        filename=filename,
        output_dir=output_dir,
        token=token,
        revision=revision,
        max_retries=max_retries,
    )

    # 下载
    downloader = ModelDownloader(config.download)
    result_path = downloader.download()

    # 验证（除非禁用）
    if not no_verify and config.download.verify_hash:
        try:
            validator = FileValidator(config.download)
            validator.verify(result_path)
        except VerificationError as e:
            logger.error(f"文件验证失败: {e}")
            raise typer.Exit(1)

    logger.info(f"下载完成: {result_path}")


@app.command()
def validate(
    file_path: Path = typer.Argument(..., help="要验证的文件路径"),
    repo_id: str = typer.Argument(..., help="Hugging Face 仓库 ID"),
    filename: str = typer.Argument(..., help="文件名"),
    algorithm: str = typer.Option("sha256", "--algorithm", "-a", help="hash 算法"),
    revision: str = typer.Option("main", "--revision", "-r", help="分支或标签"),
    token: Optional[str] = typer.Option(None, "--token", "-t", help="HF token"),
) -> None:
    """验证文件完整性"""
    config = AppConfig()
    config.setup_download(
        repo_id=repo_id,
        filename=filename,
        output_dir=file_path.parent,
        token=token,
        revision=revision,
    )
    config.download.hash_algorithm = algorithm

    validator = FileValidator(config.download)
    try:
        validator.verify(file_path)
        logger.info("验证通过")
    except VerificationError as e:
        logger.error(f"验证失败: {e}")
        raise typer.Exit(1)


@app.command()
def merge(
    base_model: Path = typer.Argument(..., help="基础模型路径 (GGUF)"),
    lora_adapter: Path = typer.Argument(..., help="LoRA 适配器路径"),
    output_path: Path = typer.Argument(..., help="输出模型路径"),
    llama_cpp_path: Optional[Path] = typer.Option(
        None, "--llama-cpp", help="merge-lora 工具路径"
    ),
    lora_scale: float = typer.Option(1.0, "--scale", "-s", help="LoRA 缩放因子"),
) -> None:
    """合并 LoRA 权重到基础模型"""
    config = AppConfig()
    config.setup_merge(
        base_model=base_model,
        lora_adapter=lora_adapter,
        output_path=output_path,
        llama_cpp_path=llama_cpp_path,
        lora_scale=lora_scale,
    )

    merger = ModelMerger(config.merge)
    result_path = merger.merge()
    logger.info(f"合并完成: {result_path}")


@app.command("generate-modelfile")
def generate_modelfile(
    model_name: str = typer.Argument(..., help="Ollama 模型名称"),
    base_model_path: str = typer.Argument(..., help="合并后的 GGUF 模型路径"),
    output_path: Path = typer.Option(
        Path("./Modelfile"), "--output", "-o", help="输出路径"
    ),
    temperature: float = typer.Option(0.8, "--temperature", help="temperature 参数"),
    top_p: float = typer.Option(0.9, "--top-p", help="top_p 参数"),
    top_k: int = typer.Option(40, "--top-k", help="top_k 参数"),
    num_ctx: int = typer.Option(4096, "--num-ctx", help="上下文长度"),
    system_prompt: Optional[str] = typer.Option(None, "--system", help="系统提示"),
) -> None:
    """生成 Ollama Modelfile"""
    config = AppConfig()
    config.setup_modelfile(
        model_name=model_name,
        base_model_path=base_model_path,
        output_path=output_path,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        num_ctx=num_ctx,
        system_prompt=system_prompt or "You are a helpful assistant.",
    )

    generator = ModelFileGenerator(config.modelfile)
    result_path = generator.generate()
    logger.info(f"Modelfile 已生成: {result_path}")


@app.command()
def all(
    repo_id: str = typer.Argument(..., help="Hugging Face 仓库 ID"),
    filename: str = typer.Argument(..., help="要下载的文件名"),
    base_model: Path = typer.Argument(..., help="基础模型路径 (GGUF)"),
    output_dir: Path = typer.Option(
        Path("./output"), "--output", "-o", help="输出目录"
    ),
    revision: str = typer.Option("main", "--revision", "-r", help="分支或标签"),
    token: Optional[str] = typer.Option(None, "--token", "-t", help="HF token"),
    model_name: str = typer.Option(
        "custom-model", "--model-name", "-n", help="Ollama 模型名称"
    ),
    lora_scale: float = typer.Option(1.0, "--scale", "-s", help="LoRA 缩放因子"),
    llama_cpp_path: Optional[Path] = typer.Option(
        None, "--llama-cpp", help="merge-lora 工具路径"
    ),
    max_retries: int = typer.Option(3, "--max-retries", help="最大重试次数"),
    no_verify: bool = typer.Option(False, "--no-verify", help="跳过文件验证"),
) -> None:
    """执行完整流程: 下载 -> 验证 -> 合并 -> 生成 Modelfile"""
    logger.info("=" * 60)
    logger.info("开始执行完整流程")
    logger.info("=" * 60)

    # Step 1: 下载
    logger.info("步骤 1/4: 下载模型权重")
    config = AppConfig()
    config.setup_download(
        repo_id=repo_id,
        filename=filename,
        output_dir=output_dir / "lora",
        token=token,
        revision=revision,
        max_retries=max_retries,
    )

    downloader = ModelDownloader(config.download)
    lora_path = downloader.download()

    if not no_verify and config.download.verify_hash:
        logger.info("验证文件完整性...")
        validator = FileValidator(config.download)
        validator.verify(lora_path)

    # Step 2: 合并
    logger.info("步骤 2/4: 合并 LoRA 权重")
    merged_path = output_dir / "merged" / "model.gguf"
    merged_path.parent.mkdir(parents=True, exist_ok=True)

    config.setup_merge(
        base_model=base_model,
        lora_adapter=lora_path,
        output_path=merged_path,
        llama_cpp_path=llama_cpp_path,
        lora_scale=lora_scale,
    )

    merger = ModelMerger(config.merge)
    merger.merge()

    # Step 3: 生成 Modelfile
    logger.info("步骤 3/4: 生成 Ollama Modelfile")
    modelfile_path = output_dir / "Modelfile"

    config.setup_modelfile(
        model_name=model_name,
        base_model_path=str(merged_path),
        output_path=modelfile_path,
    )

    generator = ModelFileGenerator(config.modelfile)
    generator.generate()

    # Step 4: 完成
    logger.info("步骤 4/4: 完成")
    logger.info("=" * 60)
    logger.info("完整流程执行完成!")
    logger.info(f"LoRA 权重: {lora_path}")
    logger.info(f"合并模型: {merged_path}")
    logger.info(f"Modelfile: {modelfile_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    app()
