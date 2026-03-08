//go:build linux

package linuxx11

import "testing"

func TestParseQuery(t *testing.T) {
	query := []byte("rules: evdev\nmodel: pc105\nlayout: us,ru,fr\n")
	items := parseQuery(query)
	if len(items) != 3 {
		t.Fatalf("expected 3 layouts, got %d", len(items))
	}
	if items[0].ID != "us" || items[1].ID != "ru" || items[2].ID != "fr" {
		t.Fatalf("unexpected layout ids: %#v", items)
	}
}
