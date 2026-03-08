package hotkeys

import (
	"fmt"
	"sort"
	"strings"
)

type BindingType string

const (
	BindingTypeSingleClick BindingType = "single_click"
	BindingTypeCombo       BindingType = "combo"
)

type Key string

const (
	KeyRightCtrl  Key = "RightCtrl"
	KeyRightShift Key = "RightShift"
)

type Binding struct {
	LayoutID  string      `json:"layout_id"`
	Type      BindingType `json:"type"`
	Key       Key         `json:"key"`
	Modifiers []Key       `json:"modifiers,omitempty"`
	Display   string      `json:"display"`
	IsCustom  bool        `json:"is_custom"`
}

func (b Binding) Canonical() string {
	mods := append([]Key(nil), b.Modifiers...)
	sort.Slice(mods, func(i, j int) bool { return mods[i] < mods[j] })
	parts := make([]string, 0, len(mods)+2)
	for _, mod := range mods {
		parts = append(parts, string(mod))
	}
	parts = append(parts, string(b.Key), string(b.Type))
	return strings.Join(parts, "+")
}

func (b Binding) Validate() error {
	if strings.TrimSpace(b.LayoutID) == "" {
		return fmt.Errorf("layout_id is required")
	}
	if b.Type != BindingTypeSingleClick && b.Type != BindingTypeCombo {
		return fmt.Errorf("unsupported binding type: %s", b.Type)
	}
	if strings.TrimSpace(string(b.Key)) == "" {
		return fmt.Errorf("key is required")
	}
	if b.Type == BindingTypeSingleClick && len(b.Modifiers) > 0 {
		return fmt.Errorf("single_click binding cannot contain modifiers")
	}
	return nil
}

func DefaultBindings(englishID, alternateID string) ([]Binding, []string) {
	bindings := make([]Binding, 0, 2)
	warnings := make([]string, 0, 2)
	if englishID != "" {
		bindings = append(bindings, Binding{
			LayoutID: englishID,
			Type:     BindingTypeSingleClick,
			Key:      KeyRightCtrl,
			Display:  "RightCtrl (Single Click)",
		})
	} else {
		warnings = append(warnings, "english layout was not detected")
	}
	if alternateID != "" {
		bindings = append(bindings, Binding{
			LayoutID: alternateID,
			Type:     BindingTypeSingleClick,
			Key:      KeyRightShift,
			Display:  "RightShift (Single Click)",
		})
	} else {
		warnings = append(warnings, "alternate layout was not detected")
	}
	return bindings, warnings
}

func ValidateUnique(bindings []Binding) error {
	seen := map[string]string{}
	for _, binding := range bindings {
		if err := binding.Validate(); err != nil {
			return err
		}
		canonical := binding.Canonical()
		if existingLayout, ok := seen[canonical]; ok {
			return fmt.Errorf("binding conflict between layouts %s and %s", existingLayout, binding.LayoutID)
		}
		seen[canonical] = binding.LayoutID
	}
	return nil
}
