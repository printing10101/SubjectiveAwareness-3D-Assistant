import axios from 'axios'

const apiClient = axios.create({
  baseURL: '',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error

    if (!config) {
      return Promise.reject(error)
    }

    const status = response?.status

    if (status === 401 && !config._retryAuth) {
      config._retryAuth = true
      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (!refreshToken) {
          throw new Error('No refresh token')
        }
        const res = await axios.post('/api/auth/refresh', {
          refresh_token: refreshToken,
        })
        const { access_token, refresh_token } = res.data
        localStorage.setItem('auth_token', access_token)
        if (refresh_token) {
          localStorage.setItem('refresh_token', refresh_token)
        }
        config.headers.Authorization = `Bearer ${access_token}`
        return apiClient(config)
      } catch {
        localStorage.removeItem('auth_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject({
          message: '认证已过期，请重新登录',
          status: 401,
          requiresLogin: true,
        })
      }
    }

    const normalizedError = {
      message: extractErrorMessage(error),
      status: status || 0,
      data: response?.data || null,
    }

    return Promise.reject(normalizedError)
  }
)

function extractErrorMessage(error) {
  if (error.response?.data?.detail) {
    return error.response.data.detail
  }
  if (error.response?.data?.message) {
    return error.response.data.message
  }
  if (error.message) {
    return error.message
  }
  return '请求失败'
}

export default apiClient