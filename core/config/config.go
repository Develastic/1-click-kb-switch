package config

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	appassets "github.com/mykola/one-click-kb-switch/app/assets"
	"github.com/mykola/one-click-kb-switch/core/hotkeys"
	"github.com/mykola/one-click-kb-switch/core/layouts"
)

type Config struct {
	PlaySwitchSound             bool              `json:"play_switch_sound"`
	StartMinimizedAfterFirstRun bool              `json:"start_minimized_after_first_run"`
	HasCompletedFirstRun        bool              `json:"has_completed_first_run"`
	Layouts                     []layouts.Info    `json:"layouts"`
	HotkeyBindings              []hotkeys.Binding `json:"hotkey_bindings"`
}

func AppConfigDir() (string, error) {
	base, err := os.UserConfigDir()
	if err != nil {
		return "", fmt.Errorf("cannot resolve user config dir: %w", err)
	}
	return filepath.Join(base, "one-click-kb-switch"), nil
}

func AppConfigPath() (string, error) {
	dir, err := AppConfigDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(dir, "config.json"), nil
}

func Defaults() (Config, error) {
	var cfg Config
	if err := json.Unmarshal(appassets.ConfigDefaults, &cfg); err != nil {
		return Config{}, fmt.Errorf("cannot parse embedded default config: %w", err)
	}
	return cfg, nil
}

func Load(path string) (Config, error) {
	content, err := os.ReadFile(path)
	if err != nil {
		return Config{}, fmt.Errorf("cannot read config: %w", err)
	}
	var cfg Config
	if err := json.Unmarshal(content, &cfg); err != nil {
		return Config{}, fmt.Errorf("cannot parse config: %w", err)
	}
	if err := cfg.Validate(); err != nil {
		return Config{}, err
	}
	return cfg, nil
}

func (c Config) Validate() error {
	if err := hotkeys.ValidateUnique(c.HotkeyBindings); err != nil {
		return err
	}
	for _, item := range c.Layouts {
		if strings.TrimSpace(item.ID) == "" {
			return fmt.Errorf("layout id is required")
		}
	}
	return nil
}

func (c Config) Save(path string) error {
	if err := c.Validate(); err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return fmt.Errorf("cannot create config dir: %w", err)
	}
	payload, err := json.MarshalIndent(c, "", "  ")
	if err != nil {
		return fmt.Errorf("cannot encode config: %w", err)
	}
	if err := os.WriteFile(path, payload, 0o644); err != nil {
		return fmt.Errorf("cannot write config: %w", err)
	}
	return nil
}

func CreateFromDefaults(path string) (Config, error) {
	cfg, err := Defaults()
	if err != nil {
		return Config{}, err
	}
	if err := cfg.Save(path); err != nil {
		return Config{}, err
	}
	return cfg, nil
}
