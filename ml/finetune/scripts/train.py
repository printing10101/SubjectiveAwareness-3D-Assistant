"""
LoRA模型微调训练脚本
使用Unsloth框架进行高效的LoRA微调
"""

import os
import sys

from model_loader import load_config

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def prepare_dataset(data_path: str, tokenizer, config: dict):
    """准备训练数据集"""
    from datasets import load_dataset

    print(f"加载数据集: {data_path}")

    # 根据文件类型加载数据
    if data_path.endswith(".json"):
        dataset = load_dataset("json", data_files=data_path, split="train")
    elif data_path.endswith(".csv"):
        dataset = load_dataset("csv", data_files=data_path, split="train")
    else:
        raise ValueError(f"不支持的数据格式: {data_path}")

    print(f"数据集大小: {len(dataset)}")

    # 数据格式化
    def format_prompt(examples):
        """将数据格式化为模型可接受的格式"""
        data_config = config.get("data", {}).get("dataset_field", {})
        prompt_field = data_config.get("prompt", "instruction")
        response_field = data_config.get("response", "output")

        texts = []
        for prompt, response in zip(examples[prompt_field], examples[response_field]):
            messages = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response},
            ]
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
            texts.append(text)

        return {"text": texts}

    dataset = dataset.map(
        format_prompt, batched=True, remove_columns=dataset.column_names
    )

    return dataset


def train():
    """执行训练流程"""
    # 加载配置
    config = load_config()

    print("=" * 60)
    print("开始LoRA微调训练")
    print("=" * 60)

    # 1. 加载模型
    print("\n[步骤1] 加载模型...")
    from unsloth import FastLanguageModel

    model_config = config["model"]
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_config["model_name_or_path"],
        max_seq_length=model_config["max_seq_length"],
        dtype=None,
        load_in_4bit=model_config["load_in_4bit"],
    )
    print("模型加载完成!")

    # 2. 应用LoRA配置
    print("\n[步骤2] 应用LoRA配置...")
    lora_config = config["lora"]

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
    print("LoRA配置应用完成!")

    # 3. 加载训练数据
    print("\n[步骤3] 加载训练数据...")
    data_config = config["data"]

    train_dataset = prepare_dataset(data_config["train_data_path"], tokenizer, config)

    # 如果有验证数据，也加载
    if os.path.exists(data_config.get("eval_data_path", "")):
        eval_dataset = prepare_dataset(data_config["eval_data_path"], tokenizer, config)
    else:
        eval_dataset = None
        print("未找到验证数据集，将仅使用训练数据")

    # 4. 配置训练参数
    print("\n[步骤4] 配置训练参数...")
    training_config = config["training"]

    from trl import SFTTrainer
    from transformers import TrainingArguments

    training_args = TrainingArguments(
        output_dir=training_config["output_dir"],
        num_train_epochs=training_config["num_train_epochs"],
        per_device_train_batch_size=(training_config["per_device_train_batch_size"]),
        gradient_accumulation_steps=(training_config["gradient_accumulation_steps"]),
        learning_rate=training_config["learning_rate"],
        weight_decay=training_config["weight_decay"],
        warmup_ratio=training_config["warmup_ratio"],
        lr_scheduler_type=training_config["lr_scheduler_type"],
        logging_steps=training_config["logging_steps"],
        save_steps=training_config["save_steps"],
        save_total_limit=training_config["save_total_limit"],
        fp16=training_config["fp16"],
        bf16=training_config["bf16"],
        max_grad_norm=training_config["max_grad_norm"],
        optim=training_config["optim"],
        seed=training_config["seed"],
        report_to=training_config["report_to"],
    )

    # 5. 初始化训练器
    print("\n[步骤5] 初始化训练器...")
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        dataset_text_field="text",
        max_seq_length=model_config["max_seq_length"],
        args=training_args,
    )

    # 6. 开始训练
    print("\n[步骤6] 开始训练...")
    trainer.train()

    # 7. 保存模型
    print("\n[步骤7] 保存模型...")
    output_dir = training_config["output_dir"]
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    print(f"\n训练完成! 模型已保存至: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    train()
