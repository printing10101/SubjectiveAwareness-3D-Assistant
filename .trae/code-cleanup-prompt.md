# 代码库大清洗提示词

> 适用于【帮信罪主观明知智能分析系统】项目代码库全面清洗

---

## 系统角色

你是代码重构专家，负责对整个代码库进行全面清洗和规范化。你需要：
1. 识别并修复所有代码质量问题
2. 统一代码风格和规范
3. 优化性能和可维护性
4. 确保不破坏现有功能

---

## 清洗流程（必须按顺序执行）

### 阶段1: 备份与检查

```
1. 确认当前Git工作区干净（无未提交更改）
2. 创建清洗分支: git checkout -b cleanup/2026-05-26
3. 运行现有测试，记录基线状态
4. 扫描代码库，生成问题清单
```

### 阶段2: Python后端清洗

#### 2.1 导入排序修复

**问题**: 导入顺序混乱，存在未使用导入

**修复规则**:
```python
# ✅ 正确顺序
# 1. 标准库
import os
import sys
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

# 2. 第三方库
from fastapi import FastAPI, HTTPException, Depends
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import Session, declarative_base
import httpx

# 3. 项目内部导入
from app.config import settings
from app.database import get_db, engine
from app.models.case import Case
from app.models.analysis import Analysis
from app.utils.common import generate_cache_key, sanitize_json_string
```

**操作命令**:
```bash
cd backend
ruff check --select I --fix .
ruff check --select F401 --fix .  # 删除未使用导入
```

#### 2.2 类型注解补全

**问题**: 函数缺少类型注解

**修复规则**:
```python
# ❌ 修复前
def analyze_case(case_text, mode="auto"):
    result = process(case_text)
    return result

# ✅ 修复后
async def analyze_case(
    case_text: str,
    mode: str = "auto",
    case_id: Optional[int] = None,
) -> Dict[str, Any]:
    """分析案件文本。
    
    Args:
        case_text: 案件描述文本。
        mode: 分析模式。
        case_id: 可选的案件ID。
        
    Returns:
        分析结果字典。
    """
    result: Dict[str, Any] = await process(case_text)
    return result
```

#### 2.3 异步代码修复

**问题**: 同步调用异步函数

**关键修复点**:
```python
# ❌ 错误: 同步调用异步函数
# backend/app/services/analysis_service.py 第19行
result = analyze_pipeline(case.case_text, mode=mode)

# ✅ 修复: 添加await
result = await analyze_pipeline(case.case_text, mode=mode)

# 同时需要修改函数签名
# ❌ 修复前
def run_analysis(db: Session, case_id: int, mode: str = "auto") -> Analysis:

# ✅ 修复后
async def run_analysis(db: Session, case_id: int, mode: str = "auto") -> Analysis:
```

#### 2.4 日志规范化

**问题**: 使用print或f-string日志

**修复规则**:
```python
# ❌ 修复前
print(f"分析完成，耗时 {elapsed}ms")
logger.info(f"处理案件 {case_id}")

# ✅ 修复后
logger.info("分析完成，耗时 {}ms", elapsed)
logger.info("处理案件 ID={}", case_id)
```

#### 2.5 错误处理完善

**问题**: 缺少异常处理或处理不完善

**修复规则**:
```python
# ❌ 修复前
def parse_json_response(response: str) -> dict:
    return json.loads(response)

# ✅ 修复后
from loguru import logger

def parse_json_response(response: str) -> Dict[str, Any]:
    """解析JSON响应，处理异常情况。
    
    Args:
        response: JSON字符串。
        
    Returns:
        解析后的字典。
        
    Raises:
        ValueError: 当JSON解析失败时抛出。
    """
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        logger.error("JSON解析失败: {}, 响应内容: {}", e, response[:200])
        raise ValueError(f"无效的JSON响应: {e}") from e
```

#### 2.6 数据库操作规范

