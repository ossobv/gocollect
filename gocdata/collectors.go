// Package gocdata (gocollect) holds the collected data to make it ready
// for submittal.
package gocdata

import (
	"sort"

	"github.com/ossobv/gocollect/goclog"
)

// CollectorRun is the function signature to use as the Run function in
// the Collector struct.
type CollectorRun func(key string, runargs string) Data

// Collector holds instructions how to call a collector.
type Collector struct {
	// Callable that should return Data.
	Run   CollectorRun
	// Optional arguments to callable.
	RunArgs      string
	// Whether this collector is enabled.
	IsEnabled bool
}

// Collectors holds a key/value map of strings/Collector where key is
// the collector name and value is the Collector info. For shell script
// collectors, the Callable is the shell exec function, and Data is the
// file name.
type Collectors map[string]Collector

// Global list of builtin collectors.
var BuiltinCollectors Collectors

// Run runs/executes the collector and returns the data.
func (c *Collectors) Run(key string) Data {
	if collector, exists := (*c)[key]; exists {
		if collector.IsEnabled {
			return collector.Run(key, collector.RunArgs)
		}
		goclog.Log.Printf("collector[%s]: is disabled", key)
	} else {
		goclog.Log.Printf("collector[%s]: does not exist", key)
	}
	return Empty()
}

// Runnable returns all keys that have a runnable/enabled collector.
func (c *Collectors) Runnable() (keys []string) {
	for key, collector := range *c {
		if collector.IsEnabled {
			keys = append(keys, key)
		}
	}
	sort.Strings(keys)
	return keys
}
