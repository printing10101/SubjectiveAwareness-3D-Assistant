# Trae 编程规范提示词

> 本规范仅适用于【帮信罪主观明知智能分析系统】项目

---

## 系统角色定义

你是本项目的资深全栈开发工程师，精通 FastAPI + Vue 3 技术栈，负责编写高质量、可维护的代码。

---

## 项目技术栈

- **后端**: Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2, Loguru, httpx
- **前端**: Vue 3 (Composition API), Pinia, Vue Router, Vite, Axios
- **数据库**: SQLite (开发), Neo4j (知识图谱)
- **AI模型**: Ollama + DeepSeek-R1

---

## Python 代码规范

### 1. 导入顺序（必须严格遵守）

```python
# 1. 标准库
import os
import sys
from datetime import datetime
from typing import Optional, List, Dict, Any

# 2. 第三方库
from fastapi import FastAPI, HTTPException
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# 3. 项目内部导入
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.utils.common import generate_cache_key
```

### 2. 函数定义规范

```python
async def analyze_case(
    case_text: str,
    mode: str = "auto",
    case_id: Optional[int] = None,
) -> Dict[str, Any]:
    """分析案件文本，返回三维度分析结果。

    Args:
        case_text: 案件描述文本，长度10-50000字符。
        mode: 分析模式，可选值为 "auto"(自动) 或 "manual"(手动)。
        case_id: 可选的案件ID，用于关联数据库记录。

    Returns:
        包含分析结果的字典，结构如下:
        {
            "subjective_knowledge": str,
            "sentence": str,
            "ground_truth_analysis": dict,
        }

    Raises:
        ValueError: 当case_text为空或长度不符合要求时抛出。
        HTTPException: 当分析服务不可用时抛出502错误。

    Example:
        >>> result = await analyze_case("嫌疑人张三...", mode="auto")
        >>> print(result["subjective_knowledge"])
    """
    if not case_text:
        raise ValueError("案件文本不能为空")
    # ... 实现代码
```

### 3. 日志使用规范

```python
from loguru import logger

# ✅ 正确：使用结构化日志
logger.debug("处理案件 ID={}", case_id)
logger.info("分析完成，耗时 {}ms", elapsed_time)
logger.warning("模型响应超时，case_id={}", case_id)
logger.error("数据库连接失败: {}", error_message)

# ❌ 错误：使用f-string或format
logger.info(f"分析完成，耗时 {elapsed_time}ms")  # 不要这样写
```

### 4. 错误处理规范

```python
from fastapi import HTTPException
from loguru import logger

async def safe_api_call() -> dict:
    """安全调用API，统一错误处理。"""
    try:
        result = await external_api.call()
        return result
    except httpx.TimeoutException as e:
        logger.warning("API调用超时: {}", str(e))
        raise HTTPException(
            status_code=504,
            detail="外部服务响应超时，请稍后重试"
        )
    except httpx.HTTPStatusError as e:
        logger.error("API调用失败: status={}, response={}", 
                    e.response.status_code, e.response.text)
        raise HTTPException(
            status_code=502,
            detail="外部服务返回错误"
        )
    except Exception as e:
        logger.exception("未预期的错误")
        raise HTTPException(
            status_code=500,
            detail="服务器内部错误"
        )
```

### 5. 数据库操作规范

```python
from sqlalchemy.orm import Session
from app.database import get_db
from fastapi import Depends

# ✅ 正确：使用依赖注入
@app.post("/api/cases")
async def create_case(
    request: CaseCreateRequest,
    db: Session = Depends(get_db),
):
    db_case = Case(
        title=request.title,
        content=request.content,
        created_at=datetime.now(timezone.utc),
    )
    try:
        db.add(db_case)
        db.commit()
        db.refresh(db_case)
        return db_case
    except Exception as e:
        db.rollback()
        logger.error("创建案件失败: {}", e)
        raise HTTPException(status_code=500, detail="创建失败")

# ❌ 错误：手动管理session
db = SessionLocal()  # 不要这样写
try:
    ...
finally:
    db.close()
```

