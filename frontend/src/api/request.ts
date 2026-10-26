import axios from 'axios'

// 流式接口走原生 fetch，拿不到 axios 的 baseURL，这里统一暴露前缀
export const API_BASE_URL = '/api'

const request = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => Promise.reject(error),
)

export default request
