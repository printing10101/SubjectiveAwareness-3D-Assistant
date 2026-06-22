# Deprecated 服务重构映射报告

**生成时间**: 2026-06-18  
**版本**: V1.2.0  
**目的**: 记录 V1.0 旧版分析服务与 V1.1 新版分析服务的代码引用关系，指导代码收敛工作

---

## 1. 服务映射关系总览

| 旧版服务 (V1.0) | 新版服务 (V1.1) | 处理方式 |
|----------------|----------------|---------|
| `path_identifier.py` | `standard_path_recognizer.py` | 迁移核心逻辑 + deprecation 标记 |
| `boundary_checker.py` | `boundary_reminder.py` | 迁移核心逻辑 + deprecation 标记 |
| `subject_stratifier.py` | `multi_subject_analyzer.py` | 迁移核心逻辑 + deprecation 标记 |
| `evidence_layer.py` | `evidence_strength_layer.py` | 重构为枚举类型 + deprecation 标记 |
| `version_manager.py` | `versioned_data_loader.py` | 委托调用 + deprecation 标记 |

---

## 2. 服务文件路径

### 2.1 旧版服务 (V1.0)
- `backend/app/services/path_identifier.py`
- `backend/app/services/boundary_checker.py`
- `backend/app/services/subject_stratifier.py`
- `backend/app/services/evidence_layer.py`
- `backend/app/services/version_manager.py`

### 2.2 新版服务 (V1.1)
- `backend/app/services/standard_path_recognizer.py`
- `backend/app/services/boundary_reminder.py`
- `backend/app/services/multi_subject_analyzer.py`
- `backend/app/services/evidence_strength_layer.py`
- `backend/app/services/versioned_data_loader.py`

---

## 3. 代码引用分析

### 3.1 path_identifier.py 引用位置

#### 核心引用
- **文件**: `backend/app/services/pipeline.py`
  - **行号**: 约第 15 行
  - **引用方式**: `from app.services.path_identifier import identify_legal_path`
  - **上下文**: 在分析流程中调用 `identify_legal_path(case_text)` 识别规范路径

#### 测试引用
- **文件**: `backend/tests/test_path_identifier.py`
  - **引用方式**: 完整测试套件
  - **上下文**: 测试路径识别功能的各个场景

#### 其他引用
- **文件**: `backend/app/main.py`
  - **引用方式**: 间接引用（通过 pipeline 调用）
- **文件**: `docs/CHANGELOG.md`
  - **引用方式**: 文档说明

---

### 3.2 standard_path_recognizer.py 引用位置

#### 核心引用
- **文件**: `backend/app/services/pipeline.py`
  - **行号**: 约第 18 行
  - **引用方式**: `from app.services.standard_path_recognizer import recognize_standard_path`
  - **上下文**: 新版路径识别接口

#### 测试引用
- **文件**: `backend/tests/test_standard_path_recognizer.py`
  - **引用方式**: 完整测试套件
  - **上下文**: 测试新版路径识别功能

---

### 3.3 boundary_checker.py 引用位置

#### 核心引用
- **文件**: `backend/app/services/pipeline.py`
  - **行号**: 约第 22 行
  - **引用方式**: `from app.services.boundary_checker import check_boundary`
  - **上下文**: 在分析流程中调用 `check_boundary(case)` 检查边界

#### 测试引用
- **文件**: `backend/tests/test_boundary_checker.py`
  - **引用方式**: 完整测试套件
  - **上下文**: 测试边界检查功能

#### 其他引用
- **文件**: `backend/scripts/batch_fix_all.py`
  - **引用方式**: 批处理脚本中调用
- **文件**: `backend/scripts/smart_fix.py`
  - **引用方式**: 智能修复脚本中引用

---

### 3.4 boundary_reminder.py 引用位置

#### 核心引用
- **文件**: `backend/app/services/pipeline.py`
  - **行号**: 约第 25 行
  - **引用方式**: `from app.services.boundary_reminder import check_boundary_alerts`
  - **上下文**: 新版边界提醒接口

#### 测试引用
- **文件**: `backend/tests/test_boundary_reminder.py`
  - **引用方式**: 完整测试套件
  - **上下文**: 测试新版边界提醒功能

---

### 3.5 subject_stratifier.py 引用位置

#### 核心引用
- **文件**: `backend/app/services/pipeline.py`
  - **行号**: 约第 30 行
  - **引用方式**: `from app.services.subject_stratifier import stratify_subjects`
  - **上下文**: 在分析流程中调用 `stratify_subjects(case_text)` 进行多主体分层