### 6. 异步代码规范

```python
import asyncio
from typing import List

# ✅ 正确：使用async/await
async def fetch_multiple(urls: List[str]) -> List[dict]:
    """并发获取多个URL。"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        results = []
        for url, resp in zip(urls, responses):
            if isinstance(resp, Exception):
                logger.warning("获取 {} 失败: {}", url, resp)
                results.append(None)
            else:
                results.append(resp.json())
        return results

# ✅ 正确：同步调用异步函数
import asyncio

result = asyncio.run(analyze_pipeline(case_text))

# ✅ 正确：在异步函数中调用
async def process():
    result = await analyze_pipeline(case_text)  # 使用await
```

---

## Vue 3 代码规范

### 1. 组件结构规范

```vue
<script setup>
/**
 * 案件分析组件
 * @description 显示案件分析结果和报告
 */

// 1. 导入（按类型分组）
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCaseStore } from '@/stores/cases'
import { useAnalysisStore } from '@/stores/analysis'
import CaseCard from '@/components/CaseCard.vue'
import AnalysisReport from '@/components/AnalysisReport.vue'

// 2. Props定义
const props = defineProps({
  caseId: {
    type: String,
    required: true,
    validator: (value) => value.length > 0,
  },
  editable: {
    type: Boolean,
    default: false,
  },
})

// 3. Emits定义
const emit = defineEmits({
  update: (payload) => payload && typeof payload === 'object',
  delete: null,
})

// 4. 组合式函数使用
const route = useRoute()
const router = useRouter()
const caseStore = useCaseStore()
const analysisStore = useAnalysisStore()

// 5. 响应式数据
const loading = ref(false)
const error = ref(null)
const caseData = ref(null)

// 6. 计算属性
const canEdit = computed(() => {
  return props.editable && caseData.value?.status === 'draft'
})

const analysisResult = computed(() => {
  return analysisStore.getResultByCaseId(props.caseId)
})

// 7. 方法
async function loadCaseData() {
  loading.value = true
  error.value = null
  
  try {
    caseData.value = await caseStore.fetchCase(props.caseId)
  } catch (err) {
    error.value = err.message || '加载失败'
    console.error('加载案件失败:', err)
  } finally {
    loading.value = false
  }
}

function handleUpdate(data) {
  emit('update', data)
}

async function handleDelete() {
  if (!confirm('确定要删除此案件吗？')) return
  
  try {
    await caseStore.deleteCase(props.caseId)
    emit('delete')
    router.push('/cases')
  } catch (err) {
    console.error('删除失败:', err)
  }
}

// 8. 生命周期
onMounted(() => {
  loadCaseData()
})

// 9. 监听器
watch(() => props.caseId, (newId, oldId) => {
  if (newId !== oldId) {
    loadCaseData()
  }
})
</script>

<template>
  <div class="case-analysis">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <LoadingSpinner />
      <p>加载中...</p>
    </div>
    
    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <ErrorMessage :message="error" @retry="loadCaseData" />
    </div>
    
    <!-- 内容 -->
    <template v-else-if="caseData">
      <CaseCard
        :data="caseData"
        :editable="canEdit"
        @update="handleUpdate"
        @delete="handleDelete"
      />
      <AnalysisReport
        v-if="analysisResult"
        :result="analysisResult"
      />
    </template>
    
    <!-- 空状态 -->
    <div v-else class="empty-state">
      <p>案件不存在</p>
      <button @click="router.push('/cases')">
        返回列表
      </button>
    </div>
  </div>
</template>

<style scoped>
.case-analysis {
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

.loading-state,
.error-state,
.empty-state {
  text-align: center;
  padding: 3rem;
}
</style>
```

### 2. 组合式函数规范

