// Package gocrun (gocollect) is the core of the GoCollect daemon. The
// Run() method will do the collecting and submitting to the central
// server.
package gocrun

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
