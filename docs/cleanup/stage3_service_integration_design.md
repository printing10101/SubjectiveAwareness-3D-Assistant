# 阶段 3.1：服务模块整合设计报告

**完成日期**: 2026-06-22  
**分析范围**: backend/app/services 目录下 29 个服务模块（不含 pipeline/ 和 knowledge/ 子目录）

---

## 1. 现状统计

| 指标 | 数值 |
|------|------|
| 服务模块总数 | 29 个 |
| 总代码行数 | 约 10,500 行 |
| 平均文件大小 | 约 362 行 |
| 超过 500 行的文件 | 6 个 |
| 小于 150 行的文件 | 12 个 |

---

## 2. 功能分组与重叠分析

### 2.1 报告服务组（高度重叠，建议合并）

**现有文件**:
- `report_service.py` (100 行) - 报告 CRUD 和分页查询
- `report_generator.py` (220 行) - 结构化报告生成
- `report_exporter.py` (100 行) - PDF/Word 格式导出

**问题**: 三个文件职责紧密相关但分散，调用链复杂  
**建议**: 合并为统一的 `report.py`，内部按功能分子模块

**预计减少**: 2 个文件，约 100 行冗余代码

---

### 2.2 提示词服务组（功能相似，建议合并）

**现有文件**:
- `prompt_manager.py` (390 行) - 提示词加载、热重载、统计
- `prompts.py` (589 行) - V1/V2 协议提示词模板定义

**问题**: 提示词定义和管理分离，维护不便  
**建议**: 合并为 `prompt.py`，模板定义和管理逻辑统一

**预计减少**: 1 个文件，代码量保持约 900 行

---

### 2.3 版本服务组（功能相关，建议合并）

**现有文件**:
- `version_manager.py` (100 行) - 版本信息和升级管理
- `versioned_data_loader.py` (100 行) - 版本化数据加载

**问题**: 版本管理和数据加载紧密相关但分离  
**建议**: 合并为 `version.py`

**预计减少**: 1 个文件

---

### 2.4 数据处理服务组（可优化）

**现有文件**:
- `document_processor.py` (194 行) - 多格式文档文本提取
- `real_judgment_loader.py` (427 行) - 真实判决书解析

**问题**: 都是数据输入处理，但职责差异较大  
**建议**: 暂不合并，但可提取通用的数据验证逻辑

---

### 2.5 主体分析服务组（功能重叠，建议合并）

**现有文件**:
- `multi_subject_analyzer.py` (420 行) - 多主体独立分析
- `subject_stratifier.py` (100 行) - 主体分类处理

**问题**: 都涉及主体分析，职责边界模糊  
**建议**: 合并为 `subject.py`，统一主体分析能力

**预计减少**: 1 个文件

---

### 2.6 核心分析服务组（保持稳定）

**现有文件**:
- `analysis_service.py` (320 行) - 核心分析执行
- `pipeline.py` (2258 行) - 分析管道编排（已拆分到 pipeline/ 子目录）
- `conflict_detector.py` (494 行) - 冲突检测
- `rule_engine.py` (200 行) - 规则引擎
- `tier_combiner.py` (100 行) - 档级组合
- `conclusion_generator.py` (369 行) - 结论生成
- `tag_extractor.py` (100 行) - 标签抽取

**问题**: pipeline.py 仍然很大（2258 行），但已拆分到子目录  
**建议**: 保持现有结构，pipeline.py 可考虑标记为废弃，统一使用 pipeline/ 子目录

---

### 2.7 辅助服务组（独立性强）

**现有文件**:
- `ollama_client.py` (519 行) - LLM 调用客户端
- `experiment.py` (852 行) - A/B 测试
- `case_service.py` (336 行) - 案件管理
- `dedup_service.py` (186 行) - 案件去重
- `boundary_reminder.py` (70 行) - 边界提醒
- `system_service.py` (100 行) - 系统服务
- `review_checklist.py` (200 行) - 审查清单
- `evidence_strength_layer.py` (339 行) - 证据分级
- `sentencing.py` (100 行) - 量刑建议
- `similar_cases.py` (100 行) - 相似案例
- `standard_path_recognizer.py` (100 行) - 标准路径识别

**建议**: 保持独立，部分小文件可考虑合并到相关服务

---

## 3. 合并优先级与计划

### 第一批合并（高优先级，预计减少 4 个文件）

1. **报告服务合并**: report_service + report_generator + report_exporter → report.py
2. **提示词服务合并**: prompt_manager + prompts → prompt.py
3. **版本服务合并**: version_manager + versioned_data_loader → version.py
4. **主体分析合并**: multi_subject_analyzer + subject_stratifier → subject.py

### 第二批合并（中优先级，预计减少 2-3 个文件）

1. **小文件整合**: boundary_reminder + system_service + review_checklist → 合并到相关服务
2. **分析辅助合并**: sentencing + similar_cases + standard_path_recognizer → 合并到 analysis_service 或保持独立

---

## 4. 通用基础类提取建议

### 4.1 BaseService 设计

```python
class BaseService:
    """服务基类，提供通用能力"""
    
    def __init__(self, db: AsyncSession = None):
        self.db = db
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def health_check(self) -> dict:
        """健康检查"""
        return {"status": "healthy", "service": self.__class__.__name__}
    
    def validate_input(self, data: dict, schema: type) -> bool:
        """输入验证"""
        # Pydantic 验证逻辑
        pass
```

### 4.2 可复用能力

- 数据库会话管理
- 日志记录
- 输入验证
- 错误处理
- 健康检查

---

## 5. 预期收益

| 指标 | 当前 | 目标 | 优化幅度 |
|------|------|------|----------|
| 服务模块数量 | 29 个 | 22-23 个 | -21% ~ -24% |
| 总代码行数 | ~10,500 行 | ~9,800 行 | -700 行 |
| 重复代码 | 约 500 行 | <100 行 | -80% |
| 平均文件大小 | 362 行 | 427 行 | +18% |

---

## 6. 风险评估

### 6.1 低风险

- 报告服务合并：内部重构，API 接口不变
- 提示词服务合并：仅影响内部实现
- 版本服务合并：调用方较少

### 6.2 中风险

- 主体分析合并：涉及核心分析逻辑，需充分测试
- 通用基础类提取：可能影响现有服务继承结构

### 6.3 缓解措施

- 每个合并步骤后执行完整测试
- 保持 API 接口向后兼容
- 使用渐进式重构，避免大规模改动

---

## 7. 验收标准

- [ ] 服务模块数量从 29 个减少至 22-23 个
- [ ] 所有 API 接口保持 100% 兼容
- [ ] 测试覆盖率达到 80% 以上
- [ ] 无循环依赖
- [ ] 代码行数减少 700 行以上

---

**下一步**: 创建通用基础类，执行第一批合并
