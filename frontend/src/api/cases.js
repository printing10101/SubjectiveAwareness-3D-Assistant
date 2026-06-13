import apiClient from './client.js'

export function fetchCases(params = {}) {
  return apiClient.get('/api/cases', { params })
}

export function fetchCaseById(id) {
  return apiClient.get(`/api/cases/${id}`)
}

export function createCase(caseData) {
  return apiClient.post('/api/cases', caseData)
}

export function updateCase(id, caseData) {
  return apiClient.put(`/api/cases/${id}`, caseData)
}

export function deleteCase(id) {
  return apiClient.delete(`/api/cases/${id}`)
}

export function fetchCaseAnalysis(id) {
  return apiClient.get(`/api/cases/${id}/analysis`)
}