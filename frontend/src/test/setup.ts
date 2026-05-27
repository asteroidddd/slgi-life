// Vitest setup — global jest-dom matchers + browser polyfills required by
// libraries we use (Recharts uses ResizeObserver, Leaflet uses matchMedia /
// getBoundingClientRect 자체는 jsdom 에서 0 으로 떨어지지만 throw 안 함).
//
// 본 파일은 vitest.config.ts 의 setupFiles 로 자동 로드된다.

import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// Recharts 가 ResizeObserver 를 요구. jsdom 에는 없으므로 no-op 클래스 주입.
class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

if (typeof globalThis.ResizeObserver === 'undefined') {
  (globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
    ResizeObserverStub;
}

// matchMedia stub (일부 라이브러리가 미디어 쿼리 호출).
if (typeof window !== 'undefined' && typeof window.matchMedia === 'undefined') {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {}, // legacy
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

// 각 테스트 후 RTL 마운트된 DOM 정리.
afterEach(() => {
  cleanup();
});
