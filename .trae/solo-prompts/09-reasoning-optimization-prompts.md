# 推理能力优化提示词集合

本文档包含 5 个优化方案的提示词，每个方案包含分步骤的实施指令和对应的检验方法。
按优先级排序：方案1（Prompt CoT）→ 方案2（参数优化）→ 方案3（维度串行）→ 方案4（Self-Consistency）→ 方案5（知识图谱增强）。

---

## 方案 1：Prompt 重构 — 启用 DeepSeek-R1 思维链推理

**目标**：利用 DeepSeek-R1 的原生 `<think/>` 能力，让模型先逐步推理再输出 JSON，提升推理准确率。

**涉及文件**：`backend/app/services/prompts.py`、`backend/app/services/ollama_client.py`

### 提示词

```
你是法律 AI 提示词工程师，精通 DeepSeek-R1 模型的思维链推理机制。

【任务】
重构分析管线的 prompt 模板和 JSON 解析逻辑，启用 DeepSeek-R1 的思维链推理能力。

【当前问题】
1. prompts.py 中所有 prompt 直接要求模型输出 JSON，没有任何思维链引导
2. ollama_client.py 的 generate_json() 直接从响应中提取 JSON，不处理 <think/> 标签
3. DeepSeek-R1 的推理能力完全被浪费

【步骤 1：修改 ANALYSIS_SYSTEM_PROMPT】

文件：backend/app/services/prompts.py，第 6-46 行

将当前的 ANALYSIS_SYSTEM_PROMPT 替换为包含思维链引导的版本。

要求：
- 在要求输出 JSON 之前，明确要求模型按固定步骤进行推理
- 推理步骤应覆盖：事实提取 → 要件匹配 → 证据评估 → 矛盾识别 → 法律适用 → 综合判断
- 告知模型可以使用 <think/> 标签来组织推理过程
- 最终输出仍为 JSON 格式
- 保持原有的三维度分析框架不变

参考结构（不要照搬，根据法律分析场景优化）：
```
你是一个专业的刑事案件分析助手。

【重要】在给出最终 JSON 结论之前，你必须先进行逐步推理分析。
你可以使用 <think</think 标签来组织你的推理过程。

推理步骤要求：
第一步：事实提取 — 从案件描述中提取所有关键事实
第二步：要件匹配 — 将事实与法律要件逐一对照
第三步：证据评估 — 评估证据的可靠性和完整性
...（根据法律分析场景补充完整）

