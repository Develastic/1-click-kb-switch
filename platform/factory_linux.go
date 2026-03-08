//go:build linux

package platformfactory

import (
	"github.com/mykola/one-click-kb-switch/core/platform"
	"github.com/mykola/one-click-kb-switch/platform/linuxx11"
)

func NewBackend() platform.Backend {
	return linuxx11.NewBackend()
}
