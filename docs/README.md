# 帮信罪主观明知分析系统 - 技术文档

## 文档概述

本文档套件全面介绍了**帮信罪主观明知分析系统 V1.0** 的架构设计、API 接口、部署运维、AI 模型、知识图谱以及用户操作指南。本系统是一款专用于帮助信息网络犯罪活动罪（帮信罪）案件分析的司法智能辅助系统，通过大语言模型（LLM）与知识图谱技术，辅助司法人员对案件中的"主观明知"要素进行标准化、多维度的智能分析。

## 文档目录结构

```
docs/
├── README.md              # 本文档入口文件
├── architecture.md        # 系统架构说明
├── api_reference.md       # API 接口文档
├── deployment.md          # 部署运维指南
├── model.md               # AI 模型说明
├── knowledge_graph.md     # 知识图谱说明
└── user_guide.md          # 用户操作手册
```

## 文档内容简介

| 文档 | 主要内容 | 目标读者 |
|------|---------|---------|
| [architecture.md](architecture.md) | 五层系统架构图、模块职责、核心数据流、技术选型说明 | 架构师、开发者 |
| [api_reference.md](api_reference.md) | 全部 RESTful API 的路径、方法、参数、响应格式、错误码及示例 | 前端开发者、集成工程师 |
| [deployment.md](deployment.md) | 环境要求、安装步骤、配置文件说明、常见问题排查 | 运维工程师 |
| [model.md](model.md) | 基础模型选型、LoRA 微调方法、训练参数配置、数据集、评估指标与结果 | ML 工程师 |
| [knowledge_graph.md](knowledge_graph.md) | 三层图结构设计、节点/关系类型、数据导入流程、Cypher 查询示例 | 知识图谱开发者 |
| [user_guide.md](user_guide.md) | 各功能页面的操作步骤、功能说明、界面导览 | 最终用户（检察官/法官） |

## 阅读指引

- **初次接触系统**：建议按顺序阅读 architecture.md → deployment.md → user_guide.md
- **开发与集成**：重点关注 architecture.md 和 api_reference.md
- **模型优化**：阅读 model.md 了解训练流程与评估方法
- **运维部署**：以 deployment.md 为主，参考 architecture.md 理解依赖关系

## 相关资源

- **项目源码**: `/backend`（FastAPI 后端）、`/frontend`（Vue 3 前端）
- **AI 模型**: `/models/merged_model`（Ollama Modelfile）
- **训练脚本**: `/scripts/train_lora.py`、`/scripts/evaluate_model.py`
- **实验数据**: `/research/`（回溯性对比实验方案与结果）
- **原始数据**: `/data/raw/`（爬取的裁判文书，99 份）
