import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/static/' : '/',
  // 개발 서버에서도 /api 를 같은 출처로 보이게 Django(8000)로 넘긴다.
  // 이게 없으면 dev 서버가 /api/v1/* 를 직접 받아 SPA 문서를 돌려주고,
  // 백엔드 상태와 무관하게 모든 화면이 목업 폴백으로 떨어진다.
  // 배포는 Django 가 프론트 정적 파일까지 함께 서빙하므로 프록시가 필요 없다.
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  plugins: [
    react(),
    tailwindcss(),
  ],
}))