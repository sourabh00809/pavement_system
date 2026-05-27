import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
})

export default api

export const pipelineApi = {
  run: (demo = true) => api.post('/pipeline/run', { demo }).then(r => r.data),
  predict: (data: any) => api.post('/life/predict', data).then(r => r.data),
}

export const vizApi = {
  signals: (gauge = 'CH0') => api.get('/viz/signals', { params: { gauge } }).then(r => r.data),
  signalsAll: () => api.get('/viz/signals/all').then(r => r.data),
  health: () => api.get('/viz/health').then(r => r.data),
  events: () => api.get('/viz/events').then(r => r.data),
  sync: () => api.get('/viz/sync').then(r => r.data),
  life: () => api.get('/viz/life').then(r => r.data),
  strains: () => api.get('/viz/strains').then(r => r.data),
  temperature: (offset10 = 0, offset11 = 0) => api.get('/viz/temperature', { params: { offset_ch10: offset10, offset_ch11: offset11 } }).then(r => r.data),
  refresh: () => api.post('/refresh').then(r => r.data),
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