#### 测试引用
- **文件**: `backend/tests/test_subject_stratifier.py`
  - **引用方式**: 完整测试套件
  - **上下文**: 测试主体分层功能

#### 其他引用
- **文件**: `docs/V1.1.0_changelog.md`
  - **引用方式**: 变更日志说明

---

### 3.6 multi_subject_analyzer.py 引用位置

#### 核心引用
- **文件**: `backend/app/services/pipeline.py`
  - **行号**: 约第 33 行
  - **引用方式**: `from app.services.multi_subject_analyzer import analyze_subjects`
  - **上下文**: 新版多主体分析接口

#### 测试引用
- **文件**: `backend/tests/test_multi_subject_analyzer.py`
  - **引用方式**: 完整测试套件
  - **上下文**: 测试新版多主体分析功能

---

### 3.7 evidence_layer.py 引用位置

#### 核心引用
- **文件**: `backend/app/services/pipeline.py`
  - **行号**: 约第 38 行
  - **引用方式**: `from app.services.evidence_layer import build_evidence_layers, guard_against_single_layer_override`
  - **上下文**: 在分析流程中调用证据分层和防护函数

#### 测试引用
- **文件**: `backend/tests/test_evidence_layer.py`
  - **引用方式**: 完整测试套件
  - **上下文**: 测试证据分层功能

#### 类型定义引用
- **文件**: `backend/app/types/evidence.py`
  - **引用方式**: `from app.services.evidence_layer import EvidenceLayer`
  - **上下文**: 导入 EvidenceLayer 类型定义

---

### 3.8 evidence_strength_layer.py 引用位置

#### 核心引用
- **文件**: `backend/app/services/pipeline.py`
  - **行号**: 约第 41 行
  - **引用方式**: `from app.services.evidence_strength_layer import EvidenceStrengthLayer`
  - **上下文**: 新版证据强度评估接口

#### 测试引用
- **文件**: `backend/tests/test_evidence_strength_layer.py`
  - **引用方式**: 完整测试套件
  - **上下文**: 测试新版证据强度评估功能

---

### 3.9 version.py 引用位置（合并自 version_manager.py 和 versioned_data_loader.py）

#### 核心引用
- **文件**: `backend/app/services/pipeline.py`
  - **行号**: 约第 45 行
  - **引用方式**: `from app.services.version import VersionManager`
  - **上下文**: 版本管理器实例化

- **文件**: `backend/app/routers/cases.py`
  - **行号**: 约第 20 行
  - **引用方式**: `from app.services.version import VersionManager`
  - **上下文**: 案件版本控制 API

- **文件**: `backend/app/routers/versions.py`
  - **行号**: 约第 15 行
  - **引用方式**: `from app.services.version import VersionManager, EntityType`
  - **上下文**: 版本管理 API 路由

- **文件**: `backend/app/services/pipeline.py`
  - **行号**: 约第 48 行
  - **引用方式**: `from app.services.version import VersionedDataLoader`
  - **上下文**: 新版版本化数据加载接口

#### 测试引用
- **文件**: `backend/tests/test_version.py`（合并自 test_version_manager.py 和 test_versioned_data_loader.py）
  - **引用方式**: 完整测试套件
  - **上下文**: 测试版本管理和数据加载功能

#### 其他引用
- **文件**: `backend/scripts/migrate_versions.py`
  - **引用方式**: 版本迁移脚本

---

## 4. 关键依赖关系

### 4.1 pipeline.py 依赖链
```python
# V1.0 旧版服务
from app.services.path_identifier import identify_legal_path
from app.services.boundary_checker import check_boundary
from app.services.subject_stratifier import stratify_subjects
from app.services.evidence_layer import build_evidence_layers, guard_against_single_layer_override
from app.services.version import VersionManager

# V1.1 新版服务
from app.services.standard_path_recognizer import recognize_standard_path
from app.services.boundary_reminder import check_boundary_alerts
from app.services.multi_subject_analyzer import analyze_subjects
from app.services.evidence_strength_layer import EvidenceStrengthLayer
from app.services.version import VersionedDataLoader
```

### 4.2 类型定义依赖
- `backend/app/types/evidence.py` 依赖 `evidence_layer.EvidenceLayer`
- `backend/app/types/subject.py` 依赖 `subject_stratifier.SubjectInfo`
- `backend/app/types/path.py` 依赖 `path_identifier.LegalPath`

