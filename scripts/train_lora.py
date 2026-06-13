"""
LoRA微调训练脚本
基于Unsloth框架实现高效LoRA微调，集成TensorBoard训练监控
"""

import os
import sys
import json
import time
import yaml
from pathlib import Path
from datetime import datetime
from datasets import load_dataset
from transformers import TrainingArguments, DataCollatorForSeq2Seq
from trl import SFTTrainer
from loguru import logger

_file_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_file_dir, ".."))
sys.path.insert(0, os.path.join(_file_dir, "..", "ml", "finetune", "scripts"))


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = (
    PROJECT_ROOT / "ml" / "finetune" / "config" / "finetune_config.yaml"
)
LORA_WEIGHTS_DIR = PROJECT_ROOT / "models" / "lora_weights"
LOGS_DIR = PROJECT_ROOT / "logs"


def load_training_config(config_path: str = None) -> dict:
    """加载训练配置文件

    Args:
        config_path: 配置文件路径，默认使用ml/finetune/config/finetune_config.yaml

    Returns:
        配置字典
    """
    if config_path is None:
        config_path = str(DEFAULT_CONFIG_PATH)

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    logger.info(f"配置文件已加载: {config_path}")
    return config


def setup_logging():
    """配置日志系统"""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOGS_DIR / (f"train_lora_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    logger.remove()
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level:<7}</level> | <cyan>{message}</cyan>"
        ),
        level="INFO",
    )
    logger.add(
        str(log_file),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {message}",
        level="DEBUG",
        rotation="50 MB",
    )

    logger.info(f"日志文件: {log_file}")
    return log_file


def prepare_dataset(data_path: str, tokenizer, config: dict, split: str = "train"):
    """准备训练/评估数据集

    Args:
        data_path: 数据文件路径
        tokenizer: 分词器
        config: 配置字典
        split: 数据集类型 (train/eval)

    Returns:
        处理后的数据集
    """
    if not os.path.exists(data_path):
        logger.warning(f"数据文件不存在: {data_path}")
        return None

    logger.info(f"加载{split}数据集: {data_path}")

    if data_path.endswith(".jsonl"):
        dataset = load_dataset("json", data_files=data_path, split="train")
    elif data_path.endswith(".json"):
        dataset = load_dataset("json", data_files=data_path, split="train")
    elif data_path.endswith(".csv"):
        dataset = load_dataset("csv", data_files=data_path, split="train")
    else:
        raise ValueError(f"不支持的数据格式: {data_path}")

    logger.info(f"{split}数据集大小: {len(dataset)}")

    data_field = config.get("data", {}).get("dataset_field", {})
    prompt_field = data_field.get("prompt", "instruction")
    response_field = data_field.get("response", "output")

    def format_chat_template(examples):
        texts = []
        for prompt, response in zip(examples[prompt_field], examples[response_field]):
            messages = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response},
            ]
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=False,
            )
            texts.append(text)
        return {"text": texts}

    dataset = dataset.map(
        format_chat_template,
        batched=True,
        remove_columns=dataset.column_names,
        desc=f"格式化{split}数据",
    )

    return dataset


