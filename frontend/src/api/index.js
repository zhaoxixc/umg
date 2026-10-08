import axios from 'axios'
import { clearAuth, getAuth } from '../auth'

const http = axios.create({ baseURL: '/api', timeout: 15000 })

http.interceptors.request.use((config) => {
  const { token } = getAuth()
  if (token.value) config.headers.Authorization = `Bearer ${token.value}`
  return config
})

http.interceptors.response.use(
  (resp) => resp,
  (error) => {
    if (error?.response?.status === 401 && !location.hash.includes('login')) {
      clearAuth()
      window.location.reload()
    }
    return Promise.reject(error)
  }
)

// ---------- 认证 ----------
export const login = (data) => http.post('/auth/login', data)
export const getMe = () => http.get('/auth/me')
export const changePassword = (data) => http.post('/auth/change-password', data)

// ---------- 用户管理（admin） ----------
export const listUsers = () => http.get('/users')
export const createUser = (data) => http.post('/users', data)
export const updateUser = (id, data) => http.put(`/users/${id}`, data)
export const deleteUser = (id) => http.delete(`/users/${id}`)

// ---------- 审计日志（admin） ----------
export const listAudit = (params = {}) => http.get('/audit', { params })

// ---------- 位置树 ----------
export const getTree = (q = '') => http.get('/locations/tree', { params: { q } })
export const createDataCenter = (data) => http.post('/locations/datacenters', data)
export const createRoom = (data) => http.post('/locations/rooms', data)
export const createGroup = (data) => http.post('/locations/groups', data)
export const createRack = (data) => http.post('/locations/racks', data)
export const updateDataCenter = (id, data) => http.put(`/locations/datacenters/${id}`, data)
export const updateRoom = (id, data) => http.put(`/locations/rooms/${id}`, data)
export const updateGroup = (id, data) => http.put(`/locations/groups/${id}`, data)
export const updateRack = (id, data) => http.put(`/locations/racks/${id}`, data)
export const deleteLocation = (type, id) => http.delete(`/locations/${type}/${id}`)

// ---------- 机柜 ----------
export const getRackView = (id) => http.get(`/racks/${id}/view`)
export const getRackStats = (id) => http.get(`/racks/${id}/stats`)
export const getRackEvents = (id, scope = 'realtime', params = {}) =>
  http.get(`/racks/${id}/events`, { params: { scope, ...params } })

// ---------- 资产 ----------
export const listAssets = (params = {}) => http.get('/assets', { params })

function saveBlob(resp, fallback) {
  const cd = resp.headers['content-disposition'] || ''
  const m = cd.match(/filename\*=UTF-8''([^;\s]+)/)
  const name = m ? decodeURIComponent(m[1]) : fallback
  const url = URL.createObjectURL(resp.data)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  a.click()
  URL.revokeObjectURL(url)
}

export const exportAssets = (params = {}) =>
  http.get('/assets/export', { params, responseType: 'blob' })
    .then((r) => saveBlob(r, 'assets.xlsx'))

export const downloadImportTemplate = () =>
  http.get('/assets/import-template', { responseType: 'blob' })
    .then((r) => saveBlob(r, 'asset_import_template.xlsx'))

export const importAssets = (file) => {
  const fd = new FormData()
  fd.append('file', file)
  return http.post('/assets/import', fd)
}

export const getAssetHistory = (id) => http.get(`/assets/${id}/history`)

// ---------- 备份（admin） ----------
export const listBackups = () => http.get('/backups')
export const createBackup = () => http.post('/backups')
export const downloadBackup = (name) =>
  http.get(`/backups/${encodeURIComponent(name)}/download`, { responseType: 'blob' })
    .then((r) => saveBlob(r, name))
export const restoreBackup = (name) =>
  http.post(`/backups/${encodeURIComponent(name)}/restore`)
export const deleteBackup = (name) =>
  http.delete(`/backups/${encodeURIComponent(name)}`)

export const getOverview = () => http.get('/assets/overview')
export const getHomeStats = () => http.get('/stats/home')
export const getAllEvents = (scope = 'realtime', params = {}) =>
  http.get('/assets/events', { params: { scope, ...params } })
export const createAsset = (data) => http.post('/assets', data)
export const updateAsset = (id, data) => http.put(`/assets/${id}`, data)
export const rackOn = (id, data) => http.post(`/assets/${id}/rack-on`, data)
export const rackOff = (id) => http.post(`/assets/${id}/rack-off`)
export const deleteAsset = (id) => http.delete(`/assets/${id}`)

export const errMsg = (e) => e?.response?.data?.detail || String(e)
