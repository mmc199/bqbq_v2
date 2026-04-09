import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  // 关键修改 1: 设置基础路径，匹配 Nginx 的 location /g2/
  base: '/g2/', 
  
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    // 关键修改 2: 允许通过域名访问开发服务器
    allowedHosts: [
      'bqbq.mmc199.com'
    ],
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/images': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/thumbnails': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})