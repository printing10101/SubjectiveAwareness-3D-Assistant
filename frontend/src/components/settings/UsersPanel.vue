<script setup>
import { ref, computed } from 'vue'

import axios from 'axios'

const props = defineProps({
  errorMsg: {
    type: Object,
    default: () => ({ value: null }),
  },
})

const users = ref([])
const usersTotal = ref(0)
const usersPage = ref(1)
const usersPageSize = ref(10)
const isUsersLoading = ref(false)

const usersTotalPages = computed(() => Math.max(1, Math.ceil(usersTotal.value / usersPageSize.value)))

const isUserDialogVisible = ref(false)
const userForm = ref({ username: '', password: '', role: 'user' })
const userFormErrors = ref({})
const isUserSubmitting = ref(false)

const isResetPwdDialogVisible = ref(false)
const resetPwdTarget = ref(null)
const resetPwdForm = ref({ new_password: '' })
const resetPwdErrors = ref({})
const isResetPwdSubmitting = ref(false)

async function fetchUsers() {
  isUsersLoading.value = true
  try {
    const params = { page: usersPage.value, page_size: usersPageSize.value }
    const res = await axios.get('/api/users', { params })
    users.value = res.data.items || []
    usersTotal.value = res.data.total || 0
  } catch (err) {
    props.errorMsg.value = err.message || '获取用户列表失败'
    users.value = []
  } finally {
    isUsersLoading.value = false
  }
}

function handleOpenCreateUser() {
  userForm.value = { username: '', password: '', role: 'user' }
  userFormErrors.value = {}
  isUserDialogVisible.value = true
}

function handleCloseUserDialog() {
  isUserDialogVisible.value = false
}

function validateUserForm() {
  const errors = {}
  if (!userForm.value.username.trim()) errors.username = '用户名不能为空'
  if (!userForm.value.password.trim()) errors.password = '密码不能为空'
  if (userForm.value.password.length < 6) errors.password = '密码至少6位'
  userFormErrors.value = errors
  return Object.keys(errors).length === 0
}

async function handleSubmitUser() {
  if (!validateUserForm()) return
  isUserSubmitting.value = true
  try {
    await axios.post('/api/users', userForm.value)
    handleCloseUserDialog()
    fetchUsers()
  } catch (err) {
    props.errorMsg.value = err.message || '创建用户失败'
  } finally {
    isUserSubmitting.value = false
  }
}

async function handleDeleteUser(user) {
  if (!confirm(`确定要删除用户「${user.username}」吗？`)) return
  try {
    await axios.delete(`/api/users/${user.id}`)
    if (users.value.length === 1 && usersPage.value > 1) usersPage.value--
    fetchUsers()
  } catch (err) {
    props.errorMsg.value = err.message || '删除用户失败'
  }
}

function handleOpenResetPassword(user) {
  resetPwdTarget.value = user
  resetPwdForm.value = { new_password: '' }
  resetPwdErrors.value = {}
  isResetPwdDialogVisible.value = true
}

function handleCloseResetPassword() {
  isResetPwdDialogVisible.value = false
  resetPwdTarget.value = null
}

function validateResetPasswordForm() {
  const errors = {}
  if (!resetPwdForm.value.new_password.trim()) errors.new_password = '新密码不能为空'
  if (resetPwdForm.value.new_password.length < 6) errors.new_password = '密码至少6位'
  resetPwdErrors.value = errors
  return Object.keys(errors).length === 0
}

async function handleSubmitResetPassword() {
  if (!validateResetPasswordForm()) return
  isResetPwdSubmitting.value = true
  try {
    await axios.put(`/api/users/${resetPwdTarget.value.id}/password`, resetPwdForm.value)
    handleCloseResetPassword()
  } catch (err) {
    props.errorMsg.value = err.message || '重置密码失败'
  } finally {
    isResetPwdSubmitting.value = false
  }
}

function handleGoToUsersPage(page) {
  if (page < 1 || page > usersTotalPages.value || page === usersPage.value) return
  usersPage.value = page
  fetchUsers()
}

function getUsersPaginationPages() {
  const pages = []
  const tp = usersTotalPages.value
  if (tp <= 7) {
    for (let i = 1; i <= tp; i++) pages.push(i)
  } else {
    pages.push(1)
    if (usersPage.value > 3) pages.push('...')
    const start = Math.max(2, usersPage.value - 1)
    const end = Math.min(tp - 1, usersPage.value + 1)
    for (let i = start; i <= end; i++) pages.push(i)
    if (usersPage.value < tp - 2) pages.push('...')
    pages.push(tp)
  }
  return pages
}

function formatTime(dateStr) {
  if (!dateStr) return '—'
  try {
    const d = new Date(dateStr)
    const pad = (n) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  } catch {
    return dateStr
  }
}

defineExpose({
  fetchUsers,
  users,
  usersTotal,
  usersPage,
  usersPageSize,
  isUsersLoading,
  usersTotalPages,
  handleOpenCreateUser,
  handleCloseUserDialog,
  handleSubmitUser,
  handleDeleteUser,
  handleOpenResetPassword,
  handleCloseResetPassword,
  handleSubmitResetPassword,
  handleGoToUsersPage,
  getUsersPaginationPages,
  formatTime,
  userForm,
  userFormErrors,
  isUserDialogVisible,
  isUserSubmitting,
  isResetPwdDialogVisible,
  resetPwdTarget,
  resetPwdForm,
  resetPwdErrors,
  isResetPwdSubmitting,
})
</script>

