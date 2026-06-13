# Trae Solo 提示词 - 前端API层封装

## 任务目标
创建统一的前端API封装层，集中管理所有后端接口调用。

## 执行步骤

### 步骤1: 创建API目录结构
```bash
cd frontend/src
mkdir -p api
mkdir -p api/modules
```

### 步骤2: 创建API基础配置
创建 `frontend/src/api/config.js`：

```javascript
/**
 * API基础配置
 */

// API基础URL
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// 请求超时时间(毫秒)
const TIMEOUT = 120000

// 请求配置
export const apiConfig = {
  baseURL: BASE_URL,
  timeout: TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
}

// 响应状态码处理
export const responseHandlers = {
  200: (data) => data,
  201: (data) => data,
  400: (error) => { throw new Error(error.detail || '请求参数错误') },
  401: (error) => { throw new Error('未授权，请重新登录') },
  403: (error) => { throw new Error('没有权限执行此操作') },
  404: (error) => { throw new Error(error.detail || '请求的资源不存在') },
  500: (error) => { throw new Error('服务器内部错误') },
  502: (error) => { throw new Error('分析服务暂时不可用') },
  504: (error) => { throw new Error('请求超时，请稍后重试') },
}
```

### 步骤3: 创建axios实例
创建 `frontend/src/api/instance.js`：

```javascript
/**
 * Axios实例配置
 */

import axios from 'axios'

import { apiConfig, responseHandlers } from './config'

// 创建axios实例
const apiInstance = axios.create(apiConfig)

// 请求拦截器
apiInstance.interceptors.request.use(
  (config) => {
    // 添加认证token
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiInstance.interceptors.response.use(
  (response) => {
    const { status, data } = response
    const handler = responseHandlers[status]
    if (handler) {
      return handler(data)
    }
    return data
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      const handler = responseHandlers[status]
      if (handler) {
        return handler(data)
      }
    }
    return Promise.reject(error)
  }
)

export default apiInstance
```

### 步骤4: 创建分析API模块
创建 `frontend/src/api/modules/analysis.js`：

```javascript
/**
 * 分析相关API
 */

import api from '../instance'

/**
 * 执行案件分析
 * @param {Object} params - 分析参数
 * @param {string} params.case_text - 案件文本
 * @param {string} [params.mode='auto'] - 分析模式
 * @param {number} [params.case_id] - 案件ID
 * @returns {Promise<Object>} 分析结果
 */
export const analyzeCase = (params) => {
  return api.post('/api/analyze', params)
}

/**
 * 获取分析历史
 * @param {number} caseId - 案件ID
 * @returns {Promise<Array>} 分析历史列表
 */
export const getAnalysisHistory = (caseId) => {
  return api.get(`/api/cases/${caseId}/analyses`)
}

/**
 * 获取单个分析结果
 * @param {number} analysisId - 分析ID
 * @returns {Promise<Object>} 分析结果详情
 */
export const getAnalysisById = (analysisId) => {
  return api.get(`/api/analyses/${analysisId}`)
}

export default {
  analyzeCase,
  getAnalysisHistory,
  getAnalysisById,
}
```

### 步骤5: 创建案件API模块
创建 `frontend/src/api/modules/cases.js`：

```javascript
/**
 * 案件相关API
 */

import api from '../instance'

/**
 * 获取案件列表
 * @param {Object} params - 查询参数
 * @param {number} [params.skip=0] - 分页偏移
 * @param {number} [params.limit=100] - 每页数量
 * @param {string} [params.status] - 状态筛选
 * @returns {Promise<Array>} 案件列表
 */
export const getCases = (params = {}) => {
  return api.get('/api/cases', { params })
}

/**
 * 获取单个案件
 * @param {number} caseId - 案件ID
 * @returns {Promise<Object>} 案件详情
 */
export const getCaseById = (caseId) => {
  return api.get(`/api/cases/${caseId}`)
}

/**
 * 创建案件
 * @param {Object} data - 案件数据
 * @returns {Promise<Object>} 创建的案件
 */
export const createCase = (data) => {
  return api.post('/api/cases', data)
}

/**
 * 更新案件
 * @param {number} caseId - 案件ID
 * @param {Object} data - 更新数据
 * @returns {Promise<Object>} 更新后的案件
 */
export const updateCase = (caseId, data) => {
  return api.put(`/api/cases/${caseId}`, data)
}

/**
 * 删除案件
 * @param {number} caseId - 案件ID
 * @returns {Promise<boolean>} 是否成功
 */
export const deleteCase = (caseId) => {
  return api.delete(`/api/cases/${caseId}`)
}

export default {
  getCases,
  getCaseById,
  createCase,
  updateCase,
  deleteCase,
}
```

### 步骤6: 创建API统一入口
创建 `frontend/src/api/index.js`：

```javascript
/**
 * API统一入口
 */

import analysisApi from './modules/analysis'
import casesApi from './modules/cases'

export const analysis = analysisApi
export const cases = casesApi

// 统一导出
export default {
  analysis: analysisApi,
  cases: casesApi,
}
```

### 步骤7: 更新store使用新API
修改 `frontend/src/stores/analysisStore.js`：

```javascript
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

import { analysis } from '@/api'  // 使用新的API层

// ... 其他代码

// 修改分析函数
async function performAnalysis(caseText, mode = 'auto') {
  isLoading.value = true
  error.value = null
  
  const startTime = Date.now()
  
  try {
    const result = await analysis.analyzeCase({
      case_text: caseText,
      mode: mode,
    })
    
    const elapsed = Date.now() - startTime
    setResponseTime(elapsed)
    setAnalysisResult(result)
    
    return result
  } catch (err) {
    setError(err.message || '分析失败')
    throw err
  } finally {
    setLoading(false)
  }
}
```

### 步骤8: 验证API层
```bash
cd frontend

# 1. 检查语法
npm run lint

# 2. 检查类型（如果有TypeScript）
npm run type-check 2>/dev/null || echo "无类型检查"

# 3. 构建测试
npm run build

# 4. 启动开发服务器测试
npm run dev
```

### 步骤9: 提交代码
```bash
git add -A
git commit -m "feat(frontend): 创建API层封装

- 创建统一的API配置管理
- 封装axios实例和拦截器
- 创建analysis和cases API模块
- 更新store使用新API层
- 所有构建检查通过"
```

## 完成标准
- [ ] `src/api/` 目录结构完整
- [ ] `config.js` 包含基础配置
- [ ] `instance.js` 配置拦截器
- [ ] `modules/` 包含analysis和cases模块
- [ ] `index.js` 统一导出所有API
- [ ] Store更新使用新API
- [ ] `npm run lint` 无错误
- [ ] `npm run build` 成功
- [ ] 代码已提交

## 验证命令
```bash
cd frontend

# 检查文件结构
ls -la src/api/
ls -la src/api/modules/

# 检查lint
npm run lint

# 检查构建
npm run build
```
