# 知识库服务重构依赖关系图

## 概述

本文档记录了知识库服务重构的依赖分析结果，作为8个旧模块合并为3个新模块的实施依据。

## 现有模块清单

| 模块文件 | 行数 | 职责 | 目标位置 |
|----------|------|------|----------|
| knowledge_service.py | 1001 | 知识库基础CRUD | repository.py |
| knowledge_search_service.py | 562 | 知识搜索（FTS5） | repository.py |
| knowledge_graph.py | 222 | 早期知识图谱 | analyzer.py |
| knowledge_graph_service.py | 690 | 新版知识图谱 | analyzer.py |
| knowledge_relation_service.py | 660 | 知识关系管理 | analyzer.py |
| knowledge_qa_service.py | 845 | 知识库问答 | analyzer.py |
| knowledge_import_service.py | 1074 | 知识导入 | manager.py |
| knowledge_lifecycle_service.py | 1388 | 生命周期管理 | manager.py |

**总计**: 6442行 → 目标: ≤1500行（净减少约3000行）

## 目标架构

### repository.py（数据访问层，≤500行）

整合来源：
- knowledge_service.py
- knowledge_search_service.py

公开API：
- get_entries_paginated()
- get_entry()
- create_entry()
- update_entry()
- delete_entry()
- get_entries_by_tag()
- add_tag_to_entry()
- remove_tag_from_entry()
- search_entries()
- get_search_suggestions()

### analyzer.py（分析层，≤400行）

整合来源：
- knowledge_graph.py
- knowledge_graph_service.py
- knowledge_relation_service.py
- knowledge_qa_service.py

公开API：
- get_graph_data()
- get_node_neighbors()
- get_shortest_path()
- add_relation()
- delete_relation()
- get_relations()
- answer_question()
- get_related_entries()

### manager.py（管理层，≤600行）

整合来源：
- knowledge_import_service.py
- knowledge_lifecycle_service.py

公开API：
- import_from_document()
- import_from_case()
- update_confidence()
- apply_decay()
- lint_knowledge_base()
- supersede_entry()

## 依赖关系

### Router层依赖

| Router文件 | 依赖的Service模块 | 调用的函数 |
|------------|-------------------|------------|
| knowledge.py | knowledge_service | get_entries_paginated, get_entry, create_entry, update_entry, delete_entry |
| knowledge.py | knowledge_search_service | search_entries |
| knowledge.py | knowledge_graph_service | get_graph_data, get_node_neighbors |
| knowledge.py | knowledge_qa_service | answer_question |
| knowledge.py | knowledge_import_service | import_from_document, import_from_case |
| knowledge.py | knowledge_lifecycle_service | update_confidence, apply_decay |
| knowledge.py | knowledge_relation_service | add_relation, delete_relation, get_relations |

### Service层内部依赖

| 模块 | 依赖的其他Service |
|------|-------------------|
| knowledge_graph_service | knowledge_service（获取条目数据） |
| knowledge_qa_service | knowledge_service, knowledge_graph_service |
| knowledge_import_service | knowledge_service |
| knowledge_lifecycle_service | knowledge_service |
| knowledge_relation_service | knowledge_service |

### 测试文件依赖

| 测试文件 | 测试的Service模块 |
|----------|-------------------|
| test_knowledge_service.py | knowledge_service |
| test_knowledge_search.py | knowledge_search_service |
| test_knowledge_graph.py | knowledge_graph, knowledge_graph_service |
| test_knowledge_qa.py | knowledge_qa_service |
| test_knowledge_import.py | knowledge_import_service |
| test_knowledge_lifecycle.py | knowledge_lifecycle_service |
| test_knowledge_relation.py | knowledge_relation_service |

## 迁移策略

### 阶段1：创建新模块结构

1. 创建 `backend/app/services/knowledge/` 目录
2. 创建 `__init__.py` 提供统一导入入口
3. 实现 `repository.py`
4. 实现 `analyzer.py`
5. 实现 `manager.py`

### 阶段2：更新依赖

1. 更新所有router文件的import语句
2. 更新service层内部依赖
3. 确保测试文件可以正常运行

### 阶段3：兼容性处理

1. 保留旧service文件作为re-export层
2. 添加deprecated标记
3. 提供迁移指引

### 阶段4：测试验证

1. 运行全量pytest测试
2. 验证所有功能正常
3. 执行git commit

## 代码精简策略

### 去除冗余

1. 合并重复的数据库查询逻辑
2. 统一错误处理方式
3. 移除未使用的私有函数
4. 简化过度复杂的类型转换

### 优化结构

1. 使用更简洁的异步/await语法
2. 提取公共辅助函数
3. 减少嵌套层级
4. 使用更高效的SQLAlchemy查询

### 文档精简

1. 移除过时的注释
2. 保留关键API文档
3. 使用更简洁的docstring格式

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| API不兼容 | 高 | 保持函数签名完全一致 |
| 功能缺失 | 高 | 逐个函数验证迁移 |
| 测试失败 | 中 | 每步迁移后运行测试 |
| 性能下降 | 低 | 保持核心查询逻辑不变 |

## 验收标准

1. 所有pytest测试通过
2. 代码行数符合限制要求
3. 外部API完全兼容
4. 无功能回归
5. git commit符合规范
