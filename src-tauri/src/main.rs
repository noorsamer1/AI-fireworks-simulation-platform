// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    // IPC commands (e.g. `get_sidecar_port`) are registered on the builder in `lib.rs`.
    pyromind_app_lib::run()
}
