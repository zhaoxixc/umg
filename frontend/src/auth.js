import { ref } from 'vue'

const token = ref(localStorage.getItem('token') || '')
const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

export function getAuth() {
  return { token, user }
}

export function setAuth(t, u) {
  token.value = t
  user.value = u
  localStorage.setItem('token', t)
  localStorage.setItem('user', JSON.stringify(u))
}

export function clearAuth() {
  token.value = ''
  user.value = null
  localStorage.removeItem('token')
  localStorage.removeItem('user')
}

export const ROLE_NAMES = { admin: '管理员', operator: '运维', viewer: '只读' }

export function hasAny(...roles) {
  return roles.includes(user.value?.role)
}
