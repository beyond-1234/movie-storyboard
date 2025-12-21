import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      // 1. 处理 API 请求
      '/api': {
        target: 'http://127.0.0.1:5000', // 你的 Flask 后端地址
        changeOrigin: true,
        // 如果后端路由不带 /api 前缀，需要开启 rewrite：
        // rewrite: (path) => path.replace(/^\/api/, '') 
        // 但根据你的旧代码，后端似乎本来就定义了 /api 路由，所以通常不需要 rewrite
      },
      // 2. 处理 WebSocket (Socket.io)
      '/socket.io': {
        target: 'http://127.0.0.1:5000',
        ws: true, // 开启 WebSocket 代理
        changeOrigin: true
      },
      // 3. 处理静态资源 (上传的图片等)
      // 假设后端图片存在 /static 或 /uploads 下
      '/static': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true
      },
      '/uploads': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true
      }
    }
  }
})