# 代码规范指南

本文档定义了帮信罪主观明知智能分析系统的代码规范，所有贡献者都应遵循这些规范。

---

## 目录

1. [通用原则](#通用原则)
2. [Python代码规范](#python代码规范)
3. [前端代码规范](#前端代码规范)
4. [Git提交规范](#git提交规范)
5. [工具使用](#工具使用)

---

## 通用原则

### 1. 代码可读性优先

- 代码是写给人看的，机器只是顺便执行
- 使用有意义的变量名和函数名
- 保持函数简短，单一职责
- 避免过度优化导致代码难以阅读

### 2. 注释规范

- 注释解释"为什么"而不是"做什么"
- 及时更新注释，避免过时注释误导
- 复杂算法需要详细注释说明思路
- 使用中文注释（本项目面向中文用户）

### 3. 文件组织

```
项目/
├── backend/          # 后端代码
│   ├── app/          # 应用代码
│   │   ├── models/   # 数据模型
│   │   ├── routers/  # API路由
│   │   ├── services/ # 业务逻辑
│   │   └── utils/    # 工具函数
│   ├── tests/        # 测试代码
│   └── alembic/      # 数据库迁移
├── frontend/         # 前端代码
│   ├── src/          # 源代码
│   │   ├── views/    # 页面组件
│   │   ├── stores/   # 状态管理
│   │   └── router/   # 路由配置
│   └── tests/        # 测试代码
└── docs/             # 文档
```

---

## Python代码规范

### 1. 代码风格

我们使用 **Ruff** 作为代码格式化和检查工具，配置基于以下规范：

- **PEP 8** - Python代码风格指南
- **Google Python Style Guide** - 文档字符串规范
- **Black** 格式化风格

### 2. 导入排序

```python
# 1. 标准库导入
import os
import sys
from datetime import datetime
from typing import Optional

# 2. 第三方库导入
from fastapi import FastAPI
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import create_engine

# 3. 项目内部导入
from app.config import settings
from app.database import get_db
from app.models.user import User
```

### 3. 类型注解

```python
from typing import Optional, List, Dict, Any

def analyze_case(
    case_text: str,
    mode: str = "auto",
    case_id: Optional[int] = None,
) -> Dict[str, Any]:
    """分析案件文本。

    Args:
        case_text: 案件描述文本。
        mode: 分析模式，可选值为 "auto" 或 "manual"。
        case_id: 可选的案件ID，用于关联数据库记录。

    Returns:
        包含分析结果的字典。

    Raises:
        ValueError: 当case_text为空时抛出。
    """
    if not case_text:
        raise ValueError("案件文本不能为空")
    # ...
```

### 4. 异步代码规范

```python
import asyncio
from typing import AsyncGenerator

async def fetch_data(url: str) -> dict:
    """异步获取数据。"""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

async def process_items(items: List[str]) -> List[dict]:
    """并发处理多个项目。"""
    tasks = [fetch_data(item) for item in items]
    return await asyncio.gather(*tasks)
```

### 5. 错误处理

```python
from loguru import logger

def safe_operation() -> Optional[Result]:
    """安全执行操作，返回None表示失败。"""
    try:
        return perform_operation()
    except SpecificException as e:
        logger.warning(f"操作失败: {e}")
        return None
    except Exception as e:
        logger.error(f"意外错误: {e}")
        raise
```

### 6. 日志规范

```python
from loguru import logger

# 调试信息
logger.debug("处理案件 ID={}", case_id)

# 一般信息
logger.info("分析完成，耗时 {}ms", elapsed_time)

# 警告
logger.warning("模型响应超时，使用默认结果")

# 错误
logger.error("数据库连接失败: {}", error_message)

# 异常（自动包含堆栈）
logger.exception("未处理的异常")
```

---

## 前端代码规范

### 1. Vue组件规范

```vue
<script setup>
// 1. 导入
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useCaseStore } from '@/stores/cases'
import CaseCard from '@/components/CaseCard.vue'

// 2.  Props和Emits定义
const props = defineProps({
  caseId: {
    type: String,
    required: true,
  },
  editable: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update', 'delete'])

// 3. 响应式数据
const caseStore = useCaseStore()
const route = useRoute()
const loading = ref(false)
const caseData = ref(null)

// 4. 计算属性
const canEdit = computed(() => {
  return props.editable && caseData.value?.status === 'draft'
})

// 5. 方法
async function loadCase() {
  loading.value = true
  try {
    caseData.value = await caseStore.fetchCase(props.caseId)
  } catch (error) {
    console.error('加载案件失败:', error)
  } finally {
    loading.value = false
  }
}

function handleUpdate(data) {
  emit('update', data)
}

// 6. 生命周期
onMounted(() => {
  loadCase()
})
</script>

<template>
  <div class="case-detail">
    <CaseCard
      v-if="caseData"
      :data="caseData"
      :editable="canEdit"
      @update="handleUpdate"
    />
    <div v-else-if="loading" class="loading">
      加载中...
    </div>
    <div v-else class="error">
      加载失败
    </div>
  </div>
</template>

<style scoped>
.case-detail {
  padding: 1rem;
}

.loading {
  text-align: center;
  color: var(--text-secondary);
}
</style>
```

### 2. 组合式函数规范

```javascript
// useAnalysis.js
import { ref, computed } from 'vue'
import { analyzeCase as analyzeCaseApi } from '@/api/analysis'

export function useAnalysis() {
  const loading = ref(false)
  const result = ref(null)
  const error = ref(null)

  const hasResult = computed(() => result.value !== null)
  const hasError = computed(() => error.value !== null)

  async function analyzeCase(caseText, options = {}) {
    loading.value = true
    error.value = null

    try {
      result.value = await analyzeCaseApi(caseText, options)
      return result.value
    } catch (err) {
      error.value = err
      throw err
    } finally {
      loading.value = false
    }
  }

  function reset() {
    result.value = null
    error.value = null
    loading.value = false
  }

  return {
    loading,
    result,
    error,
    hasResult,
    hasError,
    analyzeCase,
    reset,
  }
}
```

### 3. 命名规范

| 类型 | 命名方式 | 示例 |
|------|----------|------|
| 组件 | PascalCase | `CaseCard.vue`, `UserProfile.vue` |
| 组合式函数 | camelCase, use前缀 | `useAnalysis`, `useAuth` |
| 工具函数 | camelCase | `formatDate`, `parseCaseText` |
| 常量 | SCREAMING_SNAKE_CASE | `API_BASE_URL`, `MAX_RETRY_COUNT` |
| 变量 | camelCase | `caseData`, `isLoading` |
| 布尔变量 | 前缀is/has/should | `isVisible`, `hasError` |
| 事件处理 | handle前缀 | `handleClick`, `handleSubmit` |
| 异步函数 | 动词开头 | `fetchData`, `loadCases` |

---

## Git提交规范

### 1. 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 2. 提交类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(api): 添加案件批量分析接口` |
| `fix` | 修复bug | `fix(frontend): 修复报告页面加载问题` |
| `docs` | 文档更新 | `docs: 更新API文档` |
| `style` | 代码格式 | `style(backend): 格式化pipeline.py` |
| `refactor` | 重构 | `refactor(db): 优化查询性能` |
| `perf` | 性能优化 | `perf(api): 缓存分析结果` |
| `test` | 测试相关 | `test(backend): 添加单元测试` |
| `build` | 构建相关 | `build: 更新依赖版本` |
| `ci` | CI/CD | `ci: 添加GitHub Actions` |
| `chore` | 其他 | `chore: 清理无用文件` |
| `revert` | 回滚 | `revert: 回滚feat(api)的更改` |

### 3. 提交范围

- `backend` - 后端代码
- `frontend` - 前端代码
- `api` - API接口
- `db` - 数据库
- `config` - 配置
- `docs` - 文档
- `test` - 测试
- `deps` - 依赖

### 4. 提交示例

```bash
# 添加新功能
git commit -m "feat(api): 添加案件批量分析接口

- 支持一次提交多个案件进行分析
- 添加批量分析进度跟踪
- 优化并发处理逻辑

Closes #123"

# 修复bug
git commit -m "fix(frontend): 修复报告页面加载问题

修复了当分析结果包含特殊字符时页面崩溃的问题。

Fixes #456"

# 简单提交
git commit -m "docs: 更新README中的部署说明"
```

---

## 工具使用

### 1. 安装开发依赖

```bash
# 后端
pip install pre-commit ruff mypy bandit

# 前端
cd frontend
npm install -D eslint prettier eslint-plugin-vue eslint-plugin-import
```

### 2. 配置pre-commit

```bash
# 安装pre-commit钩子
pre-commit install

# 手动运行所有检查
pre-commit run --all-files

# 运行特定检查
pre-commit run ruff
pre-commit run eslint
```

### 3. 代码格式化

```bash
# Python格式化
ruff format backend/
ruff check --fix backend/

# 前端格式化
cd frontend
npm run format
npm run lint
```

### 4. 类型检查

```bash
# Python类型检查
mypy backend/app

# 前端类型检查（如果使用TypeScript）
cd frontend
npm run type-check
```

### 5. 测试

```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
npm run test
```

---

## 代码审查清单

提交PR前请检查：

- [ ] 代码符合项目代码规范
- [ ] 所有测试通过
- [ ] 新增代码有适当的测试覆盖
- [ ] 文档已更新
- [ ] 提交信息符合规范
- [ ] 没有引入新的安全漏洞
- [ ] 性能影响已评估

---

## 常见问题

### Q: Ruff报告的全角字符问题需要修复吗？

A: 对于中文项目中的中文文本（如提示词、注释），全角字符是合法的。Ruff配置已忽略RUF001-RUF003规则。但代码中的标点符号应使用半角。

### Q: 如何处理遗留代码？

A: 对于遗留代码：
1. 修改时顺手格式化相关代码
2. 不要专门提交只包含格式化的PR
3. 逐步迁移到新的代码规范

### Q: 紧急修复需要遵循规范吗？

A: 紧急修复可以简化流程，但修复完成后应：
1. 补充测试
2. 补充文档
3. 确保代码符合规范

---

## 参考资源

- [PEP 8 - Python代码风格指南](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Vue.js风格指南](https://vuejs.org/style-guide/)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

*最后更新: 2026-05-26*
