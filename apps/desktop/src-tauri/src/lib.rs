//! Loom — Tauri 2.0 库 + 核心模块。
//!
//! 命令名对齐 `src/platform/tauri-bridge.ts`：
//!   list_plugins / read_text_file / write_text_file

pub mod commands;
pub mod plugin_loader;

pub fn greet() -> &'static str {
    "Loom"
}

/// 移动端（Android/iOS）入口 — Tauri 生成 JNI（`app.loom.shell.Rust`）。
/// 缺少本函数会导致 `UnsatisfiedLinkError` → 真机闪退。
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            commands::list_plugins,
            commands::read_text_file,
            commands::write_text_file,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Loom");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn greet_works() {
        assert_eq!(greet(), "Loom");
    }
}