推理完成后，请以 JSON 格式输出最终结论：
{...原有 JSON 格式保持不变...}
```

【步骤 2：修改三个维度 prompt】

文件：backend/app/services/prompts.py，第 48-86 行

对 DIMENSION1_PROMPT、DIMENSION2_PROMPT、DIMENSION3_PROMPT 做同样的修改：
- 在要求输出 JSON 之前，添加该维度专属的推理步骤引导
- 维度1（事实审查）：先列出关键事实清单，再逐一匹配要件
- 维度2（模式匹配）：先描述行为特征，再与典型模式对比
- 维度3（矛盾分析）：先列出各方陈述，再逐对比较找矛盾
- 保持最终 JSON 输出格式不变

【步骤 3：修改 generate_json() 处理 <think/> 标签】

文件：backend/app/services/ollama_client.py，第 148-175 行

当前 generate_json() 直接从 raw 响应中查找 { 和 } 来提取 JSON。
DeepSeek-R1 的响应格式为：<think推理过程</thinkJSON结果。

修改要求：
1. 在提取 JSON 之前，先用正则表达式提取 <think...</think 中的推理过程
2. 将推理过程保存到返回结果中（新增 reasoning_process 字段）
3. 从 </think 之后的内容中提取 JSON
4. 如果没有 <think/> 标签，保持原有逻辑不变（兼容其他模型）
5. 推理过程应作为元数据返回，不影响原有 JSON 解析逻辑

具体实现思路：
- 在 OllamaClient 类中新增一个方法 _extract_think_content(raw: str) -> tuple[str, str]
  返回 (reasoning_text, json_text)
- 修改 generate_json()，先调用 _extract_think_content，再从 json_text 中解析 JSON
- 将 reasoning_text 附加到返回结果中

【步骤 4：修改 pipeline.py 保存推理过程】

文件：backend/app/services/pipeline.py

在 multi_dimension_analysis() 和 single_pass_analysis() 的返回结果中，
新增 "reasoning_process" 字段，保存从 <think/> 中提取的推理过程。

修改 _single_dimension_analysis()（第 625-653 行）：
- 接收 call_ollama_with_retry 返回的完整响应
- 调用 _extract_think_content 分离推理过程和 JSON
- 将推理过程存入维度结果的 "reasoning_process" 字段

注意：需要修改 call_ollama_with_retry 或 _single_dimension_analysis 的调用方式，
使其能获取到原始响应文本而非仅解析后的 JSON。

【检验方法】

检验 1.1 — 验证 prompt 包含思维链引导：
```bash
cd backend
grep -n "think\|逐步\|推理步骤\|第一步\|第二步" app/services/prompts.py
```
预期：ANALYSIS_SYSTEM_PROMPT 和三个 DIMENSION_PROMPT 中都出现推理步骤引导

检验 1.2 — 验证 <think/> 标签处理逻辑：
```bash
grep -n "think\|_extract_think" app/services/ollama_client.py
```
预期：有 _extract_think_content 方法或等效的正则提取逻辑

检验 1.3 — 验证推理过程保存到结果中：
```bash
grep -n "reasoning_process" app/services/pipeline.py
```
预期：在分析结果中有 reasoning_process 字段

检验 1.4 — 端到端功能测试：
启动 Ollama 服务后，执行一次案件分析：
```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"case_text": "被告人张三于2024年1月15日在某超市盗窃价值500元的商品，被当场抓获。", "mode": "multi"}'
```
检查返回的 JSON 中：
- dimension1/dimension2/dimension3 是否都包含 reasoning_process 字段
- reasoning_process 是否包含结构化的推理文本（而非空或 JSON 片段）
- score 和 reasoning 字段是否正常

检验 1.5 — 兼容性测试（如果切换到非 DeepSeek-R1 模型）：
临时将 OLLAMA_MODEL 改为其他模型（如 qwen2.5:7b），执行同样的分析，
确认没有 <think/> 标签时仍能正常解析 JSON。
```

---

## 方案 2：生成参数优化

**目标**：优化 Ollama 调用参数，减少输出截断和重复，提升 JSON 解析成功率。

**涉及文件**：`backend/app/config.py`、`backend/app/services/ollama_client.py`

### 提示词

