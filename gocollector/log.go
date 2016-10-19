// Package gocollector is the core of the GoCollect daemon. It collects
// data through supplied scripts, writes data to a central server.
package gocollector

import (
	"log"
)

var logger *log.Logger

// SetLog sets/updates the logger used by the gocollector package.
func SetLog(suggestedLogger *log.Logger) {
	logger = suggestedLogger
}