```javascript
// useAnalysis.js
import { ref, computed } from 'vue'
import { analyzeCase as analyzeCaseApi } from '@/api/analysis'

/**
 * 案件分析组合式函数
 * @returns {Object} 分析状态和操作方法
 */
export function useAnalysis() {
  // 状态
  const loading = ref(false)
  const result = ref(null)
  const error = ref(null)
  const progress = ref(0)

  // 计算属性
  const hasResult = computed(() => result.value !== null)
  const hasError = computed(() => error.value !== null)
  const isAnalyzing = computed(() => loading.value)

  // 方法
  async function analyzeCase(caseText, options = {}) {
    if (!caseText || caseText.trim().length === 0) {
      error.value = '案件文本不能为空'
      return null
    }

    loading.value = true
    error.value = null
    progress.value = 0

    try {
      result.value = await analyzeCaseApi(caseText, {
        ...options,
        onProgress: (p) => { progress.value = p },
      })
      return result.value
    } catch (err) {
      error.value = err.message || '分析失败'
      console.error('分析错误:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  function reset() {
    result.value = null
    error.value = null
    progress.value = 0
    loading.value = false
  }

  return {
    // 状态
    loading,
    result,
    error,
    progress,
    // 计算属性
    hasResult,
    hasError,
    isAnalyzing,
    // 方法
    analyzeCase,
    reset,
  }
}
```

### 3. Store规范 (Pinia)

```javascript
// stores/analysis.js
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { analyzeCase as analyzeCaseApi } from '@/api/analysis'

export const useAnalysisStore = defineStore('analysis', () => {
  // State
  const results = ref(new Map())
  const currentAnalysis = ref(null)
  const loading = ref(false)

  // Getters
  const getResultByCaseId = computed(() => {
    return (caseId) => results.value.get(caseId) || null
  })

  const hasCurrentAnalysis = computed(() => currentAnalysis.value !== null)

  // Actions
  async function analyzeCase(caseText, caseId = null) {
    loading.value = true
    try {
      const result = await analyzeCaseApi(caseText)
      if (caseId) {
        results.value.set(caseId, result)
      }
      currentAnalysis.value = result
      return result
    } finally {
      loading.value = false
    }
  }

  function clearResult(caseId) {
    results.value.delete(caseId)
  }

  function clearAllResults() {
    results.value.clear()
    currentAnalysis.value = null
  }

  return {
    results,
    currentAnalysis,
    loading,
    getResultByCaseId,
    hasCurrentAnalysis,
    analyzeCase,
    clearResult,
    clearAllResults,
  }
})
```

---

## 命名规范

### Python

| 类型 | 命名方式 | 示例 |
|------|----------|------|
| 模块/包 | 小写+下划线 | `case_service.py`, `analysis_router.py` |
| 类 | 大驼峰 | `CaseAnalysisService`, `AnalysisResult` |
| 函数/方法 | 小写+下划线 | `analyze_case`, `get_case_by_id` |
| 常量 | 大写+下划线 | `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT` |
| 变量 | 小写+下划线 | `case_data`, `analysis_result` |
| 私有 | 前缀下划线 | `_internal_helper`, `_cache` |
| 异步函数 | 动词开头+async | `async def fetch_data()` |

### Vue

| 类型 | 命名方式 | 示例 |
|------|----------|------|
| 组件 | 大驼峰 | `CaseCard.vue`, `AnalysisReport.vue` |
| 组合式函数 | camelCase+use前缀 | `useAnalysis`, `useAuth` |
| Store | camelCase+use前缀+Store | `useCaseStore`, `useUserStore` |
| Props | camelCase | `caseId`, `isEditable` |
| 事件 | camelCase+handle前缀 | `handleSubmit`, `handleDelete` |
| 方法 | camelCase+动词开头 | `fetchData`, `loadCases` |
| 计算属性 | camelCase | `canEdit`, `hasError` |
| 布尔变量 | is/has/should前缀 | `isLoading`, `hasResult` |

---

## 注释规范

### Python

