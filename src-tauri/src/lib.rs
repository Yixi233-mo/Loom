//! Loom Shell — Tauri 2.0 库 + 核心模块。
//!
//! 命令名对齐 `src/platform/tauri-bridge.ts`：
//!   list_plugins / read_text_file / write_text_file

pub mod commands;
pub mod plugin_loader;

pub fn greet() -> &'static str {
    "Loom Shell"
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn greet_works() {
        assert_eq!(greet(), "Loom Shell");
    }
}
