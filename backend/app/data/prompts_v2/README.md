# V2 提示词模板目录

本目录管理**阶段 4：推理引擎重构**后使用的 V2 协议提示词模板。

## 与 V1 的差异

| 项 | V1 (`backend/app/data/prompts.json`) | V2 (`backend/app/data/prompts_v2/prompts.json`) |
| --- | --- | --- |
| 输出形式 | 0-10 评分 | T1-T4 档级（T1 较轻 → T4 特别严重） |
| 推理步骤 | 6 步（含 6=综合判断） | 5 步（事实清单 → 主观明知 → 客观行为 → 要件齐备 → 档级判定） |
| 整合规则 | 无 | `triggered_rules` 注入 + 命中 ID 列表回传 |
| 整合标签 | 无 | `matched_tags` 注入 |
| 整合冲突 | 无 | 维度间一致性 / 规则互斥 / 证据缺失 |
| 文档位置 | `app/services/prompts.py` | `app/services/prompts.py`（运行时）+ 本目录（配置化） |
| 协议版本 | `1.0` | `2.0` |

## 文件清单

- `prompts.json`：主模板文件，包含 tier_legend、3 个 dimension、tag_extraction、rule_injection、conclusion。

## 渲染占位符

模板使用 `${name}` 占位符，调用方在渲染时需替换：

- `${tier_legend}` → 档级说明（从 `tier_legend.content` 注入）
- `${case_text}` → 案件事实
- `${matched_tags}` → 已抽取的标签列表（JSON / 文本）
- `${triggered_rules}` → 已命中的规则列表
- `${prior_dim1}` / `${prior_dim2}` → 维度 1 / 2 的前置推理文本
- `${legal_knowledge}` → 检索到的法律知识片段
- `${final_tier}` / `${final_label}` / `${sentence_band}` → 组合器结论
- `${dim1_tier}` / `${dim2_tier}` / `${dim3_tier}` → 各维度档级
- `${conflicts}` → 冲突列表文本
- `${tag_candidates}` / `${rule_candidates}` → 候选标签/规则序列化

## 加载器

- 运行期：`from app.services.prompts import V2_DIMENSION1_PROMPT, …`（已与 V1 共存）。
- 配置期：使用 `prompt_manager.py` 中的 `PromptManager` 加载本目录 JSON，模板 ID 形如 `v2.dimensions.dimension1`。

## 向后兼容

V1 数据读取路径不变（`version` 字段缺失视为 v1）。
