package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestCreateFromDefaults(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "config.json")
	cfg, err := CreateFromDefaults(path)
	if err != nil {
		t.Fatalf("CreateFromDefaults returned error: %v", err)
	}
	if !cfg.PlaySwitchSound {
		t.Fatal("expected play_switch_sound to be true from defaults")
	}
	if _, err := os.Stat(path); err != nil {
		t.Fatalf("expected config file to exist: %v", err)
	}
}

func TestLoadRejectsConflictingBindings(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "config.json")
	payload := `{
  "play_switch_sound": true,
  "start_minimized_after_first_run": true,
  "has_completed_first_run": true,
  "layouts": [{"id":"us","display_name":"English US","is_english":true,"auto_label":"EU"}],
  "hotkey_bindings": [
    {"layout_id":"us","type":"single_click","key":"RightCtrl","display":"RightCtrl"},
    {"layout_id":"ru","type":"single_click","key":"RightCtrl","display":"RightCtrl"}
  ]
}`
	if err := os.WriteFile(path, []byte(payload), 0o644); err != nil {
		t.Fatalf("cannot write config fixture: %v", err)
	}
	if _, err := Load(path); err == nil {
		t.Fatal("expected config validation error")
	}
}
