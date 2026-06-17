# 模块C：Ruflo/Claude-Flow 智能编排参考文档

## 概述

Ruflo (Claude-Flow V3) 是企业级多智能体协作平台。6000+提交、314个MCP工具、16种智能体角色、19个AgentDB控制器、21个原生插件。

## 核心理念

```
编排层：CLAUDE-FLOW  = 状态追踪 + 记忆 + 协调
执行层：执行者       = 写代码 + 运行命令 + 创建文件
```

**规则：编排层不执行代码，执行层干所有实际工作。**

## 智能体类型全表

### 核心开发

| 类型 | 职责 |
|------|------|
| `coordinator` | 多智能体协调与调度 |
| `coder` | 代码编写与实现 |
| `tester` | 测试编写与验证 |
| `reviewer` | 代码审查与质量保障 |
| `architect` | 系统架构设计 |
| `researcher` | 需求分析与技术调研 |

### 专项智能体

| 类型 | 职责 |
|------|------|
| `security-architect` | 安全架构设计 |
| `security-auditor` | 安全审计 |
| `performance-engineer` | 性能优化 |
| `memory-specialist` | 记忆管理 |
| `api-docs` | API文档编写 |
| `system-architect` | 系统设计 |

### 共识与分布式

| 类型 | 职责 |
|------|------|
| `byzantine-coordinator` | 拜占庭容错协调 |
| `raft-manager` | Raft共识管理 |
| `gossip-coordinator` | Gossip协议协调 |
| `crdt-synchronizer` | CRDT同步 |

### GitHub自动化

| 类型 | 职责 |
|------|------|
| `pr-manager` | PR管理 |
| `code-review-swarm` | 代码审查 |
| `issue-tracker` | 问题追踪 |
| `release-manager` | 发布管理 |
| `workflow-automation` | 工作流自动化 |

## Swarm编排

### 拓扑结构

| 拓扑 | 用途 | 命令 |
|------|------|------|
| `hierarchical` | 分层协调、反漂移（推荐默认） | `--topology hierarchical` |
| `mesh` | 点对点、无中心 | `--topology mesh` |
| `hierarchical-mesh` | 混合模式（V3推荐） | `--topology hierarchical-mesh` |
| `ring` | 顺序处理 | `--topology ring` |
| `star` | 中心协调 | `--topology star` |
| `adaptive` | 动态切换 | `--topology adaptive` |

### 何时使用Swarm

**使用Swarm**（任务复杂度>30%）：
- 多文件修改（3+）
- 新功能实现
- 跨模块重构
- API变更+测试
- 安全相关变更

**不使用Swarm**：
- 单文件编辑
- 简单Bug修复（1-2行）
- 文档更新
- 配置变更

### Swarm编排模式

#### 基本流水线

```bash
npx claude-flow swarm init --topology hierarchical --max-agents 8
npx claude-flow agent spawn --type coordinator --name lead
npx claude-flow agent spawn --type coder --name coder-1
npx claude-flow agent spawn --type tester --name tester-1
npx claude-flow agent spawn --type reviewer --name reviewer-1
npx claude-flow swarm start --objective "任务描述" --strategy development
```

#### 智能体路由码

| 码 | 任务 | 智能体组合 |
|----|------|-----------|
| 1 | Bug修复 | coordinator, researcher, coder, tester |
| 3 | 功能开发 | coordinator, architect, coder, tester, reviewer |
| 5 | 重构 | coordinator, architect, coder, reviewer |
| 7 | 性能优化 | coordinator, perf-engineer, coder |
| 9 | 安全审计 | coordinator, security-architect, auditor |
| 11 | 记忆管理 | coordinator, memory-specialist, perf-engineer |
| 13 | 文档 | researcher, api-docs |

#### 智能体团队通信

```javascript
// 生成命名智能体并通过SendMessage通信
Task({
  prompt: "设计API架构。完成后SendMessage给'developer'。",
  subagent_type: "system-architect",
  name: "architect",
  run_in_background: true
})
Task({
  prompt: "等待architect的设计。实现代码。SendMessage给'tester'。",
  subagent_type: "coder",
  name: "developer",
  run_in_background: true
})
SendMessage({
  to: "architect",
  summary: "开始设计",
  message: "设计用户管理的REST API，含CRUD端点"
})
```

