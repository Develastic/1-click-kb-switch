package state

import (
	"context"
	"errors"
	"io"
	"log"
	"testing"

	"github.com/mykola/one-click-kb-switch/core/config"
	"github.com/mykola/one-click-kb-switch/core/layouts"
	"github.com/mykola/one-click-kb-switch/core/platform"
)

type fakeBackend struct {
	layouts   []layouts.Info
	switched  string
	switchErr error
}

func (f *fakeBackend) ListLayouts(context.Context) ([]layouts.Info, error) { return f.layouts, nil }
func (f *fakeBackend) GetActiveLayout(context.Context) (string, error)     { return "", nil }
func (f *fakeBackend) SwitchLayout(_ context.Context, layoutID string) error {
	if f.switchErr != nil {
		return f.switchErr
	}
	f.switched = layoutID
	return nil
}
func (f *fakeBackend) StartEventLoop(context.Context, platform.EventHandler) error { return nil }
func (f *fakeBackend) SetTrayState(context.Context, platform.TrayState) error      { return nil }
func (f *fakeBackend) Shutdown(context.Context) error                              { return nil }

type fakePlayer struct{ called bool }

func (f *fakePlayer) PlaySwitch(context.Context) error { f.called = true; return nil }

func TestBootstrapFirstRunCreatesConfigAndWindow(t *testing.T) {
	backend := &fakeBackend{layouts: []layouts.Info{
		layouts.BuildInfo("us", "English US", ""),
		layouts.BuildInfo("ru", "Russian", ""),
	}}
	player := &fakePlayer{}
	logger := log.New(io.Discard, "", 0)
	service := NewService(backend, player, logger)
	path := t.TempDir() + "/config.json"
	model, err := service.Bootstrap(context.Background(), path)
	if err != nil {
		t.Fatalf("Bootstrap returned error: %v", err)
	}
	if !model.ShowMainWindow {
		t.Fatal("expected first run to show main window")
	}
	if len(model.Config.HotkeyBindings) != 2 {
		t.Fatalf("expected default bindings to be generated, got %d", len(model.Config.HotkeyBindings))
	}
}

func TestBootstrapRepeatedRunStartsMinimized(t *testing.T) {
	backend := &fakeBackend{layouts: []layouts.Info{layouts.BuildInfo("us", "English US", "")}}
	logger := log.New(io.Discard, "", 0)
	service := NewService(backend, &fakePlayer{}, logger)
	path := t.TempDir() + "/config.json"
	cfg := config.Config{PlaySwitchSound: true, StartMinimizedAfterFirstRun: true, HasCompletedFirstRun: true}
	if err := cfg.Save(path); err != nil {
		t.Fatalf("cannot save config: %v", err)
	}
	model, err := service.Bootstrap(context.Background(), path)
	if err != nil {
		t.Fatalf("Bootstrap returned error: %v", err)
	}
	if model.ShowMainWindow {
		t.Fatal("expected repeated run to start minimized")
	}
}

func TestSwitchLayoutUpdatesLabelAndPlaysSound(t *testing.T) {
	backend := &fakeBackend{}
	player := &fakePlayer{}
	service := NewService(backend, player, log.New(io.Discard, "", 0))
	model := &Model{Config: config.Config{PlaySwitchSound: true, Layouts: []layouts.Info{{ID: "ru", DisplayName: "Russian", AutoLabel: "RU"}}}}
	if err := service.SwitchLayout(context.Background(), model, "ru"); err != nil {
		t.Fatalf("SwitchLayout returned error: %v", err)
	}
	if model.TrayLabel != "RU" {
		t.Fatalf("expected tray label RU, got %q", model.TrayLabel)
	}
	if !player.called {
		t.Fatal("expected sound player to be called")
	}
}

func TestSwitchLayoutDoesNotPlaySoundOnError(t *testing.T) {
	backend := &fakeBackend{switchErr: errors.New("boom")}
	player := &fakePlayer{}
	service := NewService(backend, player, log.New(io.Discard, "", 0))
	model := &Model{Config: config.Config{PlaySwitchSound: true}}
	if err := service.SwitchLayout(context.Background(), model, "ru"); err == nil {
		t.Fatal("expected switch error")
	}
	if player.called {
		t.Fatal("sound should not play on switch error")
	}
}
