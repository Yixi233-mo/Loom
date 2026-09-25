//! 插件加载器 — 扫描 `plugins/` 目录，解析 manifest，返回插件列表。
//!
//! 约定：
//! - 每个插件一个子目录，内含 `plugin.json` 或 `plugin.yaml` 作为 manifest
//! - 空目录 / 无插件目录：返回空列表，不报错
//! - 格式错误的 manifest：跳过并记日志（`eprintln!`）
//!
//! 依赖约束：仅 `serde` / `serde_json`。YAML 用最小字段提取
//! （`serde_yaml` 不在允许列表），完整 YAML 语义由 Python 侧 `dsl.compiler` 负责。

use std::fs;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

/// 插件清单（manifest）核心字段。
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PluginInfo {
    pub name: String,
    pub version: String,
    /// manifest 所在路径（便于 UI 跳转）
    #[serde(skip)]
    pub manifest_path: PathBuf,
    /// 插件目录
    #[serde(skip)]
    pub plugin_dir: PathBuf,
    #[serde(default)]
    pub description: String,
}

/// 加载结果：合法插件 + 被跳过的 manifest 路径（含原因日志）。
#[derive(Debug, Default)]
pub struct LoadReport {
    pub plugins: Vec<PluginInfo>,
    pub skipped: Vec<(PathBuf, String)>,
}

/// 扫描 `root` 下的一级子目录，解析各自 manifest。
///
/// - `root` 不存在或为空 → 空列表
/// - 单个 manifest 非法 → 跳过并记录，不影响其它插件
pub fn load_plugins(root: impl AsRef<Path>) -> LoadReport {
    let root = root.as_ref();
    let mut report = LoadReport::default();

    let entries = match fs::read_dir(root) {
        Ok(e) => e,
        Err(e) => {
            // 目录不存在 / 不可读：返回空列表，不报错
            eprintln!("[plugin_loader] 无法读取目录 {:?}: {}", root, e);
            return report;
        }
    };

    let mut dirs: Vec<PathBuf> = entries
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.is_dir())
        .collect();
    dirs.sort();

    for dir in dirs {
        match load_one_plugin(&dir) {
            Ok(info) => report.plugins.push(info),
            Err(reason) => {
                eprintln!("[plugin_loader] 跳过插件 {:?}: {}", dir, reason);
                report.skipped.push((dir, reason));
            }
        }
    }

    report
}

/// 只返回插件列表（对应验收「返回插件列表」）。
pub fn list_plugins(root: impl AsRef<Path>) -> Vec<PluginInfo> {
    load_plugins(root).plugins
}

fn load_one_plugin(dir: &Path) -> Result<PluginInfo, String> {
    let json_path = dir.join("plugin.json");
    if json_path.is_file() {
        return parse_json_manifest(&json_path, dir);
    }

    let yaml_path = dir.join("plugin.yaml");
    if yaml_path.is_file() {
        return parse_yaml_manifest(&yaml_path, dir);
    }

    let yml_path = dir.join("plugin.yml");
    if yml_path.is_file() {
        return parse_yaml_manifest(&yml_path, dir);
    }

    Err("缺少 plugin.json / plugin.yaml manifest".into())
}

fn parse_json_manifest(path: &Path, dir: &Path) -> Result<PluginInfo, String> {
    let raw = fs::read_to_string(path).map_err(|e| format!("读取失败: {e}"))?;
    let mut info: PluginInfo =
        serde_json::from_str(&raw).map_err(|e| format!("JSON 解析失败: {e}"))?;
    if info.name.trim().is_empty() {
        return Err("manifest 缺少 name".into());
    }
    if info.version.trim().is_empty() {
        return Err("manifest 缺少 version".into());
    }
    info.manifest_path = path.to_path_buf();
    info.plugin_dir = dir.to_path_buf();
    Ok(info)
}

/// 最小 YAML 提取：仅取顶层 `name` / `version` / `description`。
/// 解析失败或缺字段 → Err（调用方跳过并记日志）。
fn parse_yaml_manifest(path: &Path, dir: &Path) -> Result<PluginInfo, String> {
    let raw = fs::read_to_string(path).map_err(|e| format!("读取失败: {e}"))?;
    let name = yaml_top_str(&raw, "name").ok_or("YAML 缺少 name")?;
    let version = yaml_top_str(&raw, "version").ok_or("YAML 缺少 version")?;
    if name.trim().is_empty() {
        return Err("YAML name 为空".into());
    }
    if version.trim().is_empty() {
        return Err("YAML version 为空".into());
    }
    // 基础合法性：拒绝明显非 YAML 映射的内容
    if raw.trim_start().starts_with('[') {
        return Err("YAML 根节点应为映射，实际为序列".into());
    }
    Ok(PluginInfo {
        name,
        version,
        manifest_path: path.to_path_buf(),
        plugin_dir: dir.to_path_buf(),
        description: yaml_top_str(&raw, "description").unwrap_or_default(),
    })
}