## 记忆与学习

### 工作流

```
每次任务：
1. LEARN：memory_search(query="关键词", namespace="patterns")
2. COORDINATE：swarm_init(topology="hierarchical")
3. EXECUTE：实际编写代码
4. REMEMBER：memory_store(key="pattern-x", value="成功经验", namespace="patterns")
```

### 记忆命令

```bash
# 存储
npx claude-flow memory store --key "key" --value "value" --namespace patterns

# 搜索（语义搜索，>0.7分=强匹配）
npx claude-flow memory search --query "搜索词"

# 检索
npx claude-flow memory retrieve --key "key"

# 列表
npx claude-flow memory list --namespace patterns
```

### RuVector智能系统

4步流水线：
1. **RETRIEVE** — HNSW语义搜索匹配模式
2. **JUDGE** — 评估判决（成功/失败）
3. **DISTILL** — LoRA提取关键学习
4. **CONSOLIDATE** — EWC++防止灾难性遗忘

## Hooks管道

### 17个Hook分类

| 类别 | Hook | 触发时机 |
|------|------|---------|
| **核心** | pre-edit, post-edit | 编辑前/后 |
| | pre-command, post-command | 命令前/后 |
| | pre-task, post-task | 任务前/后 |
| **会话** | session-start, session-end | 会话开始/结束 |
| | session-restore, notify | 恢复/通知 |
| **智能** | route, explain | 路由/解释 |
| | pretrain, build-agents | 预训练/构建 |
| **学习** | intelligence (轨迹) | 学习过程 |
| **团队** | teammate-idle, task-completed | 智能体闲置/任务完成 |

### 12个后台Worker

| Worker | 优先级 | 说明 |
|--------|--------|------|
| `audit` | critical | 安全分析 |
| `optimize` | high | 性能优化 |
| `ultralearn` | normal | 深度知识获取 |
| `deepdive` | normal | 深度代码分析 |
| `document` | normal | 自动文档生成 |
| `refactor` | normal | 重构建议 |
| `benchmark` | normal | 性能基准测试 |
| `testgaps` | normal | 测试覆盖分析 |
| `map` | normal | 代码库映射 |
| `predict` | normal | 预测预加载 |
| `consolidate` | low | 记忆整合 |
| `preload` | low | 资源预加载 |

### Hook命令

```bash
# 任务Hook
npx claude-flow hooks pre-task --description "任务描述"
npx claude-flow hooks post-task --task-id "id" --success true

# 会话Hook
npx claude-flow hooks session-start --session-id "id"
npx claude-flow hooks session-end --export-metrics true

# Worker管理
npx claude-flow hooks worker list
npx claude-flow hooks worker dispatch --trigger audit
npx claude-flow hooks worker status
```

## 健康检查

```bash
npx claude-flow doctor --fix
```

## Hive-Mind共识

### 共识策略

| 策略 | 容错 | 适用 |
|------|------|------|
| `byzantine` | f < n/3 | 有恶意节点 |
| `raft` | f < n/2 | 标准场景（推荐） |
| `gossip` | 最终一致 | 大规模网络 |
| `crdt` | 自动合并 | 离线优先 |
| `quorum` | 可配 | 自定义多数 |

## 插件系统（21个原生插件）

| 插件 | 说明 |
|------|------|
| `@claude-flow/security` | 输入验证、路径安全、CVE修复 |
| `@claude-flow/embeddings` | 向量嵌入、sql.js、HNSW |
| `@claude-flow/neural` | 神经模式训练（SONA、MoE、EWC++） |
| `@claude-flow/claims` | 基于声明的授权 |
| `@claude-flow/performance` | 性能分析 |

安装：`npx claude-flow plugins install @claude-flow/<name>`

## 环境变量

```bash
CLAUDE_FLOW_CONFIG=./claude-flow.config.json
CLAUDE_FLOW_LOG_LEVEL=info
CLAUDE_FLOW_MEMORY_BACKEND=hybrid
CLAUDE_FLOW_MEMORY_PATH=./data/memory
```
