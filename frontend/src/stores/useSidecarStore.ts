import { invoke } from "@tauri-apps/api/core";
import { create } from "zustand";

type SidecarStore = {
  /** OS-assigned localhost port for the Python sidecar, or null before init. */
  port: number | null;
  /** True after `get_sidecar_port` IPC succeeds. */
  ready: boolean;
  /** Load port from Tauri (must run inside the Tauri webview). */
  init: () => Promise<void>;
};

export const useSidecarStore = create<SidecarStore>((set) => ({
  port: null,
  ready: false,
  init: async () => {
    const port = await invoke<number>("get_sidecar_port");
    set({ port, ready: true });
  },
}));
