// Package log (gocollect) holds the GoCollect daemon logger.
package log

import (
	golog "log"
)

// Log references a valid logger here. The application should set this ASAP.
var Log *golog.Logger