```
你是 LLM 推理优化工程师，精通 Ollama 模型参数调优。

【任务】
优化 Ollama 生成参数配置，提升推理输出质量。

【当前配置】
文件：backend/app/config.py，第 111-115 行
```python
OLLAMA_NUM_CTX: int = 4096
OLLAMA_DEFAULT_TEMPERATURE: float = 0.3
OLLAMA_PIPELINE_TIMEOUT: float = 60.0
```

文件：backend/app/services/ollama_client.py，第 87-95 行
```python
payload = {
    "model": model or settings.OLLAMA_MODEL,
    "prompt": prompt,
    "stream": False,
    "options": {
        "temperature": temperature,
        "num_ctx": AnalysisConfig.OLLAMA_NUM_CTX,
    },
}
```

【步骤 1：在 config.py 中新增参数】

在 OLLAMA_DEFAULT_TEMPERATURE 之后（第 113 行后），添加以下配置项：

```python
OLLAMA_TOP_P: float = 0.9
OLLAMA_NUM_PREDICT: int = 4096
OLLAMA_REPEAT_PENALTY: float = 1.15
```

同时修改 OLLAMA_NUM_CTX：
```python
OLLAMA_NUM_CTX: int = 8192  # 从 4096 提升到 8192
```

并修改 OLLAMA_DEFAULT_TEMPERATURE：
```python
OLLAMA_DEFAULT_TEMPERATURE: float = 0.2  # 从 0.3 降低到 0.2，提高推理确定性
```

【步骤 2：在 ollama_client.py 中使用新参数】

修改 generate() 方法中的 payload 构造（第 87-95 行），
在 options 字典中添加新参数：

```python
"options": {
    "temperature": temperature,
    "num_ctx": AnalysisConfig.OLLAMA_NUM_CTX,
    "top_p": AnalysisConfig.OLLAMA_TOP_P,
    "num_predict": AnalysisConfig.OLLAMA_NUM_PREDICT,
    "repeat_penalty": AnalysisConfig.OLLAMA_REPEAT_PENALTY,
},
```

注意：仅添加新参数，不改变原有的 temperature 和 num_ctx 逻辑。

【步骤 3：验证参数传递】

确保新参数被正确传递到 Ollama API 的 payload 中。

【检验方法】

检验 2.1 — 验证 config.py 新增参数：
```bash
cd backend
grep -n "OLLAMA_TOP_P\|OLLAMA_NUM_PREDICT\|OLLAMA_REPEAT_PENALTY\|OLLAMA_NUM_CTX\|OLLAMA_DEFAULT_TEMPERATURE" app/config.py
```
预期：
- OLLAMA_NUM_CTX = 8192
- OLLAMA_DEFAULT_TEMPERATURE = 0.2
- OLLAMA_TOP_P = 0.9
- OLLAMA_NUM_PREDICT = 4096
- OLLAMA_REPEAT_PENALTY = 1.15

检验 2.2 — 验证 payload 包含新参数：
```bash
grep -n "top_p\|num_predict\|repeat_penalty" app/services/ollama_client.py
```
预期：generate() 方法的 payload options 中包含这三个参数

检验 2.3 — 语法检查：
```bash
python -m py_compile app/config.py
python -m py_compile app/services/ollama_client.py
```
预期：无错误

检验 2.4 — 运行现有测试：
```bash
pytest tests/test_pipeline.py tests/test_ollama_client.py -v
```
预期：所有测试通过

检验 2.5 — 实际调用验证：
启动 Ollama 后，执行一次简单分析，检查：
- 返回的 JSON 是否完整（无截断）
- 推理文本是否无重复内容
- 响应时间是否在合理范围内（num_ctx 翻倍可能略增加延迟）
```

---

## 方案 3：维度间信息传递 — 两阶段串行推理

**目标**：将三个维度的纯并行分析改为两阶段（先并行维度1+2，再串行维度3），让矛盾分析能引用事实审查和模式匹配的结果。

**涉及文件**：`backend/app/services/pipeline.py`、`backend/app/services/prompts.py`

### 提示词

```
你是法律 AI 系统架构师。

【任务】
将 multi_dimension_analysis() 从三维度纯并行改为两阶段推理，
使维度3（矛盾分析）能接收维度1（事实审查）和维度2（模式匹配）的分析结果。

【当前实现】
文件：backend/app/services/pipeline.py，第 714-794 行

三个维度完全并行（第 734-745 行）：
```python
gather_results = await asyncio.gather(
    _timed_dimension_analysis(case_text, DIMENSION1_PROMPT, "维度1"),
    _timed_dimension_analysis(case_text, DIMENSION2_PROMPT, "维度2"),
    _timed_dimension_analysis(case_text, DIMENSION3_PROMPT, "维度3"),
    return_exceptions=True,
)
```

维度之间零信息共享。

【步骤 1：修改 DIMENSION3_PROMPT 支持接收前置分析结果】

文件：backend/app/services/prompts.py，第 75-86 行

在 DIMENSION3_PROMPT 中新增一个可选的上下文段落：

修改后的 DIMENSION3_PROMPT 应支持两种模式：
- 无前置结果时：保持原有行为
- 有前置结果时：在案件文本之前插入前置分析摘要

使用 Python 格式化字符串，新增 {prior_analysis} 占位符：
```python
DIMENSION3_PROMPT = """请分析以下案件的矛盾分析维度：

{prior_analysis}

案件原文：
{case_text}

请基于上述前置分析结果，重点分析：
1. 识别嫌疑人辩解与证据的矛盾
2. 分析前置分析中可能存在的逻辑不一致之处
3. 评估辩解的可信度

返回JSON格式：
{{
  "score": 数值(0-10),
  "reasoning": "详细分析理由",
  "contradictions": ["矛盾点列表"]
}}
"""
```

注意：{prior_analysis} 在无前置结果时应为空字符串或省略提示语。

【步骤 2：新增辅助函数 _build_prior_analysis_context()】

文件：backend/app/services/pipeline.py

在 multi_dimension_analysis() 之前，新增一个函数：

```python
def _build_prior_analysis_context(
    dim1_result: dict[str, Any],
    dim2_result: dict[str, Any],
) -> str:
    """将维度1和维度2的结果摘要为维度3可用的上下文."""
