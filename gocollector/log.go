// GoCollect daemon, collects data through supplied scripts, writes data
// to a central server.
package gocollector

import (
    "log"
)

var logger *log.Logger

func SetLog(suggestedLogger *log.Logger) {
    logger = suggestedLogger
}
