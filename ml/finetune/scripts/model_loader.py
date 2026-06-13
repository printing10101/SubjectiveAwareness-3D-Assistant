"""
模型加载与LoRA配置模块
提供从配置文件加载模型和LoRA参数的功能
"""

import os
import yaml
import torch
from typing import List


def load_config(config_path: str = None) -> dict:
    """加载YAML配置文件"""
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config",
            "finetune_config.yaml",
        )

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def get_lora_target_modules(target_modules: List[str]):
    """获取LoRA目标模块"""
    return target_modules


def setup_model_from_config(config: dict):
    """
    根据配置文件加载模型和LoRA参数
    使用Unsloth进行4bit量化加载和LoRA配置
    """
    model_config = config["model"]
    lora_config = config["lora"]

    # 导入Unsloth
    from unsloth import FastLanguageModel

    # 加载4bit量化模型 (使用Unsloth)
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_config["model_name_or_path"],
        max_seq_length=model_config["max_seq_length"],
        dtype=None,  # 自动选择
        load_in_4bit=model_config["load_in_4bit"],
    )

    # 配置LoRA
    model = FastLanguageModel.get_peft_model(
        model,
        r=lora_config["lora_r"],
        target_modules=lora_config["target_modules"],
        lora_alpha=lora_config["lora_alpha"],
        lora_dropout=lora_config["lora_dropout"],
        bias=lora_config["bias"],
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    return model, tokenizer


def get_gpu_memory_info():
    """获取GPU显存使用信息"""
    if not torch.cuda.is_available():
        return {"available": False, "message": "CUDA不可用"}

    device_count = torch.cuda.device_count()
    memory_info = {"available": True, "device_count": device_count, "devices": []}

    for i in range(device_count):
        props = torch.cuda.get_device_properties(i)
        free_mem, total_mem = torch.cuda.mem_get_info(i)
        used_mem = total_mem - free_mem

        memory_info["devices"].append(
            {
                "device_id": i,
                "name": props.name,
                "total_memory_gb": round(total_mem / (1024**3), 2),
                "used_memory_gb": round(used_mem / (1024**3), 2),
                "free_memory_gb": round(free_mem / (1024**3), 2),
                "memory_utilization": round(used_mem / total_mem * 100, 2),
            }
        )

    return memory_info


def check_memory_within_limit(limit_gb: float = 22.0):
    """检查显存是否在限制范围内"""
    if not torch.cuda.is_available():
        return False, "CUDA不可用"

    free_mem, total_mem = torch.cuda.mem_get_info(0)
    used_mem = total_mem - free_mem
    used_mem_gb = used_mem / (1024**3)

    if used_mem_gb <= limit_gb:
        return True, (f"显存使用 {used_mem_gb:.2f}GB / {limit_gb}GB - 正常")
    else:
        return False, (f"显存使用 {used_mem_gb:.2f}GB 超过限制 {limit_gb}GB")


if __name__ == "__main__":
    # 测试配置加载
    config = load_config()
    print("配置文件加载成功!")
    print(f"模型路径: {config['model']['model_name_or_path']}")
    print(
        f"LoRA配置: r={config['lora']['lora_r']}, alpha={config['lora']['lora_alpha']}"
    )
    print(f"目标模块: {config['lora']['target_modules']}")
