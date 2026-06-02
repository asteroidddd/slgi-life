/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_KAKAO_JS_KEY?: string;
  readonly VITE_MAP_TILE_URL?: string;
  readonly VITE_AI_AGENT_PUBLIC_MODE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
