//go:build windows

package platformfactory

import (
	"github.com/mykola/one-click-kb-switch/core/platform"
	winbackend "github.com/mykola/one-click-kb-switch/platform/windows"
)

func NewBackend() platform.Backend {
	return winbackend.NewBackend()
}
