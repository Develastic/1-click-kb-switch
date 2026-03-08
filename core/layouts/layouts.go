package layouts

import (
	"strings"
	"unicode"
)

const DefaultLabel = "KB"

var englishExactNames = map[string]struct{}{
	"english":        {},
	"english us":     {},
	"english uk":     {},
	"us":             {},
	"usa":            {},
	"uk":             {},
	"gb":             {},
	"british":        {},
	"united states":  {},
	"united kingdom": {},
}

var englishWords = map[string]struct{}{
	"english": {},
	"us":      {},
	"usa":     {},
	"uk":      {},
	"gb":      {},
	"british": {},
}

type Info struct {
	ID            string `json:"id"`
	DisplayName   string `json:"display_name"`
	IsEnglish     bool   `json:"is_english"`
	AutoLabel     string `json:"auto_label"`
	LabelOverride string `json:"label_override,omitempty"`
}

func NormalizeDisplayName(value string) string {
	trimmed := strings.TrimSpace(value)
	if trimmed == "" {
		return "Unknown"
	}
	fields := strings.Fields(trimmed)
	return strings.Join(fields, " ")
}

func IsEnglishLayout(name string) bool {
	normalized := strings.ToLower(NormalizeDisplayName(name))
	if _, ok := englishExactNames[normalized]; ok {
		return true
	}
	for _, field := range strings.FieldsFunc(normalized, func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsNumber(r)
	}) {
		if _, ok := englishWords[field]; ok {
			return true
		}
	}
	return false
}

func GenerateAutoLabel(name string) string {
	if strings.TrimSpace(name) == "" {
		return DefaultLabel
	}
	normalized := NormalizeDisplayName(name)
	words := strings.Fields(normalized)
	letters := make([]rune, 0, 2)
	if len(words) >= 2 {
		for _, part := range words {
			for _, r := range part {
				if unicode.IsLetter(r) {
					letters = append(letters, unicode.ToUpper(r))
					break
				}
			}
			if len(letters) == 2 {
				return string(letters)
			}
		}
	}
	for _, r := range normalized {
		if unicode.IsLetter(r) {
			letters = append(letters, unicode.ToUpper(r))
			if len(letters) == 2 {
				return string(letters)
			}
		}
	}
	if len(letters) == 1 {
		return string([]rune{letters[0], letters[0]})
	}
	return DefaultLabel
}

func BuildInfo(id, displayName, override string) Info {
	normalized := NormalizeDisplayName(displayName)
	return Info{
		ID:            id,
		DisplayName:   normalized,
		IsEnglish:     IsEnglishLayout(normalized),
		AutoLabel:     GenerateAutoLabel(normalized),
		LabelOverride: strings.TrimSpace(override),
	}
}

func EffectiveLabel(info Info) string {
	if strings.TrimSpace(info.LabelOverride) != "" {
		return strings.ToUpper(strings.TrimSpace(info.LabelOverride))
	}
	if strings.TrimSpace(info.AutoLabel) != "" {
		return strings.ToUpper(strings.TrimSpace(info.AutoLabel))
	}
	return DefaultLabel
}

func ChooseDefaultPair(items []Info) (englishID, alternateID string) {
	for _, item := range items {
		if englishID == "" && item.IsEnglish {
			englishID = item.ID
		}
		if alternateID == "" && !item.IsEnglish {
			alternateID = item.ID
		}
	}
	return englishID, alternateID
}
