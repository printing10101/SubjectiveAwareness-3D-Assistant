// 协议状态共享组合式函数。
//
// 提供全应用范围内一致的"用户是否已接受协议"判定与接受操作入口。
// 接受状态持久化在 localStorage 中，键名集中管理以便升级与回滚。

const AGREEMENT_STORAGE_KEY = 'user_agreement_accepted_v1'

export function isAgreementAccepted() {
  try {
    const raw = localStorage.getItem(AGREEMENT_STORAGE_KEY)
    if (!raw) {
      return false
    }
    const parsed = JSON.parse(raw)
    return Boolean(parsed?.accepted)
  } catch {
    return false
  }
}

export function acceptAgreement() {
  const now = new Date().toISOString()
  localStorage.setItem(
    AGREEMENT_STORAGE_KEY,
    JSON.stringify({ accepted: true, at: now, version: 'v1' }),
  )
  return now
}

export function revokeAgreement() {
  localStorage.removeItem(AGREEMENT_STORAGE_KEY)
}
