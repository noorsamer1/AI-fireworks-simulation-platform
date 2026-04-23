//! Tauri IPC commands exposed to the frontend.

use tauri::State;

use crate::sidecar::SidecarRuntime;

/// Returns the TCP port the Python sidecar is listening on (dynamic allocation).
#[tauri::command]
pub fn get_sidecar_port(runtime: State<SidecarRuntime>) -> u16 {
    runtime.port
}
