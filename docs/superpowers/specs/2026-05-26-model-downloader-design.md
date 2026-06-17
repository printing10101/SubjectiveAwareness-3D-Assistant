# 模型下载与处理工具设计文档

> **日期:** 2026-05-26
> **状态:** 已批准

## 概述

开发一个功能完善的模块化模型权重下载与处理工具，用于从 Hugging Face Hub 下载预训练 LoRA 权重文件，验证文件完整性，合并到 GGUF 基础模型中，并生成符合 Ollama 规范的 ModelFile。

## 需求

1. 从 Hugging Face Hub 下载预训练 LoRA 权重文件
2. 集成 SHA256/MD5 文件完整性验证机制
3. 使用 llama.cpp 工具将 LoRA 权重合并到 GGUF 基础模型
4. 自动生成符合 Ollama 规范的 ModelFile
5. 下载进度显示（已下载大小、总大小、速度、ETA）
6. 错误检测与自动重试机制（指数退避）
7. 断点续传功能

## 架构设计

### 目录结构

```
model_downloader/
├── __init__.py           # 包初始化，导出主要接口
├── config.py             # 配置管理
├── downloader.py         # 核心下载器
├── validator.py          # 文件完整性验证
├── merger.py             # LoRA 权重合并
├── modelfile.py          # Ollama ModelFile 生成
├── cli.py                # 命令行接口
└── utils.py              # 工具函数

scripts/
└── download_model.py     # 入口脚本

requirements.txt          # 依赖列表
```

### 模块职责

**config.py** - 配置管理
- 定义数据类存储配置信息
- 模型仓库 ID、本地路径、校验算法等
- 默认配置与用户自定义配置合并

**downloader.py** - 核心下载器
- 使用 huggingface_hub API 下载
- tqdm 进度条（速度、ETA、已下载/总大小）
- HTTP Range 请求实现断点续传
- 指数退避重试策略（最多3-5次）
- 网络异常、超时、连接错误处理

**validator.py** - 文件验证
- SHA256 和 MD5 校验支持
- 从 Hugging Face 读取文件 hash 元数据
- 下载完成后自动验证

**merger.py** - 权重合并
- 调用 llama.cpp/merge-lora 工具
- 支持指定基础模型路径和输出路径
- 验证合并结果

**modelfile.py** - ModelFile 生成
- 生成 Ollama 规范的 ModelFile
- 包含模型参数、系统提示、模板

**cli.py** - 命令行接口
- typer 构建现代化 CLI
- 子命令：download, validate, merge, generate-modelfile, all

**utils.py** - 工具函数
- 日志配置
- 错误处理辅助函数

## 数据流

```
用户输入 → CLI → 下载 → 验证 → 合并 → 生成ModelFile → 完成
                ↓         ↓        ↓
              断点续传   SHA256   llama.cpp
              重试机制   校验     工具调用
```

## 依赖项

```
huggingface_hub>=0.20.0
tqdm>=4.65.0
typer>=0.9.0
requests>=2.31.0
loguru>=0.7.0  (可选，更好的日志)
```

## 错误处理策略

- 网络错误：重试 + 指数退避
- 文件损坏：验证失败后重新下载
- llama.cpp 不存在：提示用户安装
- 配置错误：明确的错误消息

## 测试策略

- 单元测试：验证器、配置解析、ModelFile 生成
- 集成测试：下载流程（使用 mock）
- 手动测试：实际下载和合并
