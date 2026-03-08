//go:build linux

package linuxx11

import (
	"bufio"
	"context"
	"fmt"
	"os/exec"
	"strings"

	"github.com/mykola/one-click-kb-switch/core/layouts"
	"github.com/mykola/one-click-kb-switch/core/platform"
)

type Backend struct{}

func NewBackend() *Backend { return &Backend{} }

func (b *Backend) ListLayouts(ctx context.Context) ([]layouts.Info, error) {
	if _, err := exec.LookPath("setxkbmap"); err != nil {
		return nil, fmt.Errorf("setxkbmap is required on Linux X11")
	}
	cmd := exec.CommandContext(ctx, "setxkbmap", "-query")
	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("cannot query X11 layouts: %w", err)
	}
	return parseQuery(output), nil
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

func parseQuery(raw []byte) []layouts.Info {
	scanner := bufio.NewScanner(strings.NewReader(string(raw)))
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if !strings.HasPrefix(line, "layout:") {
			continue
		}
		payload := strings.TrimSpace(strings.TrimPrefix(line, "layout:"))
		parts := strings.Split(payload, ",")
		items := make([]layouts.Info, 0, len(parts))
		for _, part := range parts {
			name := strings.TrimSpace(part)
			if name == "" {
				continue
			}
			items = append(items, layouts.BuildInfo(name, name, ""))
		}
		return items
	}
	return nil
}
