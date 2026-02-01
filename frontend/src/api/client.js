import axios from 'axios'

//const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const baseURL = 'http://localhost:8000'
const api = axios.create({
  baseURL,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default api
