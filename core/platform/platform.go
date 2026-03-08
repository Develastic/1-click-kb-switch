package platform

import (
	"context"
	"fmt"

	"github.com/mykola/one-click-kb-switch/core/layouts"
)

var ErrNotImplemented = fmt.Errorf("platform capability is not implemented")

type TrayState struct {
	Label    string
	ShowMain func()
	ExitApp  func()
}

type EventHandler interface {
	OnShowMainWindow()
	OnExitRequested()
}

type Backend interface {
	ListLayouts(ctx context.Context) ([]layouts.Info, error)
	GetActiveLayout(ctx context.Context) (string, error)
	SwitchLayout(ctx context.Context, layoutID string) error
	StartEventLoop(ctx context.Context, handler EventHandler) error
	SetTrayState(ctx context.Context, state TrayState) error
	Shutdown(ctx context.Context) error
}
