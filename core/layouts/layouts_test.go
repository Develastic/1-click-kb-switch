package layouts

import "testing"

func TestIsEnglishLayout(t *testing.T) {
	if !IsEnglishLayout("English US") {
		t.Fatal("expected English US to be recognized as english")
	}
	if IsEnglishLayout("Русский") {
		t.Fatal("expected Russian layout not to be recognized as english")
	}
}

func TestGenerateAutoLabel(t *testing.T) {
	cases := map[string]string{
		"English US": "EU",
		"Русский":    "РУ",
		"":           DefaultLabel,
	}
	for input, want := range cases {
		if got := GenerateAutoLabel(input); got != want {
			t.Fatalf("GenerateAutoLabel(%q) = %q, want %q", input, got, want)
		}
	}
}

func TestChooseDefaultPair(t *testing.T) {
	items := []Info{
		BuildInfo("ru", "Russian", ""),
		BuildInfo("us", "English US", ""),
		BuildInfo("fr", "French", ""),
	}
	englishID, alternateID := ChooseDefaultPair(items)
	if englishID != "us" || alternateID != "ru" {
		t.Fatalf("unexpected pair %q %q", englishID, alternateID)
	}
}
