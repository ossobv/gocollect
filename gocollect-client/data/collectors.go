// Package data (gocollect) holds the collected data to make it ready
// for submittal.
package data

import (
	"sort"
	"strings"

	"github.com/ossobv/gocollect/gocollect-client/log"
)

// CollectorRun is the function signature to use as the Run function in
// the Collector struct.
type CollectorRun func(key string, runargs string) Collected

// Collector holds instructions how to call a collector.
type Collector struct {
	// Callable that should return Collected.
	Run CollectorRun
	// Optional arguments to callable.
	RunArgs string
	// Whether this collector is enabled.
	IsEnabled bool
}

// Collectors holds a key/value map of strings/Collector where key is
// the collector name and value is the Collector info. For shell script
// collectors, the Callable is the shell exec function, and RunArgs is
// the file name.
type Collectors map[string]Collector

// BuiltinCollectors holds a list of builtin collectors.
var BuiltinCollectors = Collectors{}

// MergeCollectors merges two lists of collectors and returns a new
// list. The latter list takes precedence.
func MergeCollectors(c1 *Collectors, c2 *Collectors) *Collectors {
	n := Collectors{}
	// Shallow copy of c2.
	for key, collector := range *c2 {
		n[key] = collector
	}
	// Copy all from c1, but only if c2 didn't set it yet.
	for key, collector := range *c1 {
		if _, exists := n[key]; !exists {
			n[key] = collector
		}
	}
	return &n
}

// Run runs/executes the collector and returns the data.
func (c *Collectors) Run(key string) Collected {
	if collector, exists := (*c)[key]; exists {
		if collector.IsEnabled {
			return collector.Run(key, collector.RunArgs)
		}
		log.Log.Printf("collector[%s]: is disabled", key)
	} else {
		log.Log.Printf("collector[%s]: does not exist", key)
	}
	return EmptyCollected()
}

// GetRunnable returns all keys that have a runnable/enabled collector
// in a stable/sorted order. That is, sorted order, but core.id is first.
func (c *Collectors) GetRunnable() (keys []string) {
	for key, collector := range *c {
		if collector.IsEnabled {
			keys = append(keys, key)
		}
	}
	sort.Sort(byKeyName(keys))
	return keys
}

// Sorting functions below: sort core.* before sys.*, etc..
// This way we'll get "core.id" first. This should always be accepted.
// So if it isn't, we can abort the entire run.

var catOrder = []string{"core", "sys", "os"}

type byKeyName []string

func (s byKeyName) Len() int {
	return len(s)
}

func (s byKeyName) Swap(i, j int) {
	s[i], s[j] = s[j], s[i]
}

func (s byKeyName) Less(i, j int) bool {
	ipos := strings.IndexByte(s[i], '.')
	jpos := strings.IndexByte(s[j], '.')

	// Common case: they have a category "core." or "os."
	if ipos != -1 && jpos != -1 {
		icat := s[i][0:ipos]
		jcat := s[j][0:jpos]
		if icat == jcat {
			return s[i] < s[j]
		}
		var icatpos, jcatpos int
		for icatpos = 0; icatpos < len(catOrder); icatpos++ {
			if icat == catOrder[icatpos] {
				break
			}
		}
		for jcatpos = 0; jcatpos < len(catOrder); jcatpos++ {
			if jcat == catOrder[jcatpos] {
				break
			}
		}
		if icatpos == jcatpos {
			return s[i] < s[j]
		}
		return icatpos < jcatpos
	}

	// Unexpected cases when one or both don't have a category
	if ipos == -1 && jpos == -1 {
		return s[i] < s[j]
	}
	if ipos == -1 {
		return false // lhs has no category; so it's later
	}
	return true // rhs has no category; so lhs is less
}
