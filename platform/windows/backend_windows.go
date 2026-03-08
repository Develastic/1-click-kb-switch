//go:build windows

package windows

import (
	"context"

	"github.com/mykola/one-click-kb-switch/core/layouts"
	"github.com/mykola/one-click-kb-switch/core/platform"
)

type Backend struct{}

func NewBackend() *Backend { return &Backend{} }

func (b *Backend) ListLayouts(context.Context) ([]layouts.Info, error) {
	return nil, platform.ErrNotImplemented
}
func (b *Backend) GetActiveLayout(context.Context) (string, error) {
	return "", platform.ErrNotImplemented
}
func (b *Backend) SwitchLayout(context.Context, string) error { return platform.ErrNotImplemented }
func (b *Backend) StartEventLoop(context.Context, platform.EventHandler) error {
	return platform.ErrNotImplemented
}
func (b *Backend) SetTrayState(context.Context, platform.TrayState) error { return nil }
func (b *Backend) Shutdown(context.Context) error                         { return nil }
