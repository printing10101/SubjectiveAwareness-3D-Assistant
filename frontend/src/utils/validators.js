export function validateRequired(value, fieldName = '此字段') {
  if (!value || (typeof value === 'string' && !value.trim())) {
    return `${fieldName}不能为空`
  }
  return ''
}

export function validateLength(value, { min, max } = {}, fieldName = '内容') {
  if (!value) return ''
  const length = typeof value === 'string' ? value.trim().length : String(value).length
  if (min != null && length < min) {
    return `${fieldName}至少需要${min}个字符`
  }
  if (max != null && length > max) {
    return `${fieldName}不能超过${max}个字符`
  }
  return ''
}

export function validateEmail(email) {
  if (!email || !email.trim()) return ''
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(email.trim())) {
    return '请输入有效的邮箱地址'
  }
  return ''
}

export function validateUsername(username) {
  if (!username || !username.trim()) {
    return '用户名不能为空'
  }
  if (username.trim().length < 3) {
    return '用户名至少需要3个字符'
  }
  if (username.trim().length > 30) {
    return '用户名不能超过30个字符'
  }
  const usernameRegex = /^[a-zA-Z0-9_\u4e00-\u9fa5]+$/
  if (!usernameRegex.test(username.trim())) {
    return '用户名只能包含字母、数字、下划线和中文'
  }
  return ''
}

export function validatePassword(password) {
  if (!password) {
    return '密码不能为空'
  }
  if (password.length < 6) {
    return '密码至少需要6个字符'
  }
  if (password.length > 50) {
    return '密码不能超过50个字符'
  }
  return ''
}

export function validateForm(formData, rules) {
  const errors = {}
  for (const [field, validators] of Object.entries(rules)) {
    const value = formData[field]
    for (const validator of validators) {
      const error = validator(value)
      if (error) {
        errors[field] = error
        break
      }
    }
  }
  return {
    errors,
    isValid: Object.keys(errors).length === 0,
  }
}