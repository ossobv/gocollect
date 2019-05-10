// Package sanejoin implements Join() like filepath.Join(), except
// when later arguments are absolute, in which case it wipes the
// previous path components. (Behaves like python os.path.join().)
package sanejoin

import (
	"path/filepath"
)

// Join joins path elements, but will allow absolute paths to wipe
// previous arguments.
//
// input         | filepath     | sanejoin | different
// --------------+--------------+----------+-----------
// "a", "b"      | "a/b"        | "a/b"    |
// "a/b", "../c" | "a/c"        | "a/c"    |
// "a/b", "/c"   | "a/b/c"      | "/c"     | yes
// --------------+--------------+----------+-----------
func Join(elem ...string) string {
	absIdx := 0
	for idx, el := range elem {
		if filepath.IsAbs(el) {
			absIdx = idx
		}
	}
	return filepath.Join(elem[absIdx:]...)
}
