"""
LoRA权重合并与模型导出脚本
将微调得到的LoRA权重与原始基础模型合并，导出完整模型
"""

import os
import sys
import argparse
from typing import Optional

from model_loader import load_config

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


MERGE_MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "models",
    "merged_model",
)


def merge_and_export(
    lora_path: str,
    output_path: str,
    base_model_name: Optional[str] = None,
    push_to_ollama: bool = False,
    max_seq_length: int = 1920,
):
    """合并LoRA权重到基础模型并导出

    Args:
        lora_path: LoRA权重路径
        output_path: 输出路径
        base_model_name: 基础模型名称（默认从配置读取）
        push_to_ollama: 是否导入Ollama
        max_seq_length: 最大序列长度
    """
    print("=" * 60)
    print("LoRA权重合并与模型导出")
    print("=" * 60)

    print("\n[步骤1] 加载基础模型...")
    from unsloth import FastLanguageModel

    if base_model_name is None:
        config = load_config()
        base_model_name = config["model"]["model_name_or_path"]

    print(f"基础模型: {base_model_name}")
    print(f"LoRA权重: {lora_path}")
    print(f"输出路径: {output_path}")

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model_name,
        max_seq_length=max_seq_length,
        dtype=None,
        load_in_4bit=False,
    )

    print("\n[步骤2] 加载LoRA权重...")
    from peft import PeftModel

    model = PeftModel.from_pretrained(model, lora_path)
    print("LoRA权重加载完成")

    print("\n[步骤3] 合并权重...")
    merged_model = model.merge_and_unload()
    print("权重合并完成")

    print(f"\n[步骤4] 导出模型到 {output_path}...")
    os.makedirs(output_path, exist_ok=True)
    merged_model.save_pretrained(output_path)
    tokenizer.save_pretrained(output_path)
    print("模型导出完成")

    print("\n[步骤5] 验证导出完整性...")
    required_files = [
        "config.json",
        "tokenizer.json",
        "tokenizer_config.json",
    ]
    for f in required_files:
        fpath = os.path.join(output_path, f)
        if os.path.exists(fpath):
            size = os.path.getsize(fpath)
            print(f"  ✓ {f} ({size / 1024:.1f} KB)")
        else:
            print(f"  ✗ {f} - 缺失")

    model_files = [
        f
        for f in os.listdir(output_path)
        if f.endswith(".safetensors") or f.endswith(".bin")
    ]
    for f in model_files:
        fpath = os.path.join(output_path, f)
        size_gb = os.path.getsize(fpath) / (1024**3)
        print(f"  ✓ {f} ({size_gb:.2f} GB)")

    total_size = sum(
        os.path.getsize(os.path.join(output_path, f))
        for f in os.listdir(output_path)
        if os.path.isfile(os.path.join(output_path, f))
    )
    print(f"\n  模型总大小: {total_size / (1024**3):.2f} GB")

    if push_to_ollama:
        print("\n[步骤6] 导入Ollama...")
        _import_to_ollama(output_path)

    print("\n" + "=" * 60)
    print("合并与导出完成!")
    print("=" * 60)


def _import_to_ollama(model_path: str):
    """将合并后的模型导入Ollama"""
    modelfile_content = (
        f"FROM {model_path}\n"
        'TEMPLATE """{{ .Prompt }}"""\n'
        "PARAMETER temperature 0.3\n"
        "PARAMETER top_p 0.9\n"
    )

    modelfile_path = os.path.join(model_path, "Modelfile")
    with open(modelfile_path, "w", encoding="utf-8") as f:
        f.write(modelfile_content)

    import subprocess

    model_name = "fine-tuned-model:latest"
    result = subprocess.run(
        ["ollama", "create", model_name, "-f", modelfile_path],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"  ✓ Ollama模型 '{model_name}' 创建成功")
    else:
        print(f"  ✗ Ollama导入失败: {result.stderr}")


def convert_to_gguf(model_path: str, output_path: str):
    """将HuggingFace模型转换为GGUF格式（用于Ollama）"""
    print("\n[可选] 转换模型为GGUF格式...")
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch

        model = AutoModelForCausalLM.from_pretrained(
            model_path, torch_dtype=torch.float16, device_map="cpu"
        )
        tokenizer = AutoTokenizer.from_pretrained(model_path)

        os.makedirs(output_path, exist_ok=True)
        model.save_pretrained(output_path, safe_serialization=True)
        tokenizer.save_pretrained(output_path)
        print(f"  ✓ 模型已转换为float16并保存至 {output_path}")
    except Exception as e:
        print(f"  ✗ GGUF转换失败: {e}")
        print("  可使用 llama.cpp 的 convert.py 工具手动转换")


def main():
    parser = argparse.ArgumentParser(description="LoRA权重合并与模型导出")
    parser.add_argument(
        "--lora_path",
        type=str,
        default=os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "models",
            "lora_weights",
            "final",
        ),
        help="LoRA权重路径",
    )
    parser.add_argument(
        "--output_path",
        type=str,
        default=MERGE_MODEL_DIR,
        help="合并后模型输出路径",
    )
    parser.add_argument(
        "--base_model",
        type=str,
        default=None,
        help="基础模型名称（默认从配置文件读取）",
    )
    parser.add_argument(
        "--push_to_ollama",
        action="store_true",
        help="是否自动导入Ollama",
    )

    args = parser.parse_args()

    if not os.path.exists(args.lora_path):
        print(f"错误: LoRA权重路径不存在: {args.lora_path}")
        print("请先运行训练脚本生成LoRA权重")
        sys.exit(1)

    merge_and_export(
        lora_path=args.lora_path,
        output_path=args.output_path,
        base_model_name=args.base_model,
        push_to_ollama=args.push_to_ollama,
    )


if __name__ == "__main__":
    main()
