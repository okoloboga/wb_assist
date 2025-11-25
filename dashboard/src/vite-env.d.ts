/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_API_SECRET_KEY: string
  readonly VITE_TELEGRAM_ID: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