```

该函数应：
- 从 dim1_result 中提取 score、reasoning、key_indicators
- 从 dim2_result 中提取 score、reasoning、pattern_match
- 格式化为简洁的文本摘要（不超过 500 字）
- 如果某个维度失败（使用了默认值），在摘要中标注"该维度分析失败，请独立判断"

【步骤 3：重构 multi_dimension_analysis() 为两阶段】

文件：backend/app/services/pipeline.py，第 714-794 行

修改 multi_dimension_analysis()：

第一阶段（并行）：执行维度1和维度2
```python
phase1_results = await asyncio.gather(
    _timed_dimension_analysis(case_text, DIMENSION1_PROMPT, "维度1"),
    _timed_dimension_analysis(case_text, DIMENSION2_PROMPT, "维度2"),
    return_exceptions=True,
)
```

处理第一阶段结果，构建上下文：
```python
context = _build_prior_analysis_context(dim1_result, dim2_result)
```

第二阶段（串行）：将上下文注入维度3
```python
enriched_prompt = DIMENSION3_PROMPT.format(
    prior_analysis=context,
    case_text=case_text,
)
dim3_result, dim3_timing = await _timed_dimension_analysis(
    case_text, enriched_prompt, "维度3"
)
```

注意：
- 需要修改 _timed_dimension_analysis 或 _single_dimension_analysis，
  使其能接受完整的 prompt 字符串（而非仅 case_text）
- 或者新增一个 _dimension_analysis_with_prompt() 函数
- 保持返回结果的数据结构不变（AnalysisResult），确保下游兼容

【步骤 4：更新 single_pass_analysis() 的 prompt】

文件：backend/app/services/pipeline.py，第 599-622 行

single_pass_analysis() 用于简单案件，保持单次调用不变。
但在 ANALYSIS_SYSTEM_PROMPT 中（已在方案1中修改），
确保思维链引导中包含"先分析事实和模式，再基于前两步结果进行矛盾分析"的提示。

【检验方法】

检验 3.1 — 验证 DIMENSION3_PROMPT 包含 prior_analysis 占位符：
```bash
cd backend
grep -n "prior_analysis\|前置分析" app/services/prompts.py
```
预期：DIMENSION3_PROMPT 中有 {prior_analysis} 占位符

检验 3.2 — 验证两阶段执行逻辑：
```bash
grep -n "phase1\|phase2\|阶段\|_build_prior_analysis" app/services/pipeline.py
```
预期：multi_dimension_analysis() 中有明显的两阶段结构

检验 3.3 — 验证维度3不再在 gather 中：
```bash
grep -A 10 "asyncio.gather" app/services/pipeline.py
```
预期：gather 只包含维度1和维度2，维度3在 gather 之后单独执行

检验 3.4 — 语法检查：
```bash
python -m py_compile app/services/pipeline.py
python -m py_compile app/services/prompts.py
```
预期：无错误

检验 3.5 — 功能测试：
执行一次多维度分析，检查返回结果中：
- dimension3 的 reasoning 是否引用了 dimension1 和 dimension2 的发现
- dimension3 的 contradictions 是否更具体、更有依据
- 三个维度的元数据（dimension_meta）都正常记录了耗时

检验 3.6 — 异常隔离测试：
模拟维度1失败的场景，确认：
- 维度3 仍能正常执行（prior_analysis 中标注了维度1失败）
- 维度3 的结果不依赖维度1 的具体内容
```

---

## 方案 4：Self-Consistency 多次采样验证

**目标**：对同一案件执行多次推理，通过多数投票提升结果稳定性，并输出置信度指标。

**涉及文件**：`backend/app/services/pipeline.py`、`backend/app/config.py`

