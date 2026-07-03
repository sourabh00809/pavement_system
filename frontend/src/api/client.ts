import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 60000,
})

export default api

export const pipelineApi = {
  run: (files: { path: string; type: string }[]) =>
    api.post('/pipeline/run', { files }).then(r => r.data),
  status: (taskId: string) => api.get('/pipeline/status/' + taskId).then(r => r.data),
  predict: (data: any) => api.post('/life/predict', data, { timeout: 180000 }).then(r => r.data),
}

export const vizApi = {
  signals: (gauge = 'CH0', group = 'VER') =>
    api.get('/viz/signals', { params: { gauge, group } }).then(r => r.data),
  signalsAll: () => api.get('/viz/signals/all').then(r => r.data),
  health: () => api.get('/viz/health').then(r => r.data),
  events: () => api.get('/viz/events').then(r => r.data),
  sync: () => api.get('/viz/sync').then(r => r.data),
  life: () => api.get('/viz/life').then(r => r.data),
  strains: () => api.get('/viz/strains').then(r => r.data),
  resultsTable: () => api.get('/viz/results/table').then(r => r.data),
  temperature: (offset10 = 0, offset11 = 0) =>
    api.get('/viz/temperature', { params: { offset_ch10: offset10, offset_ch11: offset11 } }).then(r => r.data),
  refresh: () => api.post('/refresh').then(r => r.data),
}

export const exportApi = {
  events: (group = 'all') => api.get('/export/events', { params: { group }, responseType: 'blob' }),
  summary: () => api.get('/export/summary').then(r => r.data),
  results: () => api.get('/export/results', { responseType: 'blob' }),
}

export const uploadApi = (file: File) => {
  const fd = new FormData()
  fd.append('file', file)
  return api.post('/upload', fd, { timeout: 120000 }).then(r => r.data)
}

export const uploadPathsApi = {
  save: (files: { path: string; type: string }[]) =>
    api.post('/upload/paths', { files }).then(r => r.data),
  status: () => api.get('/upload/paths').then(r => r.data),
}
