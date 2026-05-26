import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,   // 2 minutes — predictions take ~60s
})

export const getHealth        = ()      => api.get('/health')
export const getLatest        = (n=20)  => api.get(`/latest?limit=${n}`)
export const getStats         = (draw)  => api.get(`/stats/${draw}`)
export const getNumbers       = (draw)  => api.get(`/numbers/${draw}`)
export const getAnalysis      = (draw)  => api.get(`/analysis/${draw}`)
export const getPredictions   = (draw, n=5) => api.get(`/predictions/${draw}?n_tickets=${n}`)

export default api