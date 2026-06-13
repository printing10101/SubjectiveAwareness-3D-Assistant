# 模型权重下载与处理工具

功能完善的模型权重下载与处理工具，支持从 Hugging Face Hub 下载 LoRA 权重文件，验证文件完整性，合并到 GGUF 基础模型，并生成 Ollama ModelFile。

## 功能特性

- 从 Hugging Face Hub 下载预训练 LoRA 权重文件
- SHA256/MD5 文件完整性验证
- 使用 llama.cpp merge-lora 工具合并 LoRA 权重到 GGUF 基础模型
- 自动生成符合 Ollama 规范的 ModelFile
- 直观的下载进度显示（已下载大小、总大小、速度、ETA）
- 错误检测与自动重试（指数退避策略）
- 断点续传功能

## 安装依赖

```bash
pip install -r model_downloader/requirements.txt
```

## 使用方法

### 下载模型权重

```bash
python scripts/download_model.py download username/model adapter_model.safetensors
```

### 验证文件完整性

```bash
python scripts/download_model.py validate ./downloads/adapter_model.safetensors username/model adapter_model.safetensors
```

### 合并 LoRA 权重

```bash
python scripts/download_model.py merge ./models/base.gguf ./downloads/adapter_model.safetensors ./output/merged.gguf
```

### 生成 Ollama ModelFile

```bash
python scripts/download_model.py generate-modelfile my-custom-model ./output/merged.gguf
```

### 执行完整流程

```bash
python scripts/download_model.py all username/model adapter_model.safetensors ./models/base.gguf --model-name my-custom-model
```

## 命令行选项

### 下载命令

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--output`, `-o` | 输出目录 | `./downloads` |
| `--revision`, `-r` | 分支或标签 | `main` |
| `--token`, `-t` | HF token（私有仓库） | - |
| `--max-retries` | 最大重试次数 | `3` |
| `--no-verify` | 跳过文件验证 | `False` |

### 合并命令

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--llama-cpp` | merge-lora 工具路径 | 自动查找 |
| `--scale`, `-s` | LoRA 缩放因子 | `1.0` |

### 完整流程命令

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--output`, `-o` | 输出目录 | `./output` |
| `--model-name`, `-n` | Ollama 模型名称 | `custom-model` |
| `--scale`, `-s` | LoRA 缩放因子 | `1.0` |
| `--llama-cpp` | merge-lora 工具路径 | 自动查找 |
| `--max-retries` | 最大重试次数 | `3` |
| `--no-verify` | 跳过文件验证 | `False` |

### 全局选项

| 选项 | 说明 |
|------|------|
| `--verbose`, `-v` | 输出详细日志 |
| `--log-file` | 日志文件路径 |

## 项目结构

```
model_downloader/
├── __init__.py           # 包初始化
├── config.py             # 配置管理
├── downloader.py         # 核心下载器
├── validator.py          # 文件完整性验证
├── merger.py             # LoRA 权重合并
├── modelfile.py          # Ollama ModelFile 生成
├── cli.py                # 命令行接口
├── utils.py              # 工具函数
└── requirements.txt      # 依赖列表

scripts/
└── download_model.py     # 入口脚本
```

## 前置要求

- Python 3.10+
- llama.cpp 编译后的 merge-lora 工具（用于合并操作）

## 许可证

MIT
