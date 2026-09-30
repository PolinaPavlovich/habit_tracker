/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  /** Set by scripts/seed.py in frontend/.env.development.local. Dev server only. */
  readonly VITE_DEV_TOKEN?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
