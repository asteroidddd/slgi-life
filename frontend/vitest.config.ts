// Vitest config — jsdom env + jest-dom matchers + path alias mirror.
//
// 본 설정은 vite.config.ts 와 별도로 두지만 alias 만 미러링한다 (vitest 가
// vite plugin react 는 자동으로 픽업하지 않으므로 jsx 트랜스폼만 ESM 기본 동작).
// React 컴포넌트 테스트 (e.g. HeatMap.test.tsx) 가 동작하려면 plugin react 가
// 필요 — 그래서 plugins 에 react() 도 명시.

import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
});
