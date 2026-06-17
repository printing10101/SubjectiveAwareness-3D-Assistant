import apiClient from './client.js'

export function login(username, password) {
  return apiClient.post('/api/auth/login', { username, password })
}

export function logout() {
  return apiClient.post('/api/auth/logout')
}

export function refreshToken(refreshTokenValue) {
  return apiClient.post('/api/auth/refresh', {
    refresh_token: refreshTokenValue,
  })
}

export function getCurrentUser() {
  return apiClient.get('/api/auth/me')
}