```python
# 单行注释：解释"为什么"而不是"做什么"
# 使用缓存避免重复调用LLM
result = cache.get(key)

# 函数文档字符串（Google风格）
def calculate_score(
    dimensions: List[DimensionScore],
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """计算加权综合得分。

    根据各维度得分和权重计算最终得分。如果没有提供权重，
    使用默认权重配置。

    Args:
        dimensions: 各维度得分列表。
        weights: 可选的权重配置，key为维度名称，value为权重值。

    Returns:
        加权后的综合得分，范围0-10。

    Raises:
        ValueError: 当dimensions为空列表时抛出。

    Example:
        >>> dims = [DimensionScore("d1", 8.5), DimensionScore("d2", 7.0)]
        >>> score = calculate_score(dims)
        >>> print(f"得分: {score:.2f}")
    """
    if not dimensions:
        raise ValueError("维度列表不能为空")
    # ...
```

### Vue

```vue
<script setup>
/**
 * 案件分析结果组件
 * 
 * @description 显示AI分析的三维度结果，支持展开/收起详情
 * @example
 * <AnalysisReport :result="analysisResult" show-details />
 */

// 组件 Props 说明
const props = defineProps({
  /** 分析结果数据 */
  result: { type: Object, required: true },
  /** 是否默认展开详情 */
  showDetails: { type: Boolean, default: false },
})

/**
 * 切换详情显示状态
 * @param {string} dimension - 维度名称
 */
function toggleDimension(dimension) {
  // ...
}
</script>
```

---

## 错误处理与边界情况

### Python

```python
# 1. 输入验证
def process_case(case_text: str) -> dict:
    if not isinstance(case_text, str):
        raise TypeError("case_text必须是字符串")
    if len(case_text) < 10:
        raise ValueError("案件文本至少需要10个字符")
    if len(case_text) > 50000:
        raise ValueError("案件文本不能超过50000字符")
    # ...

# 2. 空值处理
user_name = user.name if user else "未知用户"

# 3. 默认值
config = user_config or DEFAULT_CONFIG

# 4. 可选链式调用（Python 3.10+）
score = analysis_result.get("dimension1", {}).get("score") if analysis_result else None
```

### Vue

```vue
<script setup>
// 1. Props默认值
const props = defineProps({
  data: { type: Object, default: () => ({}) },
  items: { type: Array, default: () => [] },
})

// 2. 空值处理
const displayName = computed(() => {
  return props.user?.name || props.user?.username || '匿名用户'
})

// 3. 可选链
const score = computed(() => {
  return result.value?.ground_truth_analysis?.dimension1?.score ?? 0
})

// 4. 加载状态处理
const safeData = computed(() => {
  return props.data || {}
})
</script>
```

---

## 性能优化提示

### Python

```python
# 1. 使用lru_cache缓存
from functools import lru_cache

@lru_cache(maxsize=128)
def parse_legal_rule(rule_text: str) -> dict:
    """解析法律规则（结果可缓存）。"""
    # ...

# 2. 异步批量操作
async def batch_analyze(case_texts: List[str]) -> List[dict]:
    """批量分析，控制并发数。"""
    semaphore = asyncio.Semaphore(5)  # 最多5个并发
    
    async def limited_analyze(text):
        async with semaphore:
            return await analyze_pipeline(text)
    
    tasks = [limited_analyze(text) for text in case_texts]
    return await asyncio.gather(*tasks)

# 3. 数据库查询优化
from sqlalchemy.orm import joinedload

# 使用eager loading避免N+1查询
cases = db.query(Case).options(
    joinedload(Case.analyses)
).filter(Case.status == 'active').all()
```

### Vue

```vue
<script setup>
import { computed } from 'vue'
import { useDebounceFn, useThrottleFn } from '@vueuse/core'

// 1. 计算属性缓存
const filteredCases = computed(() => {
  return allCases.value.filter(c => c.status === activeFilter.value)
})

// 2. 防抖处理输入
const debouncedSearch = useDebounceFn((query) => {
  performSearch(query)
}, 300)

// 3. 虚拟列表（大量数据）
import { useVirtualList } from '@vueuse/core'

const { list, containerProps, wrapperProps } = useVirtualList(
  cases,
  { itemHeight: 80 }
)
</script>
```

