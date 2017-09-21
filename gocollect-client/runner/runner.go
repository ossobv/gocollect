// Package runner (gocollect) is the core of the GoCollect daemon. The
// Run() method will do the collecting and submitting to the central
// server.
package runner

// Runner holds everything we need for gocollect action. Set all fields
// to a valid value before calling Run().
type Runner struct {
	RegisterURL      string
	PushURL          string
	APIKey           string
	CollectorsPaths  []string
	RegidFilename    string
	GoCollectVersion string
}

// Run collects data from the collectors and pushes data to the central
// server. If needed, it registers first.
func (r *Runner) Run() bool {
	runner := newRunInfo(r)

	// Initialize HTTP calls.
	httpInit()
	defer httpFinish()

	// Fetch the core info -- which also fetches the regid.
	if !runner.setCoreIDData() {
		return false
	}

	// Check if we need to register first.
	if runner.needsRegister() {
		if !runner.runRegister() {
			return false
		}
	}

	// Then run all collectors.
	runner.runAll()
	return true
}

// Get collects data from a single collector and returns it as a string.
func (r *Runner) Get(collectorKey string) string {
	runner := newRunInfo(r)
	collected := runner.runCollector(collectorKey)
	if collected == nil {
		return ""
	}
	return collected.String()
}
