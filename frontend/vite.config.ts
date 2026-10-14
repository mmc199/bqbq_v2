import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
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
    allowedHosts: ['bqbq.mmc199.com',
      'bqbq-4.mmc199.com',
      'bqbq-4.mmc199.com.a1.initaj.com'],
    
    proxy: {
      // 🌟 核心修改：将目标指向 8000 (FastAPI 后端)
      '/g2/api': { 
        target: 'http://127.0.0.1:8000', 
        changeOrigin: true,
        // 把前端的 /g2/api/search 还原为 FastAPI 认识的 /api/search
        rewrite: (path) => path.replace(/^\/g2\/api/, '/api')
      },
// 🌟 新增：专门为了本地 localhost:5173 测试用的图片代理
      '/images': {
        target: 'http://127.0.0.1:8000', // 指向你的 FastAPI 后端
        changeOrigin: true
        // 这里不需要 rewrite，因为前端请求 /images 刚好对应后端的 /images
      },
      '/thumbnails': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    },

    hmr: {
      // 省略 host，浏览器会自动使用当前访问的域名进行 WebSocket 连接] host: 'bqbq.mmc199.com',
      clientPort: 443,
      protocol: 'wss'
    }
  }
})