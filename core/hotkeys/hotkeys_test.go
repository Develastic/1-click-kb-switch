package hotkeys

import "testing"

func TestDefaultBindings(t *testing.T) {
	bindings, warnings := DefaultBindings("us", "ru")
	if len(warnings) != 0 {
		t.Fatalf("unexpected warnings: %v", warnings)
	}
	if len(bindings) != 2 {
		t.Fatalf("expected 2 bindings, got %d", len(bindings))
	}
	if bindings[0].Key != KeyRightCtrl || bindings[1].Key != KeyRightShift {
		t.Fatalf("unexpected default keys: %#v", bindings)
	}
}

func TestValidateUnique(t *testing.T) {
	bindings := []Binding{
		{LayoutID: "us", Type: BindingTypeSingleClick, Key: KeyRightCtrl},
		{LayoutID: "ru", Type: BindingTypeSingleClick, Key: KeyRightCtrl},
	}
	if err := ValidateUnique(bindings); err == nil {
		t.Fatal("expected conflict")
	}
}