### 提示词

```
你是法律 AI 系统工程师，精通 LLM 推理结果验证技术。

【任务】
为分析管线添加 Self-Consistency（自洽性）多次采样验证机制。

【当前问题】
- 所有分析只执行一次 LLM 调用，无结果稳定性保障
- 单次推理可能因随机性产生偏差，尤其在边界案例上

【步骤 1：在 config.py 中添加 Self-Consistency 配置】

文件：backend/app/config.py

在分析相关配置区域（约第 117 行后）添加：
```python
# Self-Consistency 多次采样配置
SC_ENABLED: bool = True              # 是否启用多次采样
SC_NUM_SAMPLES: int = 3              # 采样次数
SC_TEMPERATURE: float = 0.5          # 采样温度（高于默认值以引入多样性）
SC_MIN_AGREEMENT: float = 0.6        # 最低一致性阈值（低于此值标记为"低置信度"）
```

注意：SC_TEMPERATURE 应高于 OLLAMA_DEFAULT_TEMPERATURE（0.2），
以在多次采样中引入足够的多样性。

【步骤 2：新增 self_consistency_analysis() 函数】

文件：backend/app/services/pipeline.py

在 multi_dimension_analysis() 之后，新增函数：

```python
async def self_consistency_analysis(
    case_text: str,
    mode: str = "auto",
    n_samples: int = 3,
    sample_temperature: float = 0.5,
) -> AnalysisResult:
```

该函数应：
1. 循环调用 n_samples 次 multi_dimension_analysis()（或 single_pass_analysis()）
   - 每次使用 sample_temperature 而非默认温度
2. 收集所有采样结果
3. 对每个维度的 score 取中位数（median）作为最终分数
4. 计算每个维度的评分一致性（所有采样评分的标准差或极差）
5. 合并所有采样的 reasoning 文本（去重、取最具代表性的）
6. 计算整体置信度（基于三个维度的一致性综合评估）
7. 在返回结果中新增以下字段：
   - "confidence": float — 整体置信度（0-1）
   - "confidence_details": dict — 各维度的一致性详情
   - "num_samples": int — 实际采样次数
   - "sample_scores": list — 所有采样的原始评分

【步骤 3：修改 analyze_pipeline() 路由】

文件：backend/app/services/pipeline.py，第 797 行开始的 analyze_pipeline()

在 analyze_pipeline() 中，根据配置决定是否使用 Self-Consistency：

```python
if AnalysisConfig.SC_ENABLED and mode != "single":
    return await self_consistency_analysis(case_text, mode=mode)
else:
    # 原有逻辑不变
```

注意：simple 模式不启用 SC（简单案件不需要多次采样）。

【步骤 4：修改 API 响应 Schema】

文件：backend/app/schemas/analysis.py 或 backend/app/types/analysis.py

在分析结果类型中添加可选字段：
- confidence: float | None = None
- confidence_details: dict | None = None
- num_samples: int | None = None

确保这些字段是可选的（Optional），不影响现有响应格式。

【检验方法】

检验 4.1 — 验证配置项：
```bash
cd backend
grep -n "SC_ENABLED\|SC_NUM_SAMPLES\|SC_TEMPERATURE\|SC_MIN_AGREEMENT" app/config.py
```
预期：四个配置项都存在且值合理

检验 4.2 — 验证 self_consistency_analysis 函数：
```bash
grep -n "self_consistency_analysis\|median\|confidence\|num_samples" app/services/pipeline.py
```
预期：函数存在，且包含中位数计算和置信度评估逻辑

检验 4.3 — 验证 analyze_pipeline 路由：
```bash
grep -n "SC_ENABLED" app/services/pipeline.py
```
预期：analyze_pipeline() 中有 SC_ENABLED 的条件判断

检验 4.4 — 语法检查：
```bash
python -m py_compile app/services/pipeline.py
python -m py_compile app/config.py
```
预期：无错误

检验 4.5 — 功能测试（需要 Ollama 运行）：
将 SC_NUM_SAMPLES 设为 2（减少测试时间），执行一次分析：
```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"case_text": "测试案件文本...", "mode": "multi"}'
```
检查返回结果中：
- confidence 字段存在且为 0-1 之间的数值
- confidence_details 包含三个维度各自的一致性信息
- num_samples 等于配置的采样次数
- score 与不启用 SC 时的结果偏差在合理范围内

检验 4.6 — 一致性验证：
对同一案件执行 2 次分析（都启用 SC），比较两次的最终 score：
- 两次的 score 差异应明显小于不启用 SC 时的差异
- confidence 高的案件，两次结果应非常接近

检验 4.7 — 性能测试：
记录启用 SC 前后的响应时间：
- SC_NUM_SAMPLES=3 时，响应时间应约为原来的 3 倍
- 如果超时，考虑增加 OLLAMA_PIPELINE_TIMEOUT
```

