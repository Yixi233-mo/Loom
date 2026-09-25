//! Loom — Tauri 2.0 应用入口。
//!
//! 加载前端 dist / dev server，并注册 IPC 命令。

// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            loom_shell::commands::list_plugins,
            loom_shell::commands::read_text_file,
            loom_shell::commands::write_text_file,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Loom");
}
