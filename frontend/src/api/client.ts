import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 60000,
})

export default api

export const pipelineApi = {
  run: (demo = true) => api.post('/pipeline/run', { demo }).then(r => r.data),
  predict: (data: any) => api.post('/life/predict', data).then(r => r.data),
}

export const vizApi = {
  signals: (gauge = 'CH0') => api.get('/viz/signals', { params: { gauge, demo: true } }).then(r => r.data),
  health: () => api.get('/viz/health', { params: { demo: true } }).then(r => r.data),
  events: () => api.get('/viz/events', { params: { demo: true } }).then(r => r.data),
  sync: () => api.get('/viz/sync', { params: { demo: true } }).then(r => r.data),
  life: () => api.get('/viz/life', { params: { demo: true } }).then(r => r.data),
}

export const exportApi = {
  events: () => api.get('/export/events', { responseType: 'blob' }),
  summary: () => api.get('/export/summary').then(r => r.data),
}

export const uploadApi = (file: File) => {
  const fd = new FormData()
  fd.append('file', file)
  return api.post('/upload', fd).then(r => r.data)
}