---

## 方案 5：知识图谱增强推理

**目标**：在分析管线中集成知识图谱检索，将相关法律条文和判例注入 prompt 上下文，减少 LLM 幻觉。

**涉及文件**：`backend/app/services/pipeline.py`、`backend/app/services/prompts.py`、`backend/app/services/knowledge_qa_service.py`

### 提示词

```
你是法律 AI 系统架构师，精通知识图谱增强的 LLM 推理（GraphRAG）。

【任务】
在分析管线中集成知识图谱检索，分析前先从知识库中检索相关法律知识，注入 prompt 上下文。

【当前问题】
- 分析管线（pipeline.py）与知识图谱模块（knowledge_graph_service.py、knowledge_qa_service.py）完全隔离
- 推理完全依赖 LLM 的参数化知识，可能产生法律条文引用错误

【步骤 1：新增知识检索函数】

文件：backend/app/services/pipeline.py

在 analyze_pipeline() 之前，新增函数：

```python
async def _retrieve_legal_knowledge(
    case_text: str,
    max_entries: int = 5,
) -> str:
    """从知识库中检索与案件相关的法律知识.

    Args:
        case_text: 案件文本
        max_entries: 最大返回条目数

    Returns:
        str: 格式化的相关知识文本，用于注入 prompt。
             如果知识库为空或 Neo4j 未配置，返回空字符串。
    """
```

该函数应：
1. 检查 Neo4j 是否可用（NEO4J_URI 不为 None）
2. 如果不可用，直接返回空字符串（优雅降级）
3. 从案件文本中提取关键词（复用已有的复杂度评估中的关键词列表）
4. 调用知识库搜索接口（参考 knowledge_qa_service.py 的实现）
5. 获取与关键词最相关的知识条目（标题 + 摘要）
6. 格式化为简洁的文本：
```
【相关知识】
1. [法律条文标题] 摘要内容...
2. [判例标题] 摘要内容...
3. [法律概念标题] 摘要内容...
```
7. 控制总长度不超过 1000 字（避免占用过多上下文窗口）

注意：需要处理 Neo4j 未配置、知识库为空、搜索超时等异常情况，
任何异常都应优雅降级为空字符串，不阻塞分析流程。

【步骤 2：修改 ANALYSIS_SYSTEM_PROMPT 支持知识注入】

文件：backend/app/services/prompts.py

在 ANALYSIS_SYSTEM_PROMPT 中新增一个可选段落：

```
{legal_knowledge}

【重要】以上相关知识仅供参考。如果相关知识与你对案件的分析有冲突，
以案件事实为准，但请在推理中说明你的判断依据。
```

使用 {legal_knowledge} 占位符，在无知识时为空字符串。

【步骤 3：修改各维度 prompt 支持知识注入】

在 DIMENSION1_PROMPT、DIMENSION2_PROMPT、DIMENSION3_PROMPT 中，
同样新增 {legal_knowledge} 占位符（放在案件文本之前）。

但注意：只有维度1（事实审查）最需要法律条文参考，
维度2和维度3可以只传入精简版知识或不传入。

【步骤 4：修改 analyze_pipeline() 集成知识检索】

文件：backend/app/services/pipeline.py，第 797 行开始的 analyze_pipeline()

在复杂度评估之后、调用分析函数之前，插入知识检索步骤：

```python
# 检索相关知识
legal_knowledge = await _retrieve_legal_knowledge(case_text)