### 4.3 API 路由依赖
- `backend/app/routers/cases.py` 依赖 `version_manager.VersionManager`
- `backend/app/routers/versions.py` 依赖 `version_manager.VersionManager, EntityType`
- `backend/app/routers/reports.py` 间接依赖多个服务

---

## 5. 迁移影响评估

### 5.1 高影响文件（需重点验证）
1. **backend/app/services/pipeline.py**
   - 影响：核心分析管道，同时引用新旧版服务
   - 风险：高
   - 验证：需确保所有调用路径正常工作

2. **backend/app/types/evidence.py**
   - 影响：类型定义依赖旧版服务
   - 风险：中
   - 验证：需更新类型导入路径

3. **backend/app/routers/versions.py**
   - 影响：版本管理 API
   - 风险：中
   - 验证：需确保 API 接口兼容性

### 5.2 中影响文件
1. **backend/scripts/batch_fix_all.py**
   - 影响：批处理脚本
   - 风险：低
   - 验证：功能测试

2. **backend/scripts/smart_fix.py**
   - 影响：智能修复脚本
   - 风险：低
   - 验证：功能测试

### 5.3 低影响文件
1. **测试文件**
   - 影响：仅测试代码
   - 风险：低
   - 验证：pytest 全量测试

2. **文档文件**
   - 影响：仅文档说明
   - 风险：无
   - 验证：无需验证

---

## 6. 迁移策略

### 6.1 第一阶段：添加 deprecation 标记
- 为所有旧版服务文件添加 `@deprecated` 装饰器
- 添加标准化警告信息，指向迁移指南

### 6.2 第二阶段：迁移核心逻辑
1. **path_identifier.py → standard_path_recognizer.py**
   - 迁移 `identify_legal_path` 核心逻辑为 `_internal_identify_legal_path`
   - 旧版函数改为 re-export

2. **boundary_checker.py → boundary_reminder.py**
   - 迁移 `check_boundary` 核心逻辑为 `_internal_check_boundary`
   - 旧版函数改为 re-export

3. **subject_stratifier.py → multi_subject_analyzer.py**
   - 迁移 `stratify_subjects` 核心逻辑为 `_internal_stratify_subjects`
   - 旧版函数改为 re-export

4. **evidence_layer.py → evidence_strength_layer.py**
   - 将 `EvidenceLayer` 重构为 `_LayerEnum` 枚举
   - 旧版类型定义改为 alias

5. **version_manager.py → versioned_data_loader.py**
   - 修改 `VersionManager.create_version` 委托调用新版实现
   - 旧版类保留接口兼容性

### 6.3 第三阶段：更新引用
- 更新 `pipeline.py` 中的导入路径（可选，保持向后兼容）
- 更新类型定义文件的导入路径
- 保持 API 路由的接口兼容性

### 6.4 第四阶段：验证
- 执行 pytest 全量测试
- 验证 API 路由功能
- 检查类型定义一致性

---

## 7. 向后兼容性保证

### 7.1 兼容性期限
- 旧版服务保持可用至 **V1.3.0** 版本
- 所有公开 API 接口保持不变
- 所有类型定义保持兼容

### 7.2 迁移指引
- 迁移指南文档：`docs/cleanup/deprecated_migration.md`
- 每个 deprecation warning 包含明确的迁移路径
- 提供代码示例和最佳实践

---

## 8. 检查清单

- [ ] 创建 deprecated_refactor_map.md 文档
- [ ] 为 5 个旧版服务添加 deprecation 标记
- [ ] 迁移 path_identifier.py 核心逻辑
- [ ] 迁移 boundary_checker.py 核心逻辑
- [ ] 迁移 subject_stratifier.py 核心逻辑
- [ ] 重构 evidence_layer.py 为枚举类型
- [ ] 修改 version_manager.py 委托调用
- [ ] 更新 pipeline.py 引用（如需要）
- [ ] 更新类型定义文件导入
- [ ] 执行 pytest 全量测试
- [ ] 验证 API 路由功能
- [ ] 创建 deprecated_migration.md 迁移指南
- [ ] 代码审查和合并

---

## 9. 附录

### 9.1 相关文档
- [V1.1.0 变更日志](../V1.1.0_changelog.md)
- [API 参考文档](../api_reference.md)
- [综合技术文档](../综合技术文档.md)

### 9.2 联系人
- 技术负责人：[待填写]
- 代码审查人：[待填写]
- 测试负责人：[待填写]

---

**文档版本**: 1.0  
**最后更新**: 2026-06-18  
**状态**: 进行中