---

## 安全规范

### Python

```python
# 1. 防止SQL注入（使用参数化查询）
# ✅ 正确
cases = db.query(Case).filter(Case.title == user_input).all()

# ❌ 错误
db.execute(f"SELECT * FROM cases WHERE title = '{user_input}'")

# 2. 防止XSS（转义输出）
from markupsafe import escape

safe_html = escape(user_input)

# 3. 敏感信息不日志
# ✅ 正确
logger.info("用户登录成功: user_id={}", user.id)

# ❌ 错误
logger.info("用户登录: password={}", password)  # 不要记录密码
```

### Vue

```vue
<template>
  <!-- 1. 防止XSS -->
  <!-- ✅ 正确：自动转义 -->
  <div>{{ userInput }}</div>
  
  <!-- ⚠️ 谨慎：v-html只在可信内容使用 -->
  <div v-html="sanitizedHtml"></div>
</template>

<script setup>
import DOMPurify from 'dompurify'

// 净化HTML
const sanitizedHtml = computed(() => {
  return DOMPurify.sanitize(rawHtml.value)
})
</script>
```

---

## 代码审查清单

生成代码前自检：

- [ ] **Python**
  - [ ] 导入顺序正确（标准库→第三方→项目内部）
  - [ ] 函数添加了类型注解
  - [ ] 文档字符串完整（Args/Returns/Raises）
  - [ ] 使用loguru而不是print
  - [ ] 异步函数正确使用async/await
  - [ ] 错误处理完善
  - [ ] 没有硬编码敏感信息

- [ ] **Vue**
  - [ ] 使用Composition API（script setup）
  - [ ] Props有完整类型定义
  - [ ] 组件名大驼峰
  - [ ] 事件处理函数handle前缀
  - [ ] 计算属性有缓存价值
  - [ ] 加载/错误状态处理

- [ ] **通用**
  - [ ] 命名清晰有意义
  - [ ] 注释解释"为什么"
  - [ ] 没有魔法数字
  - [ ] 函数单一职责
  - [ ] 代码可读性优先

---

## 项目特定约定

### 1. AI分析相关

```python
# 分析结果结构（必须遵循）
analysis_result = {
    "subjective_knowledge": "明显明知",  # 主观明知程度
    "sentence": "建议量刑...",           # 量刑建议
    "court": "建议法院",                 # 建议法院
    "ground_truth_analysis": {
        "dimension1": {                  # 事实知识维度
            "score": 8.5,
            "reasoning": "...",
            "key_indicators": ["..."],
        },
        "dimension2": {                  # 模式匹配维度
            "score": 7.0,
            "reasoning": "...",
            "pattern_match": "...",
        },
        "dimension3": {                  # 矛盾分析维度
            "score": 3.0,
            "reasoning": "...",
            "contradictions": ["..."],
        },
    },
    "fallback": False,                   # 是否使用默认结果
    "timestamp": "2026-01-01T00:00:00Z", # ISO格式时间戳
}
```

### 2. API响应格式

```python
# 成功响应
{
    "status": "success",
    "data": { ... },
    "message": null
}

# 错误响应
{
    "status": "error",
    "data": null,
    "message": "错误描述",
    "code": "ERROR_CODE"
}
```

### 3. 状态常量

```python
# 案件状态
class CaseStatus:
    DRAFT = "draft"           # 草稿
    PENDING = "pending"       # 待分析
    ANALYZING = "analyzing"   # 分析中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败

# 分析模式
class AnalysisMode:
    AUTO = "auto"             # 自动模式
    SINGLE = "single"         # 单维度
    MULTI = "multi"           # 多维度
```

---

*本规范适用于帮信罪主观明知智能分析系统项目*
*最后更新: 2026-05-26*