# 将知识注入 prompt
if legal_knowledge:
    # 修改 system prompt 或 user prompt，注入知识
    ...
```

具体实现方式有两种选择：
A. 修改 system_prompt（推荐）：在 ANALYSIS_SYSTEM_PROMPT 中注入
B. 修改 user_prompt：在 case_text 之前添加知识段落

选择方案 A，因为知识是全局参考信息，不属于案件文本的一部分。

【步骤 5：确保优雅降级】

在整个知识检索链路中，任何环节失败都不应阻塞分析：
- Neo4j 未配置 → 跳过检索，正常分析
- 知识库为空 → 跳过检索，正常分析
- 检索超时 → 跳过检索，正常分析（记录警告日志）
- 格式化失败 → 使用空字符串，正常分析

在返回的 AnalysisResult 中新增字段：
- "knowledge_used": bool — 是否使用了知识图谱增强
- "knowledge_entries": list — 使用的知识条目摘要

【检验方法】

检验 5.1 — 验证知识检索函数：
```bash
cd backend
grep -n "_retrieve_legal_knowledge\|legal_knowledge\|knowledge_used" app/services/pipeline.py
```
预期：函数存在，且在 analyze_pipeline() 中被调用

检验 5.2 — 验证 prompt 占位符：
```bash
grep -n "legal_knowledge" app/services/prompts.py
```
预期：ANALYSIS_SYSTEM_PROMPT 和至少 DIMENSION1_PROMPT 中有 {legal_knowledge}

检验 5.3 — 验证优雅降级：
临时将 NEO4J_URI 设为 None，执行分析：
```bash
# 在 .env 中设置 NEO4J_URI=
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"case_text": "测试案件...", "mode": "multi"}'
```
预期：分析正常完成，knowledge_used=false，无报错

检验 5.4 — 验证知识注入效果（需要 Neo4j 和知识库数据）：
如果 Neo4j 已配置且有知识数据：
1. 执行分析，检查返回结果中 knowledge_used=true
2. 检查 reasoning 中是否引用了具体的法律条文或判例
3. 对比有/无知识注入时的分析结果，评估法律引用准确性

检验 5.5 — 验证上下文长度控制：
```bash
grep -n "max_entries\|1000\|长度限制\|len(legal" app/services/pipeline.py
```
预期：有明确的长度控制逻辑

检验 5.6 — 语法检查：
```bash
python -m py_compile app/services/pipeline.py
python -m py_compile app/services/prompts.py
```
预期：无错误

检验 5.7 — 运行测试：
```bash
pytest tests/test_pipeline.py -v
```
预期：所有测试通过（测试中 Neo4j 不可用时应优雅降级）
```

---

## 综合检验清单

完成所有 5 个方案后，执行以下综合验证：

```bash
cd backend

# ===== 语法检查 =====
python -m py_compile app/services/prompts.py
python -m py_compile app/services/ollama_client.py
python -m py_compile app/services/pipeline.py
python -m py_compile app/config.py

# ===== 静态检查 =====
ruff check app/services/prompts.py app/services/ollama_client.py app/services/pipeline.py app/config.py

# ===== 单元测试 =====
pytest tests/test_pipeline.py tests/test_ollama_client.py -v

# ===== 端到端验证（需要 Ollama 运行）=====
# 1. 基础分析测试
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"case_text": "被告人张三于2024年1月15日在某超市盗窃价值500元的商品。", "mode": "multi"}'

# 验证返回结果包含：
# - ground_truth_analysis.dimension1.reasoning_process（思维链）
# - confidence（自洽性置信度）
# - knowledge_used（知识图谱增强标记）
# - dimension_meta.dimension3 的耗时应大于维度1（串行执行）

# 2. 参数验证
# 检查 Ollama 请求日志，确认 payload 中包含 top_p、num_predict、repeat_penalty
# 检查 num_ctx 为 8192

# 3. 回归测试
# 使用相同的案件文本，对比优化前后的分析结果：
# - 优化后的 reasoning 应更详细、更有条理
# - 优化后的 score 应更稳定（多次执行偏差更小）
# - 优化后的矛盾分析应引用具体的事实和证据
```
