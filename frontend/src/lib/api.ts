import { useSidecarStore } from "../stores/useSidecarStore";

export interface HealthResponse {
  status: string;
}

/** Base URL for REST calls to the FastAPI sidecar (dynamic port from Tauri). */
export function getSidecarBaseUrl(): string {
  const port = useSidecarStore.getState().port;
  if (port == null) {
    throw new Error("Sidecar port not initialized; call useSidecarStore.getState().init() first");
  }
  return `http://127.0.0.1:${port}`;
}

/** GET `/health` until success or attempts exhausted (sidecar may need a moment to bind). */
export async function getHealth(maxAttempts = 15, delayMs = 200): Promise<HealthResponse> {
  let lastError: unknown;
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    try {
      const response = await fetch(`${getSidecarBaseUrl()}/health`);
      if (!response.ok) {
        throw new Error(`Health check failed: ${response.status}`);
      }
      return (await response.json()) as HealthResponse;
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
  }
  throw lastError instanceof Error ? lastError : new Error(String(lastError));
}