/// 从 YAML 文本提取顶层标量字段（`key: value`），跳过注释与嵌套。
fn yaml_top_str(raw: &str, key: &str) -> Option<String> {
    let prefix = format!("{key}:");
    for line in raw.lines() {
        let t = line.trim();
        if t.is_empty() || t.starts_with('#') {
            continue;
        }
        // 顶层 key 才匹配（无前导空格）
        if !line.starts_with(|c: char| c.is_ascii_alphanumeric() || c == '_') {
            continue;
        }
        if let Some(rest) = t.strip_prefix(&prefix) {
            let v = rest.trim().trim_matches('"').trim_matches('\'');
            return Some(v.to_string());
        }
        // `name: "foo"` / `name: 'foo'`
        if t.starts_with(&prefix) {
            let v = t[prefix.len()..]
                .trim()
                .trim_matches('"')
                .trim_matches('\'');
            return Some(v.to_string());
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs::{self, File};
    use std::io::Write;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn temp_root(label: &str) -> PathBuf {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let dir = std::env::temp_dir().join(format!("loom_plugin_loader_{label}_{nanos}"));
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn empty_dir_returns_empty_list() {
        // 验收：空目录不报错，返回空列表
        let root = temp_root("empty");
        let report = load_plugins(&root);
        assert!(report.plugins.is_empty());
        assert!(report.skipped.is_empty());
        assert!(list_plugins(&root).is_empty());
        fs::remove_dir_all(&root).ok();
    }

    #[test]
    fn missing_dir_returns_empty_list() {
        let report = load_plugins("/definitely/not/existing/loom_plugins");
        assert!(report.plugins.is_empty());
    }

    #[test]
    fn valid_json_manifest() {
        let root = temp_root("json_ok");
        let pdir = root.join("notes");
        fs::create_dir_all(&pdir).unwrap();
        let mut f = File::create(pdir.join("plugin.json")).unwrap();
        writeln!(
            f,
            r#"{{"name": "notes", "version": "1.0.0", "description": "笔记插件"}}"#
        )
        .unwrap();

        let plugins = list_plugins(&root);
        assert_eq!(plugins.len(), 1);
        assert_eq!(plugins[0].name, "notes");
        assert_eq!(plugins[0].version, "1.0.0");
        assert_eq!(plugins[0].description, "笔记插件");
        fs::remove_dir_all(&root).ok();
    }

    #[test]
    fn valid_yaml_manifest() {
        let root = temp_root("yaml_ok");
        let pdir = root.join("notes");
        fs::create_dir_all(&pdir).unwrap();
        fs::write(
            pdir.join("plugin.yaml"),
            "name: notes\nversion: 1.0.0\ndescription: 笔记\nui:\n  type: list\n",
        )
        .unwrap();

        let plugins = list_plugins(&root);
        assert_eq!(plugins.len(), 1);
        assert_eq!(plugins[0].name, "notes");
        assert_eq!(plugins[0].version, "1.0.0");
        fs::remove_dir_all(&root).ok();
    }

    #[test]
    fn bad_manifest_skipped_and_logged() {
        // 验收：格式错误的 manifest 跳过并记日志
        let root = temp_root("bad");
        let bad = root.join("broken");
        fs::create_dir_all(&bad).unwrap();
        fs::write(bad.join("plugin.json"), "{not valid json").unwrap();

        let good = root.join("good");
        fs::create_dir_all(&good).unwrap();
        fs::write(
            good.join("plugin.json"),
            r#"{"name":"g","version":"0.1.0"}"#,
        )
        .unwrap();

        let report = load_plugins(&root);
        assert_eq!(report.plugins.len(), 1);
        assert_eq!(report.plugins[0].name, "g");
        assert_eq!(report.skipped.len(), 1);
        assert!(report.skipped[0].1.contains("JSON 解析失败"));
        fs::remove_dir_all(&root).ok();
    }

    #[test]
    fn yaml_missing_name_skipped() {
        let root = temp_root("yaml_bad");
        let pdir = root.join("x");
        fs::create_dir_all(&pdir).unwrap();
        fs::write(pdir.join("plugin.yaml"), "version: 1.0.0\n").unwrap();

        let report = load_plugins(&root);
        assert!(report.plugins.is_empty());
        assert_eq!(report.skipped.len(), 1);
        assert!(report.skipped[0].1.contains("name"));
        fs::remove_dir_all(&root).ok();
    }

    #[test]
    fn no_manifest_skipped() {
        let root = temp_root("no_manifest");
        let pdir = root.join("empty_plugin");
        fs::create_dir_all(&pdir).unwrap();

        let report = load_plugins(&root);
        assert!(report.plugins.is_empty());
        assert_eq!(report.skipped.len(), 1);
        assert!(report.skipped[0].1.contains("manifest"));
        fs::remove_dir_all(&root).ok();
    }

    #[test]
    fn multiple_plugins_sorted() {
        let root = temp_root("multi");
        for (name, ver) in [("b_plugin", "2.0.0"), ("a_plugin", "1.0.0")] {
            let pdir = root.join(name);
            fs::create_dir_all(&pdir).unwrap();
            fs::write(
                pdir.join("plugin.json"),
                format!(r#"{{"name":"{name}","version":"{ver}"}}"#),
            )
            .unwrap();
        }
        let plugins = list_plugins(&root);
        assert_eq!(plugins.len(), 2);
        assert_eq!(plugins[0].name, "a_plugin");
        assert_eq!(plugins[1].name, "b_plugin");
        fs::remove_dir_all(&root).ok();
    }
}
