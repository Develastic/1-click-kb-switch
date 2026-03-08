package hotkeys

import "testing"

func TestSingleClickDetector(t *testing.T) {
	detector := NewSingleClickDetector(KeyRightCtrl)
	if detector.Feed(Event{Kind: EventKeyDown, Key: KeyRightCtrl}) {
		t.Fatal("should not trigger on key down")
	}
	if !detector.Feed(Event{Kind: EventKeyUp, Key: KeyRightCtrl}) {
		t.Fatal("expected single click trigger")
	}
}

func TestSingleClickDetectorIgnoresCombinations(t *testing.T) {
	detector := NewSingleClickDetector(KeyRightCtrl)
	detector.Feed(Event{Kind: EventKeyDown, Key: KeyRightCtrl})
	detector.Feed(Event{Kind: EventKeyDown, Key: KeyRightShift})
	if detector.Feed(Event{Kind: EventKeyUp, Key: KeyRightCtrl}) {
		t.Fatal("single click should not trigger when another key was pressed")
	}
}

func TestSingleClickDetectorIgnoresMouseClick(t *testing.T) {
	detector := NewSingleClickDetector(KeyRightShift)
	detector.Feed(Event{Kind: EventKeyDown, Key: KeyRightShift})
	detector.Feed(Event{Kind: EventMouseClick})
	if detector.Feed(Event{Kind: EventKeyUp, Key: KeyRightShift}) {
		t.Fatal("single click should not trigger when mouse was clicked")
	}
}
