use serde::{Deserialize, Serialize};

pub const DEFAULT_LABEL: &str = "KB";

const ENGLISH_EXACT_NAMES: &[&str] = &[
    "english",
    "english us",
    "english uk",
    "us",
    "usa",
    "uk",
    "gb",
    "british",
    "united states",
    "united kingdom",
];

const ENGLISH_WORDS: &[&str] = &["english", "us", "usa", "uk", "gb", "british"];

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct LayoutInfo {
    pub id: String,
    pub display_name: String,
    pub is_english: bool,
    pub auto_label: String,
    #[serde(default)]
    pub label_override: String,
}

pub fn normalize_display_name(value: &str) -> String {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        return "Unknown".to_string();
    }
    trimmed.split_whitespace().collect::<Vec<_>>().join(" ")
}

pub fn is_english_layout(name: &str) -> bool {
    let normalized = normalize_display_name(name).to_lowercase();
    if ENGLISH_EXACT_NAMES.contains(&normalized.as_str()) {
        return true;
    }

    normalized
        .split(|ch: char| !ch.is_alphanumeric())
        .filter(|part| !part.is_empty())
        .any(|part| ENGLISH_WORDS.contains(&part))
}

pub fn generate_auto_label(name: &str) -> String {
    if name.trim().is_empty() {
        return DEFAULT_LABEL.to_string();
    }

    let normalized = normalize_display_name(name);
    let words: Vec<&str> = normalized.split_whitespace().collect();

    if words.len() >= 2 {
        let letters: String = words
            .iter()
            .filter_map(|word| word.chars().find(|ch| ch.is_alphabetic()))
            .take(2)
            .flat_map(|ch| ch.to_uppercase())
            .collect();
        if letters.chars().count() == 2 {
            return letters;
        }
    }

    let letters: String = normalized
        .chars()
        .filter(|ch| ch.is_alphabetic())
        .take(2)
        .flat_map(|ch| ch.to_uppercase())
        .collect();

    match letters.chars().count() {
        2 => letters,
        1 => letters
            .chars()
            .next()
            .map(|ch| format!("{ch}{ch}"))
            .unwrap_or_else(|| DEFAULT_LABEL.to_string()),
        _ => DEFAULT_LABEL.to_string(),
    }
}

pub fn build_info(id: &str, display_name: &str, label_override: &str) -> LayoutInfo {
    let normalized = normalize_display_name(display_name);
    LayoutInfo {
        id: id.trim().to_string(),
        display_name: normalized.clone(),
        is_english: is_english_layout(&normalized),
        auto_label: generate_auto_label(&normalized),
        label_override: label_override.trim().to_uppercase(),
    }
}

pub fn effective_label(info: &LayoutInfo) -> String {
    if !info.label_override.trim().is_empty() {
        return info.label_override.trim().to_uppercase();
    }
    if !info.auto_label.trim().is_empty() {
        return info.auto_label.trim().to_uppercase();
    }
    DEFAULT_LABEL.to_string()
}

pub fn choose_default_pair(items: &[LayoutInfo]) -> (Option<String>, Option<String>) {
    let english = items
        .iter()
        .find(|item| item.is_english)
        .map(|item| item.id.clone());
    let alternate = items
        .iter()
        .find(|item| !item.is_english)
        .map(|item| item.id.clone());
    (english, alternate)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detects_english_layouts() {
        assert!(is_english_layout("English US"));
        assert!(!is_english_layout("Русский"));
    }

    #[test]
    fn generates_labels() {
        assert_eq!(generate_auto_label("English US"), "EU");
        assert_eq!(generate_auto_label("Русский"), "РУ");
        assert_eq!(generate_auto_label(""), DEFAULT_LABEL);
    }

    #[test]
    fn chooses_default_pair() {
        let items = vec![
            build_info("ru", "Russian", ""),
            build_info("us", "English US", ""),
            build_info("fr", "French", ""),
        ];
        let (english, alternate) = choose_default_pair(&items);
        assert_eq!(english.as_deref(), Some("us"));
        assert_eq!(alternate.as_deref(), Some("ru"));
    }
}
