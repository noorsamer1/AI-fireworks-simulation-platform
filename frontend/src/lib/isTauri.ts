/** True when the UI runs inside the Tauri webview (not a normal browser tab). */
export function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}
