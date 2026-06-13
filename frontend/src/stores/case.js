import { ref, computed } from 'vue'

import { defineStore } from 'pinia'

export const useCaseStore = defineStore('case', () => {
  const caseList = ref([])
  const currentCase = ref(null)
  const totalCases = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(10)
  const isCaseLoading = ref(false)
  const caseError = ref(null)
  const searchKeyword = ref('')
  const filterStatus = ref('')

  const hasCases = computed(() => caseList.value.length > 0)

  const totalPages = computed(() =>
    Math.max(1, Math.ceil(totalCases.value / pageSize.value))
  )

  const hasNextPage = computed(() => currentPage.value < totalPages.value)

  const hasPrevPage = computed(() => currentPage.value > 1)

  function setCaseList(cases, total) {
    caseList.value = cases || []
    totalCases.value = total || 0
  }

  function setCurrentCase(caseData) {
    currentCase.value = caseData
  }

  function addCase(newCase) {
    caseList.value.unshift(newCase)
    totalCases.value++
  }

  function updateCase(updatedCase) {
    const index = caseList.value.findIndex(
      (c) => c.id === updatedCase.id
    )
    if (index !== -1) {
      caseList.value[index] = updatedCase
    }
    if (currentCase.value?.id === updatedCase.id) {
      currentCase.value = updatedCase
    }
  }

  function removeCase(caseId) {
    caseList.value = caseList.value.filter((c) => c.id !== caseId)
    totalCases.value = Math.max(0, totalCases.value - 1)
    if (currentCase.value?.id === caseId) {
      currentCase.value = null
    }
  }

  function setPage(page) {
    currentPage.value = page
  }

  function setSearchKeyword(keyword) {
    searchKeyword.value = keyword
  }

  function setFilterStatus(status) {
    filterStatus.value = status
  }

  function setCaseLoading(loading) {
    isCaseLoading.value = loading
  }

  function setCaseError(error) {
    caseError.value = error
  }

  function clearCaseError() {
    caseError.value = null
  }

  function reset() {
    caseList.value = []
    currentCase.value = null
    totalCases.value = 0
    currentPage.value = 1
    pageSize.value = 10
    isCaseLoading.value = false
    caseError.value = null
    searchKeyword.value = ''
    filterStatus.value = ''
  }

  return {
    caseList,
    currentCase,
    totalCases,
    currentPage,
    pageSize,
    isCaseLoading,
    caseError,
    searchKeyword,
    filterStatus,
    hasCases,
    totalPages,
    hasNextPage,
    hasPrevPage,
    setCaseList,
    setCurrentCase,
    addCase,
    updateCase,
    removeCase,
    setPage,
    setSearchKeyword,
    setFilterStatus,
    setCaseLoading,
    setCaseError,
    clearCaseError,
    reset,
  }
})