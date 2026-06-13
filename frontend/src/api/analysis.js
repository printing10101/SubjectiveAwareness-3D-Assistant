import apiClient from './client.js'

export function runAnalysis(caseText, options = {}) {
  return apiClient.post('/api/analyze', {
    case_text: caseText,
    ...options,
  })
}

export function fetchAnalysisResult(analysisId) {
  return apiClient.get(`/api/analyze/${analysisId}`)
}

export function fetchAnalysisHistory(params = {}) {
  return apiClient.get('/api/analyze/history', { params })
}

export function fetchKnowledgeEntries(params = {}) {
  return apiClient.get('/api/knowledge/entries', { params })
}

export function fetchKnowledgeEntryById(id) {
  return apiClient.get(`/api/knowledge/entries/${id}`)
}