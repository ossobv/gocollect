// GoCollect daemon, collects data through supplied scripts, writes data
// to a central server.
package main

import (
	"fmt"
	"os"
	"testing"
)

func assertEqual(t *testing.T, a interface{}, b interface{}, message string) {
	if a != b {
		if len(message) == 0 {
			t.Fatal(fmt.Sprintf("%v != %v", a, b))
		} else {
			t.Fatal(message)
		}
	}
}

func TestParseArgsOrExit_NoOptions(t *testing.T) {
	args := parseArgsOrExit()
	assertEqual(t, args["one-shot"].Bool, false, "")
	assertEqual(t, args["config"].String, "/etc/gocollect.conf", "")
}

func TestParseArgsOrExit_ShortOpts(t *testing.T) {
	os.Args = []string{"prog", "-s", "-c", "/dev/null"}
	args := parseArgsOrExit()
	assertEqual(t, args["one-shot"].Bool, true, "")
	assertEqual(t, args["config"].String, "/dev/null", "")
}

func TestParseArgsOrExit_VeryShortOpts(t *testing.T) {
	// https://github.com/kesselborn/go-getopt/pull/1
	os.Args = []string{"prog", "-sc", "/foo/bar"}
	args := parseArgsOrExit()
	assertEqual(t, args["one-shot"].Bool, true, "")
	assertEqual(t, args["config"].String, "/foo/bar", "")
}
