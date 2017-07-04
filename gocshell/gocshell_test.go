// Package gocshell (gocollect) makes shell-script plugins available for
// collection.
package gocshell

import (
	"fmt"
)

func ExampleFindShellCollectors() {
	collectors := FindShellCollectors([]string{"../collectors"})

	// collectors.Runnable() has all keys of runnable collectors.
	runnableCount := len(collectors.Runnable())
	if runnableCount < 5 {
		fmt.Print("strange, very few runners?")
	}

	// We can run a single collector using those keys. For instance the
	// core.id key.
	data := collectors.Run("core.id")
	ip4 := data.GetString("ip4")
	if ip4 == "" {
		fmt.Print("ip4 empty?")
	}

	fmt.Print("runnables found")
	// Output: runnables found
}
