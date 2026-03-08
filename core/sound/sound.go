package sound

import "context"

type Player interface {
	PlaySwitch(ctx context.Context) error
}

type NoopPlayer struct{}

func (NoopPlayer) PlaySwitch(context.Context) error { return nil }