**问题**: 手动管理session，缺少事务回滚

**修复规则**:
```python
# ❌ 修复前
def create_case(db: Session, data: dict):
    case = Case(**data)
    db.add(case)
    db.commit()
    return case

# ✅ 修复后
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

def create_case(db: Session, data: CaseCreate) -> Case:
    """创建案件记录。
    
    Args:
        db: 数据库会话。
        data: 案件创建数据。
        
    Returns:
        创建的案件对象。
        
    Raises:
        HTTPException: 当数据库操作失败时抛出。
    """
    case = Case(
        title=data.title,
        content=data.content,
        created_at=datetime.now(timezone.utc),
    )
    try:
        db.add(case)
        db.commit()
        db.refresh(case)
        logger.info("案件创建成功: id={}", case.id)
        return case
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("案件创建失败: {}", e)
        raise HTTPException(status_code=500, detail="创建案件失败")
```

#### 2.7 常量提取

**问题**: 魔法数字和字符串硬编码

**修复规则**:
```python
# ✅ 在config.py或constants.py中定义
class AnalysisConfig:
    """分析配置常量。"""
    MIN_CASE_LENGTH = 10
    MAX_CASE_LENGTH = 50000
    DEFAULT_TIMEOUT = 60.0
    MAX_RETRY_COUNT = 3
    CACHE_TTL = 3600

class CaseStatus:
    """案件状态常量。"""
    DRAFT = "draft"
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"

# 使用
if len(case_text) < AnalysisConfig.MIN_CASE_LENGTH:
    raise ValueError(f"案件文本至少需要{AnalysisConfig.MIN_CASE_LENGTH}个字符")
```

### 阶段3: 前端清洗

#### 3.1 Vue组件结构规范化

**问题**: 组件结构混乱，缺少规范

**修复规则**:
```vue
<script setup>
/**
 * 组件名称
 * @description 组件描述
 */

// 1. 导入
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStore } from '@/stores/store'
import ComponentA from '@/components/ComponentA.vue'

// 2. Props
const props = defineProps({
  propName: {
    type: String,
    required: true,
  },
})

// 3. Emits
const emit = defineEmits(['eventName'])

// 4. 组合式函数
const route = useRoute()
const store = useStore()

// 5. 响应式数据
const data = ref(null)
const loading = ref(false)

// 6. 计算属性
const computedValue = computed(() => {
  return data.value?.property || defaultValue
})

// 7. 方法
async function fetchData() {
  loading.value = true
  try {
    data.value = await store.fetch()
  } catch (error) {
    console.error('获取数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 8. 生命周期
onMounted(() => {
  fetchData()
})

// 9. 监听器
watch(() => props.propName, fetchData)
</script>
```

#### 3.2 命名规范化

**问题**: 命名不统一

**修复清单**:
```
组件名: casecard.vue → CaseCard.vue
组合式函数: useanalysis.js → useAnalysis.js
方法: getdata() → fetchData()
事件: clickhandler() → handleClick()
布尔值: loading → isLoading
```

#### 3.3 错误状态处理

**问题**: 缺少加载和错误状态处理

**修复规则**:
```vue
<template>
  <div class="component">
    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading">
      <LoadingSpinner />
      <span>加载中...</span>
    </div>
    
    <!-- 错误状态 -->
    <div v-else-if="hasError" class="error">
      <ErrorMessage :message="errorMessage" @retry="fetchData" />
    </div>
    
    <!-- 内容 -->
    <div v-else class="content">
      <!-- 实际内容 -->
    </div>
  </div>
</template>
```

### 阶段4: 配置文件清洗

#### 4.1 环境变量整理

**问题**: .env文件混乱

