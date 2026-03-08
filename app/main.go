package main

import (
	"context"
	"log"
	"os"

	platformfactory "github.com/mykola/one-click-kb-switch/platform"

	"github.com/mykola/one-click-kb-switch/core/config"
	"github.com/mykola/one-click-kb-switch/core/sound"
	"github.com/mykola/one-click-kb-switch/core/state"
	"github.com/mykola/one-click-kb-switch/ui"
)

func main() {
	logger := log.New(os.Stdout, "[kb-switch] ", log.LstdFlags)
	configPath, err := config.AppConfigPath()
	if err != nil {
		logger.Fatalf("не удалось определить путь конфига: %v", err)
	}
	service := state.NewService(platformfactory.NewBackend(), sound.NoopPlayer{}, logger)
	model, err := service.Bootstrap(context.Background(), configPath)
	if err != nil {
		logger.Fatalf("не удалось инициализировать приложение: %v", err)
	}
	if err := service.Persist(context.Background(), model); err != nil {
		logger.Fatalf("не удалось сохранить конфиг: %v", err)
	}
	if model.ShowMainWindow {
		if err := ui.Run(model); err != nil {
			logger.Fatalf("не удалось запустить окно: %v", err)
		}
		return
	}
	logger.Println("приложение запущено в свернутом режиме; tray backend еще не активирован")
}
