// Package runner (gocollect) is the core of the GoCollect daemon. The
// Push() method will do the collecting and submitting to the central
// server.
package runner

// Runner holds everything we need for gocollect action. Set all fields
// to a valid value before calling Push().
type Runner struct {
	ConfigPathBase   string
	RegisterURL      string
	PushURL          string
	APIKey           string
	CollectorsPaths  []string
	RegidFilename    string
	GoCollectVersion string

	// Sampled collector (spool) settings.
	// Collectors whose name starts with any SampledPrefixes are sampled via
	// Sample() and stored in SpoolPath. Push() then pushes the mode
	// (most frequent value) from the last SampledN snapshots instead of
	// a fresh run. Set SpoolPath to "" to disable spool behaviour.
	SpoolPath       string
	SampledN        int
	SampledPrefixes []string
}

// Push collects data from the collectors and pushes data to the central
// server. If needed, it registers first.
func (r *Runner) Push() bool {
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
	if runner.runAll() != runSuccess {
		return false
	}
	return true
}

// Sample runs all sampled collectors (those matching SampledPrefixes) and
// saves each output to SpoolPath. It is a no-op when SpoolPath is empty.
func (r *Runner) Sample() {
	if r.SpoolPath == "" {
		return
	}
	runner := newRunInfo(r)
	runner.sampleCollectors()
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