**修复规则**:
```env
# =============================================================================
# 环境配置
# =============================================================================

# --- 基础配置 ---
APP_ENV=development
DEBUG=true

# --- 服务器配置 ---
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# --- 数据库配置 ---
DATABASE_URL=sqlite:///./app.db

# --- Ollama配置 ---
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:7b

# --- JWT配置 ---
JWT_SECRET_KEY=your-secret-key-here
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# --- CORS配置 ---
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

#### 4.2 依赖版本锁定

**问题**: requirements.txt使用>=版本

**修复规则**:
```txt
# requirements.txt
# 生产环境使用精确版本

fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
sqlalchemy==2.0.23
alembic==1.12.1
httpx==0.25.2
loguru==0.7.2
python-dotenv==1.0.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

### 阶段5: 测试和验证

#### 5.1 运行测试

```bash
# 后端测试
cd backend
pytest -v --tb=short

# 前端测试
cd frontend
npm run test
```

#### 5.2 代码检查

```bash
# Python
cd backend
ruff check .
ruff format --check .
mypy app

# 前端
cd frontend
npm run lint
npm run format --check
```

#### 5.3 功能验证

```bash
# 启动服务验证
cd backend
python run.py

# 另一个终端
cd frontend
npm run dev

# 访问 http://localhost:5173 测试核心功能
```

---

## 清洗检查清单

### Python后端

- [ ] 所有导入按顺序排列（标准库→第三方→项目内部）
- [ ] 删除所有未使用的导入
- [ ] 所有函数有类型注解
- [ ] 所有公共函数有文档字符串（Args/Returns/Raises）
- [ ] 所有print替换为loguru
- [ ] 异步函数正确调用（await）
- [ ] 数据库操作有try-except-finally
- [ ] 所有异常被适当处理
- [ ] 魔法数字提取为常量
- [ ] 硬编码字符串提取为配置

### Vue前端

- [ ] 所有组件使用<script setup>
- [ ] 组件结构符合9部分规范
- [ ] 组件名大驼峰
- [ ] 组合式函数use前缀
- [ ] 方法名动词开头
- [ ] 布尔变量is/has前缀
- [ ] 事件处理handle前缀
- [ ] 所有Props有类型定义
- [ ] 加载/错误状态处理
- [ ] 可选链式调用（?.）

### 配置文件

- [ ] .env文件分类整理
- [ ] 敏感信息不提交到Git
- [ ] requirements.txt使用精确版本
- [ ] package.json依赖整理
- [ ] 删除无用依赖

### 通用

- [ ] 所有测试通过
- [ ] 代码检查无错误
- [ ] 核心功能正常
- [ ] 文档已更新

---

## 常见问题处理

### Q1: 修复导致测试失败怎么办？

**处理步骤**:
1. 记录失败的测试
2. 分析失败原因
3. 如果是修复引入的问题，调整修复方式
4. 如果是测试本身问题，更新测试
5. 确保所有测试通过后再提交

### Q2: 如何处理循环导入？

**解决方案**:
```python
# 在函数内部导入，而不是模块顶部
def get_user_service():
    from app.services.user import UserService
    return UserService()

# 或使用TYPE_CHECKING
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.user import UserService
```

### Q3: 类型注解与SQLAlchemy冲突？

**解决方案**:
```python
from sqlalchemy.orm import Mapped, mapped_column

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
```

### Q4: 清洗范围太大怎么办？

**建议分批处理**:
1. 第一批: 导入排序和删除未使用导入
2. 第二批: 添加类型注解
3. 第三批: 完善文档字符串
4. 第四批: 修复异步调用问题
5. 第五批: 前端组件规范化

每批完成后运行测试，确保不破坏功能。

---

## 提交规范

清洗完成后，按以下格式提交：

```bash
# 提交信息
git commit -m "style(backend): 规范化Python代码风格

- 修复导入顺序，删除未使用导入
- 添加函数类型注解
- 完善文档字符串
- 规范化日志使用
- 修复异步调用问题

所有测试通过，功能正常。"
```

---

*本清洗指南适用于帮信罪主观明知智能分析系统项目*
*最后更新: 2026-05-26*
