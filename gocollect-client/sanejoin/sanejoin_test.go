package sanejoin

import (
	"fmt"
	"path/filepath"
	"testing"
)

func ExampleJoin() {
	fmt.Println("On Unix:")
	fmt.Println(Join("a", "b", "c"))
	// expected: a/b/c
}

func TestJoin(t *testing.T) {
	type inout struct {
		in          []string
		out         string
		filepathOut string
	}
	list := []inout{
		{[]string{""}, "", ""},
		{[]string{"", "a"}, "a", "a"},
		{[]string{"a"}, "a", "a"},
		{[]string{"/a"}, "/a", "/a"},
		{[]string{"a", "b"}, "a/b", "a/b"},
		{[]string{"a/", "b"}, "a/b", "a/b"},
		{[]string{"/a", "b"}, "/a/b", "/a/b"},
		{[]string{"/a", "/b"}, "/b", "/a/b"}, // diff
		{[]string{"/a/b", "./c"}, "/a/b/c", "/a/b/c"},
		{[]string{"/a/b", "../c"}, "/a/c", "/a/c"},
	}
	for i := 0; i < len(list); i++ {
		input := list[i].in
		expected := list[i].out

		// Check our Join
		actual := Join(input...)
		if actual != expected {
			t.Errorf("#%d: sanejoin.Join(%q) returned %q, expected %q",
				i, input, actual, expected)
		}

		// Check filepath.Join
		expected = list[i].filepathOut
		actual = filepath.Join(input...)
		if actual != expected {
			t.Errorf("#%d: filepath.Join(%q) returned %q, expected %q",
				i, input, actual, expected)
		}
	}
}