def train():
    """执行LoRA微调训练主流程"""
    setup_logging()

    logger.info("=" * 70)
    logger.info("LoRA微调训练 - 启动")
    logger.info("=" * 70)

    config = load_training_config()
    model_config = config["model"]
    lora_config = config["lora"]
    training_config = config["training"]
    data_config = config["data"]

    batch_size = training_config.get("per_device_train_batch_size", 4)
    gradient_accumulation_steps = training_config.get("gradient_accumulation_steps", 4)
    learning_rate = training_config.get("learning_rate", 2e-4)
    num_epochs = training_config.get("num_train_epochs", 3)
    warmup_ratio = training_config.get("warmup_ratio", 0.1)
    logging_steps = training_config.get("logging_steps", 10)
    save_steps = training_config.get("save_steps", 100)

    lora_weights_path = str(LORA_WEIGHTS_DIR)
    os.makedirs(lora_weights_path, exist_ok=True)

    effective_batch_size = batch_size * gradient_accumulation_steps
    logger.info("训练参数:")
    logger.info(f"  batch_size: {batch_size}")
    logger.info(f"  gradient_accumulation_steps: {gradient_accumulation_steps}")
    logger.info(f"  有效批次大小: {effective_batch_size}")
    logger.info(f"  learning_rate: {learning_rate}")
    logger.info(f"  num_epochs: {num_epochs}")
    logger.info(f"  warmup_ratio: {warmup_ratio}")
    logger.info(f"  logging_steps: {logging_steps}")
    logger.info(f"  save_steps: {save_steps}")
    logger.info(f"  LoRA权重保存路径: {lora_weights_path}")

    logger.info("[1/6] 加载模型...")
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_config["model_name_or_path"],
        max_seq_length=model_config["max_seq_length"],
        dtype=None,
        load_in_4bit=model_config["load_in_4bit"],
    )
    logger.info(f"模型加载完成: {model_config['model_name_or_path']}")

    logger.info("[2/6] 配置LoRA...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=lora_config["lora_r"],
        target_modules=lora_config["target_modules"],
        lora_alpha=lora_config["lora_alpha"],
        lora_dropout=lora_config["lora_dropout"],
        bias=lora_config.get("bias", "none"),
        use_gradient_checkpointing="unsloth",
        random_state=training_config.get("seed", 42),
        max_seq_length=model_config["max_seq_length"],
    )

    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    logger.info(
        f"LoRA可训练参数: {trainable_params:,} / {total_params:,} "
        f"({trainable_params / total_params:.4%})"
    )

    logger.info("[3/6] 加载训练数据...")
    train_data_path = data_config.get("train_data_path")
    if not train_data_path or not os.path.exists(train_data_path):
        alt_paths = [
            str(PROJECT_ROOT / "data" / "training" / "processed.jsonl"),
            str(PROJECT_ROOT / "data" / "train.json"),
            str(PROJECT_ROOT / "data" / "train.jsonl"),
        ]
        for p in alt_paths:
            if os.path.exists(p):
                train_data_path = p
                logger.info(f"使用备选训练数据路径: {train_data_path}")
                break

    if not train_data_path or not os.path.exists(train_data_path):
        logger.error("训练数据文件不存在，请检查配置")
        logger.error(f"尝试的路径: {data_config.get('train_data_path')}")
        sys.exit(1)

    train_dataset = prepare_dataset(train_data_path, tokenizer, config, split="train")

    eval_dataset = None
    eval_data_path = data_config.get("eval_data_path")
    if eval_data_path:
        eval_dataset = prepare_dataset(eval_data_path, tokenizer, config, split="eval")

    logger.info(f"训练样本数: {len(train_dataset) if train_dataset else 0}")
    if eval_dataset:
        logger.info(f"验证样本数: {len(eval_dataset)}")

    logger.info("[4/6] 配置训练参数...")

    report_to = training_config.get("report_to", "tensorboard")
    if isinstance(report_to, str):
        report_to = [report_to] if report_to != "none" else "none"

    training_args = TrainingArguments(
        output_dir=lora_weights_path,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        weight_decay=training_config.get("weight_decay", 0.01),
        warmup_ratio=warmup_ratio,
        lr_scheduler_type=training_config.get("lr_scheduler_type", "cosine"),
        logging_steps=logging_steps,
        logging_dir=str(LOGS_DIR / "tensorboard"),
        logging_first_step=True,
        save_steps=save_steps,
        save_total_limit=training_config.get("save_total_limit", 3),
        fp16=training_config.get("fp16", True),
        bf16=training_config.get("bf16", False),
        max_grad_norm=training_config.get("max_grad_norm", 1.0),
        optim=training_config.get("optim", "adamw_torch"),
        seed=training_config.get("seed", 42),
        report_to=report_to,
        evaluation_strategy="steps" if eval_dataset else "no",
        eval_steps=save_steps if eval_dataset else None,
        load_best_model_at_end=True if eval_dataset else False,
        metric_for_best_model="eval_loss" if eval_dataset else None,
        save_safetensors=True,
        remove_unused_columns=False,
        dataloader_num_workers=0,
        ddp_find_unused_parameters=False,
    )

    logger.info(f"TensorBoard日志: {LOGS_DIR / 'tensorboard'}")
    logger.info(f"报告工具: {report_to}")

    logger.info("[5/6] 初始化训练器...")

    collator = DataCollatorForSeq2Seq(tokenizer=tokenizer)
    logger.info("使用DataCollatorForSeq2Seq")

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        args=training_args,
        max_seq_length=model_config["max_seq_length"],
        dataset_text_field="text",
        data_collator=collator,
    )

    logger.info("[6/6] 开始训练...")
    logger.info("=" * 70)

    start_time = time.time()
    train_result = trainer.train()
    total_time = time.time() - start_time

    logger.info(f"训练完成! 总耗时: {total_time:.2f}秒 ({total_time / 60:.2f}分钟)")

    logger.info("保存LoRA权重...")
    final_save_path = os.path.join(lora_weights_path, "final")
    trainer.model.save_pretrained(final_save_path)
    tokenizer.save_pretrained(final_save_path)

    logger.info(f"LoRA权重已保存至: {final_save_path}")

    adapter_config_path = os.path.join(final_save_path, "adapter_config.json")
    if os.path.exists(adapter_config_path):
        with open(adapter_config_path, "r", encoding="utf-8") as f:
            adapter_config = json.load(f)
        logger.info(f"adapter_config.json验证通过, rank={adapter_config.get('r')}")

    training_loss = (
        train_result.training_loss if hasattr(train_result, "training_loss") else None
    )
    logger.info(f"训练损失: {training_loss:.4f}" if training_loss else "训练损失: N/A")

    metrics = {}
    metrics["train_loss"] = training_loss
    metrics["train_runtime"] = total_time
    metrics["train_samples_per_second"] = (
        train_result.metrics.get("train_samples_per_second", 0)
        if hasattr(train_result, "metrics")
        else 0
    )
    metrics["train_steps_per_second"] = (
        train_result.metrics.get("train_steps_per_second", 0)
        if hasattr(train_result, "metrics")
        else 0
    )
    metrics["total_steps"] = (
        train_result.metrics.get("train_steps", 0)
        if hasattr(train_result, "metrics")
        else 0
    )
    metrics["effective_batch_size"] = effective_batch_size
    metrics["learning_rate"] = learning_rate
    metrics["num_epochs"] = num_epochs
    metrics["lora_r"] = lora_config["lora_r"]
    metrics["lora_alpha"] = lora_config["lora_alpha"]
    metrics["trainable_params"] = trainable_params

    metrics_path = os.path.join(lora_weights_path, "training_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    logger.info(f"训练指标已保存至: {metrics_path}")

    logger.info("=" * 70)
    logger.info("LoRA微调训练 - 完成")
    logger.info(f"LoRA权重: {final_save_path}")
    logger.info(f"训练损失: {training_loss:.4f}" if training_loss else "")
    logger.info("=" * 70)

    return metrics


if __name__ == "__main__":
    train()
