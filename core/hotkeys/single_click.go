package hotkeys

type EventKind string

const (
	EventKeyDown    EventKind = "key_down"
	EventKeyUp      EventKind = "key_up"
	EventMouseClick EventKind = "mouse_click"
)

type Event struct {
	Kind EventKind
	Key  Key
}

type SingleClickDetector struct {
	target        Key
	pressed       bool
	otherActivity bool
}

func NewSingleClickDetector(target Key) *SingleClickDetector {
	return &SingleClickDetector{target: target}
}

func (d *SingleClickDetector) Feed(event Event) bool {
	switch event.Kind {
	case EventKeyDown:
		if event.Key == d.target && !d.pressed {
			d.pressed = true
			d.otherActivity = false
			return false
		}
		if d.pressed {
			d.otherActivity = true
		}
	case EventKeyUp:
		if event.Key == d.target && d.pressed {
			trigger := !d.otherActivity
			d.pressed = false
			d.otherActivity = false
			return trigger
		}
		if d.pressed {
			d.otherActivity = true
		}
	case EventMouseClick:
		if d.pressed {
			d.otherActivity = true
		}
	}
	return false
}
