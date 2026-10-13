import react from '@vitejs/plugin-react'
import { loadEnv } from 'vite'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  // Cloudflare Pages 빌드(CF_PAGES=1)에서 API 주소가 빠지면 localhost로 조용히 빌드되므로 막는다.
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  if (command === 'build' && process.env.CF_PAGES && !env.VITE_API_BASE_URL) {
    throw new Error(
      'VITE_API_BASE_URL이 빌드 환경에 없습니다. Cloudflare Pages 설정에서 이 변수를 Text 형식으로 이 환경(Production/Preview)에 추가하세요.',
    )
  }

  return {
    plugins: [react()],
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
    },
  }
})
