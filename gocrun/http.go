// Package gocrun (gocollect) is the core of the GoCollect daemon. The
// Run() method will do the collecting and submitting to the central
// server.
package gocrun

import (
	"errors"
	"io"
	"io/ioutil"
	"net/http"
	"time"
)

var httpClient *http.Client
var httpTransport *http.Transport

// Do all HTTP initialization.
func httpInit() {
	// Set default HTTP options to with-keepalives (was the default
	// anyway, but it's nice to be explicit) and set a 45s timeout.
	httpTransport = &http.Transport{
		DisableKeepAlives: false, MaxIdleConnsPerHost: 1}
	httpClient = &http.Client{
		Transport: httpTransport, Timeout: 45 * time.Second}
}

// Do all HTTP cleanup/finalization.
func httpFinish() {
	// If the server supports connection keepalive, this will close
	// everything down when we're done with a POST run. The daemon stays
	// running, but we won't be doing much for a long while.
	httpTransport.CloseIdleConnections()
}

// Perform a JSON HTTP POST call.
func httpPost(url string, version string, data io.Reader) ([]byte, error) {
	req, err := http.NewRequest("POST", url, data)
	// req.Header.Set("Connection", "keep-alive") // HTTP/1.1 auto
	req.Header.Set("User-Agent", "GoCollect/"+version)
	req.Header.Set("Content-Type", "application/json")
	resp, err := httpClient.Do(req)

	var output []byte
	if resp != nil {
		output, err = ioutil.ReadAll(resp.Body)
		resp.Body.Close()
	} else {
		output = []byte("")
	}

	if err == nil && !(200 <= resp.StatusCode && resp.StatusCode < 400) {
		err = errors.New("non-2xx/3xx status")
	}

	return output, err
}
