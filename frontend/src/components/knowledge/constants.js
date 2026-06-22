const categories = [
  { key: 'legal_provision', label: '法律条文' },
  { key: 'analysis_method', label: '分析方法' },
  { key: 'historical_case', label: '历史案例' },
]

const categoryTree = [
  {
    key: 'legal_provision',
    label: '法律条文',
    expanded: true,
    children: [
      { key: 'criminal_law', label: '刑法' },
      { key: 'criminal_procedure_law', label: '刑事诉讼法' },
      { key: 'judicial_interpretation', label: '司法解释' },
    ],
  },
  {
    key: 'analysis_method',
    label: '分析方法',
    expanded: true,
    children: [
      { key: 'evidence_analysis', label: '证据分析方法' },
      { key: 'legal_reasoning', label: '法律推理方法' },
      { key: 'case_comparison', label: '案例比较方法' },
    ],
  },
  {
    key: 'historical_case',
    label: '历史案例',
    expanded: false,
    children: [
      { key: 'precedent_case', label: '判例' },
      { key: 'typical_case', label: '典型案例' },
      { key: 'reference_case', label: '参考案例' },
    ],
  },
]

const sortOptions = [
  { value: 'created_at', label: '创建时间' },
  { value: 'updated_at', label: '更新时间' },
  { value: 'confidence_score', label: '信心评分' },
]

const pageSizeOptions = [8, 12, 20, 40]

function formatTime(dateStr) {
  if (!dateStr) return '—'
  try {
    const d = new Date(dateStr)
    const pad = (n) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
  } catch {
    return dateStr
  }
}

function getCategoryLabel(key) {
  const found = categories.find((c) => c.key === key)
  if (found) return found.label
  for (const cat of categoryTree) {
    if (cat.key === key) return cat.label
    for (const child of cat.children) {
      if (child.key === key) return child.label
    }
  }
  return key || '未分类'
}

function getConfidenceStars(score) {
  const s = Math.round((score || 0) * 5)
  return '★'.repeat(s) + '☆'.repeat(5 - s)
}

export {
  categories,
  categoryTree,
  sortOptions,
  pageSizeOptions,
  formatTime,
  getCategoryLabel,
  getConfidenceStars,
}
