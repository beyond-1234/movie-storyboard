import axios from 'axios'
import { ElMessage } from 'element-plus'

const service = axios.create({
  baseURL: '/api', // 配合 Vite proxy 使用
  timeout: 300000
})

service.interceptors.response.use(
  response => response.data,
  error => {
    const msg = error.response?.data?.error || '请求失败'
    // 避免在此处弹出被取消的请求错误
    if (!axios.isCancel(error)) {
      ElMessage.error(msg)
    }
    return Promise.reject(error)
  }
)

export default service