// sanejoin package implements Join() like filepath.Join() but behaves
// like python os.path.join() which allows absolute paths to wipe
// previous arguments.
package sanejoin

import (
	"path/filepath"
)

// Join joins path elements, but will allow absolute paths to wipe
// previous arguments.
//
// input         | filepath     | sanepath
// --------------+--------------+---------
// "a", "b"      | "a/b"        | "a/b"
// "a/b", "../c" | "a/c"        | "a/c"
// "a/b", "/c"   | "a/b/c"      | "/c"
func Join(elem ...string) string {
	absIdx := 0
	for idx, el := range elem {
		if filepath.IsAbs(el) {
			absIdx = idx
		}
	}
	return filepath.Join(elem[absIdx:]...)
}
