package state

import (
	"context"
	"fmt"
	"log"
	"strings"

	"github.com/mykola/one-click-kb-switch/core/config"
	"github.com/mykola/one-click-kb-switch/core/hotkeys"
	"github.com/mykola/one-click-kb-switch/core/layouts"
	"github.com/mykola/one-click-kb-switch/core/platform"
	"github.com/mykola/one-click-kb-switch/core/sound"
)

type Model struct {
	ConfigPath     string
	Config         config.Config
	Layouts        []layouts.Info
	Warnings       []string
	TrayLabel      string
	ShowMainWindow bool
}

type Service struct {
	backend platform.Backend
	player  sound.Player
	logger  *log.Logger
}

func NewService(backend platform.Backend, player sound.Player, logger *log.Logger) *Service {
	return &Service{backend: backend, player: player, logger: logger}
}

func (s *Service) Bootstrap(ctx context.Context, configPath string) (Model, error) {
	cfg, firstRun, err := s.loadOrCreateConfig(configPath)
	if err != nil {
		return Model{}, err
	}
	items, err := s.backend.ListLayouts(ctx)
	if err != nil {
		s.logger.Printf("не удалось обнаружить раскладки: %v", err)
	}
	cfg = mergeLayoutsAndBindings(cfg, items)
	label := layouts.DefaultLabel
	if len(cfg.Layouts) > 0 {
		label = layouts.EffectiveLabel(cfg.Layouts[0])
	}
	return Model{
		ConfigPath:     configPath,
		Config:         cfg,
		Layouts:        cfg.Layouts,
		Warnings:       collectWarnings(cfg),
		TrayLabel:      label,
		ShowMainWindow: firstRun || !cfg.StartMinimizedAfterFirstRun,
	}, nil
}

func (s *Service) Persist(ctx context.Context, model Model) error {
	if err := model.Config.Save(model.ConfigPath); err != nil {
		return err
	}
	return s.backend.SetTrayState(ctx, platform.TrayState{Label: model.TrayLabel})
}

func (s *Service) SwitchLayout(ctx context.Context, model *Model, layoutID string) error {
	if err := s.backend.SwitchLayout(ctx, layoutID); err != nil {
		return err
	}
	for _, item := range model.Config.Layouts {
		if item.ID == layoutID {
			model.TrayLabel = layouts.EffectiveLabel(item)
			break
		}
	}
	if model.Config.PlaySwitchSound {
		if err := s.player.PlaySwitch(ctx); err != nil {
			s.logger.Printf("не удалось проиграть звук переключения: %v", err)
		}
	}
	return nil
}

func (s *Service) loadOrCreateConfig(path string) (config.Config, bool, error) {
	cfg, err := config.Load(path)
	if err == nil {
		return cfg, false, nil
	}
	if !strings.Contains(err.Error(), "cannot read config") {
		return config.Config{}, false, err
	}
	created, createErr := config.CreateFromDefaults(path)
	if createErr != nil {
		return config.Config{}, false, createErr
	}
	return created, true, nil
}

func mergeLayoutsAndBindings(cfg config.Config, detected []layouts.Info) config.Config {
	if len(detected) > 0 {
		cfg.Layouts = detected
	}
	if len(cfg.HotkeyBindings) == 0 {
		englishID, alternateID := layouts.ChooseDefaultPair(cfg.Layouts)
		cfg.HotkeyBindings, _ = hotkeys.DefaultBindings(englishID, alternateID)
	}
	cfg.HasCompletedFirstRun = true
	return cfg
}

func collectWarnings(cfg config.Config) []string {
	warnings := make([]string, 0, 2)
	englishID, alternateID := layouts.ChooseDefaultPair(cfg.Layouts)
	if englishID == "" {
		warnings = append(warnings, "English layout was not detected.")
	}
	if alternateID == "" {
		warnings = append(warnings, "Alternative non-English layout was not detected.")
	}
	if err := hotkeys.ValidateUnique(cfg.HotkeyBindings); err != nil {
		warnings = append(warnings, fmt.Sprintf("Hotkey conflict: %v", err))
	}
	return warnings
}
