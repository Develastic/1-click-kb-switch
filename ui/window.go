package ui

import (
	"fmt"
	"strings"

	"github.com/mykola/one-click-kb-switch/core/layouts"
	"github.com/mykola/one-click-kb-switch/core/state"
)

func Run(model state.Model) error {
	fmt.Println("One Click KB Switch")
	fmt.Println("===================")
	fmt.Println("Settings summary")
	for _, item := range model.Layouts {
		fmt.Printf("- %s | auto=%s | effective=%s\n", item.DisplayName, item.AutoLabel, layouts.EffectiveLabel(item))
	}
	if len(model.Warnings) > 0 {
		fmt.Println("Warnings:")
		for _, warning := range model.Warnings {
			fmt.Printf("  * %s\n", warning)
		}
	}
	if len(model.Config.HotkeyBindings) > 0 {
		fmt.Println("Hotkeys:")
		for _, binding := range model.Config.HotkeyBindings {
			combo := string(binding.Key)
			if len(binding.Modifiers) > 0 {
				parts := make([]string, 0, len(binding.Modifiers)+1)
				for _, mod := range binding.Modifiers {
					parts = append(parts, string(mod))
				}
				parts = append(parts, string(binding.Key))
				combo = strings.Join(parts, "+")
			}
			fmt.Printf("  * %s -> %s (%s)\n", combo, binding.LayoutID, binding.Type)
		}
	}
	return nil
}
