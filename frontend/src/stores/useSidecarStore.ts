import { invoke } from "@tauri-apps/api/core";
import { create } from "zustand";

import { isTauri } from "../lib/isTauri";

type SidecarStore = {
  /** OS-assigned localhost port for the Python sidecar, or null before init. */
  port: number | null;
  /** True after port is known (Tauri IPC or VITE_SIDECAR_PORT in browser). */
  ready: boolean;
  /** Resolve sidecar port from Tauri IPC or optional VITE_SIDECAR_PORT (browser dev). */
  init: () => Promise<void>;
};

function parseBrowserSidecarPort(): number | null {
  const raw = import.meta.env.VITE_SIDECAR_PORT;
  if (raw == null || String(raw).trim() === "") {
    return null;
  }
  const port = Number.parseInt(String(raw), 10);
  if (!Number.isFinite(port) || port < 1 || port > 65535) {
    return null;
  }
  return port;
}

export const useSidecarStore = create<SidecarStore>((set) => ({
  port: null,
  ready: false,
  init: async () => {
    if (isTauri()) {
      const port = await invoke<number>("get_sidecar_port");
      set({ port, ready: true });
      return;
    }
    const port = parseBrowserSidecarPort();
    if (port == null) {
      throw new Error("browser_preview_without_sidecar_port");
    }
    set({ port, ready: true });
  },
}));
