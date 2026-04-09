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
    allowedHosts: ['bqbq.mmc199.com'],
    
    proxy: {
      // 🌟 核心修改：将目标指向 8000 (FastAPI 后端)
      '/g2/api': { 
        target: 'http://127.0.0.1:8000', 
        changeOrigin: true,
        // 把前端的 /g2/api/search 还原为 FastAPI 认识的 /api/search
        rewrite: (path) => path.replace(/^\/g2\/api/, '/api')
      },
      '/g2/images': { 
        target: 'http://127.0.0.1:8000', 
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/g2\/images/, '/images')
      },
      '/g2/thumbnails': { 
        target: 'http://127.0.0.1:8000', 
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/g2\/thumbnails/, '/thumbnails')
      }
    },

    hmr: {
      host: 'bqbq.mmc199.com',
      clientPort: 443,
      protocol: 'wss'
    }
  }
})