<template>
  <div class="users-panel">
    <div class="panel-header">
      <h3 class="panel-title">用户管理</h3>
      <button class="btn btn-primary btn-sm" @click="handleOpenCreateUser">
        <span class="btn-icon">+</span>
        新建用户
      </button>
    </div>

    <div v-if="isUsersLoading" class="loading-state">加载中...</div>

    <div v-else class="users-list">
      <div v-for="user in users" :key="user.id" class="user-card card">
        <div class="user-header">
          <div class="user-info">
            <span class="user-name">{{ user.username }}</span>
            <span class="user-role" :class="user.role">{{ user.role }}</span>
          </div>
          <div class="user-actions">
            <button class="btn btn-ghost btn-sm" @click="handleOpenResetPassword(user)">
              重置密码
            </button>
            <button class="btn btn-danger btn-sm" @click="handleDeleteUser(user)">
              删除
            </button>
          </div>
        </div>
        <div class="user-meta">
          <span v-if="user.created_at" class="meta-item">
            <span class="meta-label">创建时间：</span>{{ formatTime(user.created_at) }}
          </span>
        </div>
      </div>

      <div v-if="users.length === 0" class="empty-state">
        <p>暂无用户</p>
      </div>
    </div>

    <div v-if="usersTotalPages > 1" class="pagination">
      <button
        class="pagination-btn"
        :disabled="usersPage === 1"
        @click="handleGoToUsersPage(usersPage - 1)"
      >
        ‹
      </button>
      <button
        v-for="page in getUsersPaginationPages()"
        :key="page"
        class="pagination-btn"
        :class="{ active: page === usersPage, disabled: page === '...' }"
        :disabled="page === '...'"
        @click="handleGoToUsersPage(page)"
      >
        {{ page }}
      </button>
      <button
        class="pagination-btn"
        :disabled="usersPage === usersTotalPages"
        @click="handleGoToUsersPage(usersPage + 1)"
      >
        ›
      </button>
    </div>

    <!-- 新建用户对话框 -->
    <div v-if="isUserDialogVisible" class="dialog-overlay" @click.self="handleCloseUserDialog">
      <div class="dialog-content card">
        <div class="dialog-header">
          <h3 class="dialog-title">新建用户</h3>
          <button class="dialog-close" @click="handleCloseUserDialog">×</button>
        </div>
        <form @submit.prevent="handleSubmitUser" class="dialog-body">
          <div class="form-group">
            <label class="form-label">用户名</label>
            <input v-model="userForm.username" type="text" class="form-input" />
            <span v-if="userFormErrors.username" class="form-error">{{ userFormErrors.username }}</span>
          </div>
          <div class="form-group">
            <label class="form-label">密码</label>
            <input v-model="userForm.password" type="password" class="form-input" />
            <span v-if="userFormErrors.password" class="form-error">{{ userFormErrors.password }}</span>
          </div>
          <div class="form-group">
            <label class="form-label">角色</label>
            <select v-model="userForm.role" class="form-select">
              <option value="user">普通用户</option>
              <option value="admin">管理员</option>
            </select>
          </div>
          <div class="dialog-footer">
            <button type="button" class="btn btn-ghost" @click="handleCloseUserDialog">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="isUserSubmitting">
              {{ isUserSubmitting ? '创建中...' : '创建' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 重置密码对话框 -->
    <div v-if="isResetPwdDialogVisible" class="dialog-overlay" @click.self="handleCloseResetPassword">
      <div class="dialog-content card">
        <div class="dialog-header">
          <h3 class="dialog-title">重置密码</h3>
          <button class="dialog-close" @click="handleCloseResetPassword">×</button>
        </div>
        <form @submit.prevent="handleSubmitResetPassword" class="dialog-body">
          <p class="dialog-desc">为用户「{{ resetPwdTarget?.username }}」设置新密码</p>
          <div class="form-group">
            <label class="form-label">新密码</label>
            <input v-model="resetPwdForm.new_password" type="password" class="form-input" />
            <span v-if="resetPwdErrors.new_password" class="form-error">{{ resetPwdErrors.new_password }}</span>
          </div>
          <div class="dialog-footer">
            <button type="button" class="btn btn-ghost" @click="handleCloseResetPassword">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="isResetPwdSubmitting">
              {{ isResetPwdSubmitting ? '重置中...' : '重置' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.users-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-title {
  font-size: var(--text-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0;
}

.loading-state,
.empty-state {
  padding: var(--space-8);
  text-align: center;
  color: var(--text-tertiary);
}

.users-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.user-card {
  padding: var(--space-4);
}

.user-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
}

.user-info {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.user-name {
  font-size: var(--text-base);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.user-role {
  display: inline-block;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-weight-medium);
}

.user-role.admin {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.user-role.user {
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.user-actions {
  display: flex;
  gap: var(--space-2);
}

.user-meta {
  display: flex;
  gap: var(--space-3);
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.meta-label {
  color: var(--text-tertiary);
}

.pagination {
  display: flex;
  justify-content: center;
  gap: var(--space-1);
  margin-top: var(--space-4);
}

.pagination-btn {
  padding: var(--space-1) var(--space-2);
  min-width: 32px;
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.pagination-btn:hover:not(:disabled) {
  background: var(--bg-secondary);
  border-color: var(--border-secondary);
}

.pagination-btn.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal);
}

.dialog-content {
  width: 90%;
  max-width: 400px;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-primary);
}

.dialog-title {
  font-size: var(--text-lg);
  font-weight: var(--font-weight-semibold);
  margin: 0;
}

.dialog-close {
  background: none;
  border: none;
  font-size: var(--text-2xl);
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
}

.dialog-close:hover {
  background: var(--bg-secondary);
}

.dialog-body {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.dialog-desc {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin: 0;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.form-label {
  font-size: var(--text-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.form-input,
.form-select {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-family: inherit;
}

.form-error {
  font-size: var(--text-xs);
  color: var(--color-danger);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-primary);
}
</style>
