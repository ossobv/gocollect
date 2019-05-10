// Package shcollectors (gocollect) makes shell-script plugins available
// for collection.
package shcollectors

import (
	"fmt"
)

func ExampleFind() {
	collectors := Find([]string{"../collectors"})

	// collectors.Runnable() has all keys of runnable collectors.
	runnableCount := len(collectors.Runnable())
	if runnableCount < 5 {
		fmt.Println("strange, very few runners?")
	}

	// We can run a single collector using those keys. For instance the
	// core.id key.
	data := collectors.Run("core.id")
	ip4 := data.GetString("ip4")
	if ip4 == "" {
		fmt.Println("ip4 empty?")
	}

	fmt.Println("runnables found")
	// Output: runnables found
}
