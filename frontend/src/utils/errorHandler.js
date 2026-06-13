const DEV = import.meta.env.DEV

export const ErrorType = {
  SYNTAX: 'syntax',
  RUNTIME: 'runtime',
  RESOURCE: 'resource',
  NETWORK: 'network',
  API: 'api',
  UNKNOWN: 'unknown',
}

export const LogLevel = {
  INFO: 'info',
  WARN: 'warn',
  ERROR: 'error',
}

const userMessages = {
  [ErrorType.SYNTAX]: '应用遇到语法错误，请刷新页面重试',
  [ErrorType.RUNTIME]: '应用运行时出现异常，请刷新页面重试',
  [ErrorType.RESOURCE]: '页面资源加载失败，请检查网络后刷新',
  [ErrorType.NETWORK]: '网络连接异常，请检查网络后重试',
  [ErrorType.API]: '服务器响应异常，请稍后重试',
  [ErrorType.UNKNOWN]: '发生未知错误，请刷新页面重试',
}

const httpStatusMessages = {
  400: '请求参数有误，请检查输入后重试',
  401: '登录已过期，请重新登录',
  403: '您没有权限执行此操作',
  404: '请求的资源不存在',
  413: '上传文件过大，请压缩后重试',
  429: '请求过于频繁，请稍后重试',
  500: '服务器内部错误，请稍后重试',
  502: '服务暂时不可用，请稍后重试',
  503: '服务正在维护，请稍后重试',
  504: '服务响应超时，请稍后重试',
}

export function classifyError(error) {
  if (error instanceof SyntaxError || error?.name === 'SyntaxError') {
    return ErrorType.SYNTAX
  }
  if (
    error instanceof TypeError ||
    error instanceof ReferenceError ||
    error instanceof RangeError
  ) {
    return ErrorType.RUNTIME
  }
  if (
    error?.code === 'ERR_NETWORK' ||
    error?.message?.includes('Network') ||
    error?.message?.includes('network') ||
    error?.code === 'ECONNABORTED'
  ) {
    return ErrorType.NETWORK
  }
  if (error?.config?.url || error?.response) {
    return ErrorType.API
  }
  if (
    error instanceof ErrorEvent ||
    (error?.target &&
      (error.target.tagName === 'IMG' ||
        error.target.tagName === 'SCRIPT' ||
        error.target.tagName === 'LINK'))
  ) {
    return ErrorType.RESOURCE
  }
  return ErrorType.UNKNOWN
}

export function getHttpStatusMessage(status) {
  return httpStatusMessages[status] || `服务器响应异常 (${status})`
}

export function collectContext(error) {
  const context = {
    timestamp: new Date().toISOString(),
    url: window.location.href,
    userAgent: navigator.userAgent,
  }

  const token = localStorage.getItem('auth_token')
  if (token) {
    try {
      if (token.startsWith('eyJ')) {
        const payload = JSON.parse(atob(token.split('.')[1]))
        context.userId = payload.sub || payload.user_id
        context.username = payload.username || payload.name
      }
    } catch {
      // ignore
    }
  }

  if (error) {
    context.errorName = error.name
    context.errorMessage = error.message
    context.errorStack = error.stack
    context.errorType = classifyError(error)
    if (error.response) {
      context.httpStatus = error.response.status
      context.responseData = error.response.data
    }
  }

  return context
}

export function formatUserMessage(error) {
  if (error?.response?.status) {
    return getHttpStatusMessage(error.response.status)
  }
  const type = classifyError(error)
  if (DEV) {
    return `${userMessages[type]}\n\n详细信息: ${error.message}`
  }
  return userMessages[type]
}

export function logError(level, message, context = {}) {
  const entry = {
    level,
    message,
    timestamp: new Date().toISOString(),
    ...context,
  }
  switch (level) {
    case LogLevel.INFO:
      console.info('[ErrorHandler]', entry)
      break
    case LogLevel.WARN:
      console.warn('[ErrorHandler]', entry)
      break
    case LogLevel.ERROR:
    default:
      console.error('[ErrorHandler]', entry)
      break
  }
  return entry
}

export function isRetryable(error) {
  const status = error?.response?.status
  return status >= 500 || status === 429 || !status
}
