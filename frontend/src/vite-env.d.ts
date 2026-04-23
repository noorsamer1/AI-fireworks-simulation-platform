/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** When set, browser dev (`pnpm dev`) can reach the sidecar without Tauri IPC. */
  readonly VITE_SIDECAR_PORT?: string;
}
