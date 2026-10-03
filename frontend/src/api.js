import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  withCredentials: false,
  headers: { 'Content-Type': 'application/json' },
})

let getToken = () => null
export function setTokenGetter(fn) { getToken = fn }

api.interceptors.request.use((cfg) => {
  const t = getToken()
  if (t) cfg.headers.Authorization = `Bearer ${t}`
  return cfg
})

export const auth = {
  login: (data) => api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
}
export const users = {
  list: () => api.get('/users/'),
  create: (data) => api.post('/users/', data),
  update: (id, data) => api.put(`/users/${id}`, data),
  remove: (id) => api.delete(`/users/${id}`),
}
export const projects = {
  list: () => api.get('/projects/'),
  create: (data) => api.post('/projects/', data),
  upload: (id, files) => {
    const fd = new FormData()
    files.forEach((f) => fd.append('files', f))
    return api.post(`/projects/${id}/upload`, fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  deleteFile: (pid, fid) => api.delete(`/projects/${pid}/files/${fid}`),
}
export const checks = {
  run: (data) => api.post('/checks/run', data),
  getRun: (id) => api.get(`/checks/run/${id}`),
  listRuns: (pid) => api.get(`/checks/project/${pid}`),
  deleteRun: (id) => api.delete(`/checks/run/${id}`),
}
export const ntd = {
  list: () => api.get('/ntd/'),
  actualCheck: () => api.get('/ntd/actual-check'),
  create: (data) => api.post('/ntd/', data),
  update: (id, data) => api.put(`/ntd/${id}`, data),
  remove: (id) => api.delete(`/ntd/${id}`),
}
export const aiModels = {
  list: () => api.get('/ai-models/'),
  plugins: () => api.get('/ai-models/plugins'),
  capabilities: (id) => api.get(`/ai-models/capabilities`, { params: { model_id: id } }),
  create: (data) => api.post('/ai-models/', data),
  update: (id, data) => api.put(`/ai-models/${id}`, data),
  remove: (id) => api.delete(`/ai-models/${id}`),
}
export const reports = {
  generate: (data) => api.post('/reports/generate', data),
  exportRun: (id, fmt = 'json') => api.get(`/reports/run/${id}?fmt=${fmt}`),
  deleteRun: (id) => api.delete(`/reports/run/${id}`),
}
export default api