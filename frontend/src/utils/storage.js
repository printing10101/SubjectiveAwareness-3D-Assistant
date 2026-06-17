const PREFIX = 'app_'

export function getItem(key) {
  try {
    return localStorage.getItem(PREFIX + key)
  } catch {
    return null
  }
}

export function setItem(key, value) {
  try {
    localStorage.setItem(PREFIX + key, value)
  } catch {
    // 静默失败（存储满或隐私模式）
  }
}

export function removeItem(key) {
  try {
    localStorage.removeItem(PREFIX + key)
  } catch {
    // 静默失败
  }
}

export function getJSON(key) {
  try {
    const value = getItem(key)
    return value ? JSON.parse(value) : null
  } catch {
    return null
  }
}

export function setJSON(key, value) {
  try {
    setItem(key, JSON.stringify(value))
  } catch {
    // 静默失败
  }
}

export function clearAll() {
  const keysToRemove = []
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key && key.startsWith(PREFIX)) {
      keysToRemove.push(key)
    }
  }
  keysToRemove.forEach((key) => {
    try {
      localStorage.removeItem(key)
    } catch {
      // 静默失败
    }
  })
}

export function getToken() {
  return localStorage.getItem('auth_token')
}

export function setAccessToken(token) {
  localStorage.setItem('auth_token', token)
}

export function setRefreshTokenValue(token) {
  localStorage.setItem('refresh_token', token)
}

export function removeTokens() {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('refresh_token')
}