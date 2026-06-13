"""
模型加载验证脚本
验证模型加载、推理功能和显存使用情况
"""

import os
import sys
import time
import torch

from model_loader import load_config, get_gpu_memory_info, check_memory_within_limit

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_model_loading():
    """测试模型加载功能"""
    print("=" * 60)
    print("开始测试模型加载...")
    print("=" * 60)

    # 加载配置
    config = load_config()
    model_config = config["model"]

    # 记录开始时间
    start_time = time.time()

    try:
        # 尝试导入Unsloth
        print("\n[1/4] 导入Unsloth框架...")
        from unsloth import FastLanguageModel

        print("  - Unsloth导入成功")

        # 加载模型
        print("\n[2/4] 加载4bit量化模型...")
        print(f"  - 模型路径: {model_config['model_name_or_path']}")
        print(f"  - 最大序列长度: {model_config['max_seq_length']}")
        print(f"  - 4bit量化: {model_config['load_in_4bit']}")

        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=model_config["model_name_or_path"],
            max_seq_length=model_config["max_seq_length"],
            dtype=None,
            load_in_4bit=model_config["load_in_4bit"],
        )
        print("  - 模型加载成功!")

        # 应用LoRA配置
        print("\n[3/4] 应用LoRA配置...")
        lora_config = config["lora"]
        print(f"  - LoRA秩(r): {lora_config['lora_r']}")
        print(f"  - LoRA alpha: {lora_config['lora_alpha']}")
        print(f"  - 目标模块: {lora_config['target_modules']}")

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
        print("  - LoRA配置应用成功!")

        load_time = time.time() - start_time
        print(f"\n  模型加载时间: {load_time:.2f}秒")

        # 显存使用监控
        print("\n[4/4] 显存使用情况...")
        mem_info = get_gpu_memory_info()
        if mem_info["available"]:
            for device in mem_info["devices"]:
                print(f"  - GPU {device['device_id']}: {device['name']}")
                print(f"    总显存: {device['total_memory_gb']}GB")
                print(f"    已使用: {device['used_memory_gb']}GB")
                print(f"    利用率: {device['memory_utilization']}%")

        return model, tokenizer, load_time

    except ImportError as e:
        print(f"\n错误: 缺少依赖库 - {e}")
        print("请确保已安装所有依赖: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: 模型加载失败 - {e}")
        sys.exit(1)


def test_inference(model, tokenizer, config):
    """测试模型推理功能"""
    print("\n" + "=" * 60)
    print("开始测试模型推理...")
    print("=" * 60)

    # 准备测试输入
    test_prompts = [
        "请解释什么是LoRA微调？",
        "用Python写一个简单的Hello World程序",
        "今天天气怎么样？",
    ]

    # 设置为推理模式
    from unsloth import FastLanguageModel

    FastLanguageModel.for_inference(model)

    inference_times = []

    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n测试 {i}/{len(test_prompts)}: {prompt}")

        # 格式化输入 (根据模型要求)
        messages = [{"role": "user", "content": prompt}]

        # 应用聊天模板
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        # 编码输入
        inputs = tokenizer(text, return_tensors="pt").to("cuda")

        # 推理
        start_time = time.time()
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=128,
                use_cache=True,
                temperature=0.7,
                top_p=0.9,
                repetition_penalty=1.1,
            )
        inference_time = time.time() - start_time
        inference_times.append(inference_time)

        # 解码输出
        output_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # 打印结果 (截断显示)
        if len(output_text) > 300:
            print(f"  输出: {output_text[:300]}...")
        else:
            print(f"  输出: {output_text}")
        print(f"  推理时间: {inference_time:.2f}秒")

    avg_inference_time = sum(inference_times) / len(inference_times)
    print(f"\n平均推理时间: {avg_inference_time:.2f}秒")

    return avg_inference_time


def print_summary(load_time, inference_time):
    """打印测试总结"""
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    print(f"\n模型加载时间: {load_time:.2f}秒")
    print(f"平均推理时间: {inference_time:.2f}秒")

    # 显存检查
    mem_check, mem_msg = check_memory_within_limit(22.0)
    print(f"显存检查: {'通过' if mem_check else '未通过'}")
    print(f"  {mem_msg}")

    # 总体评估
    print("\n" + "-" * 40)
    if mem_check:
        print("环境验证: 通过")
        print("模型可以在RTX 4090上稳定运行")
    else:
        print("环境验证: 未通过")
        print("需要优化显存使用或降低批次大小")
    print("-" * 40)


def main():
    """主函数"""
    print("LoRA模型微调环境验证脚本")
    print(f"Python版本: {sys.version}")
    print(f"PyTorch版本: {torch.__version__}")
    print(f"CUDA可用: {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        print(f"CUDA版本: {torch.version.cuda}")
        print(f"GPU设备: {torch.cuda.get_device_name(0)}")

    print("\n")

    # 测试模型加载
    model, tokenizer, load_time = test_model_loading()

    # 测试推理
    config = load_config()
    avg_inference_time = test_inference(model, tokenizer, config)

    # 打印总结
    print_summary(load_time, avg_inference_time)

    print("\n验证完成!")


if __name__ == "__main__":
    main()
