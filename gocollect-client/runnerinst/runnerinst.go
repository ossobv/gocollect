package runnerinst

import (
	"github.com/ossobv/gocollect/gocollect-client/runner"
)

// collectRunnerInstance can be used in rare circumstances when you need
// access to one of the Runner properties.
var runnerInstance *runner.Runner

// SetRunner is the ugly pattern to give access to the currently
// executing runner.
func SetRunner(instance *runner.Runner) {
	runnerInstance = instance
}

// GetRunner is the ugly pattern to allow access to the currently
// executing runner.
func GetRunner() *runner.Runner {
	return runnerInstance
}
