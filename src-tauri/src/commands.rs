//! Tauri 命令层 — 对齐前端 TauriBridge。
//!
//! list_plugins / read_text_file / write_text_file

use std::path::Path;

use crate::plugin_loader::{list_plugins as scan_plugins, PluginInfo};

/// 扫描插件目录，返回插件列表。
pub fn cmd_list_plugins(root: &str) -> Vec<PluginInfo> {
    scan_plugins(root)
}

/// 读 UTF-8 文本文件。
pub fn cmd_read_text_file(path: &str) -> Result<String, String> {
    std::fs::read_to_string(Path::new(path)).map_err(|e| format!("read failed: {e}"))
}

/// 写 UTF-8 文本文件。
pub fn cmd_write_text_file(path: &str, content: &str) -> Result<bool, String> {
    std::fs::write(Path::new(path), content)
        .map(|_| true)
        .map_err(|e| format!("write failed: {e}"))
}

// ---------------------------------------------------------------------------
// tauri::command 包装（暴露给 WebView）
// ---------------------------------------------------------------------------

#[tauri::command]
pub fn list_plugins(root: String) -> Vec<PluginInfo> {
    cmd_list_plugins(&root)
}

#[tauri::command]
pub fn read_text_file(path: String) -> Result<String, String> {
    cmd_read_text_file(&path)
}

#[tauri::command]
pub fn write_text_file(path: String, content: String) -> Result<bool, String> {
    cmd_write_text_file(&path, &content)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    #[test]
    fn read_write_roundtrip() {
        let dir = std::env::temp_dir().join("loom_tauri_cmd_test");
        fs::create_dir_all(&dir).unwrap();
        let p = dir.join("a.txt");
        assert!(cmd_write_text_file(p.to_str().unwrap(), "hello").unwrap());
        assert_eq!(cmd_read_text_file(p.to_str().unwrap()).unwrap(), "hello");
        fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn list_plugins_empty_ok() {
        let v = cmd_list_plugins("/definitely/not/existing/plugins");
        assert!(v.is_empty());
    }
}
