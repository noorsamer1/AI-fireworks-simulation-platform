mod sidecar;
mod commands;

use commands::get_sidecar_port;
use sidecar::start_sidecar;
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            let runtime = start_sidecar()?;
            app.manage(runtime);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_sidecar_port])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
