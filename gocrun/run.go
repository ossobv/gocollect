// Package gocrun (gocollect) is the core of the GoCollect daemon. The
// Run() method will do the collecting and submitting to the central
// server.
package gocrun

import (
	"encoding/json"
	"io/ioutil"
	"os"
	"path"

	"github.com/ossobv/gocollect/gocdata"
	"github.com/ossobv/gocollect/goclog"
	"github.com/ossobv/gocollect/gocshell"
)

// Run collects data from the collectors and pushes data to the central
// server. If needed, it registers first.
func (r *Runner) Run() bool {
	// Collect all collectors based on the supplied paths.
	collectors := gocshell.FindShellCollectors(r.CollectorsPaths)

	// Set default timeout to 45 seconds.
	httpInit()
	defer httpFinish()

	// Fetch the core info -- which also fetches the regid.
	coreIDData := collectors.Run("core.id")
	if coreIDData == nil {
		return false
	}

	// Patch core.id with our version and optional apiKey.
	coreIDData.SetString("gocollect", r.GoCollectVersion)
	if r.APIKey != "" {
		coreIDData.SetString("gocollect-apikey", r.APIKey)
	}

	// Check if we need to register first.
	regid := coreIDData.GetString("regid")
	if regid == "" {
		// Post data, expect {"data":{"regid":"12345"}}.
		result := r.register(coreIDData)
		if !result {
			return false
		}

		// Re-get core.id data: this time we must have regid or core.id
		// is broken (or the registration helper).
		coreIDData = collectors.Run("core.id")
		if coreIDData == nil {
			return false
		}

		regid = coreIDData.GetString("regid")
		if regid == "" {
			goclog.Log.Fatal("No regid after register from core.id")
			return false
		}
	}

	// Run all collectors and push.
	extraContext := map[string]string{"_collector": "<value>"}
	for _, collectorKey := range collectors.Runnable() {
		var collected gocdata.Data

		switch collectorKey {
		case "core.id":
			// No need to fetch it again. And besides, we patched it
			// above to contain the version as well.
			collected = coreIDData
		default:
			// Exec the collector.
			collected = collectors.Run(collectorKey)
		}

		if collected == nil {
			//logger.Printf("collector[%s]: exec fail", collectorKey)
			continue
		}

		// We update the pushURL for every push because the _collector
		// is in it, which changes continuously.
		extraContext["_collector"] = collectorKey
		tmpPushURL := coreIDData.BuildString(r.PushURL, &extraContext)

		r.push(tmpPushURL, collected)
	}

	return true
}

func (r *Runner) register(coreIDData gocdata.Data) bool {
	// Post data, expect {"data":{"regid":"12345"}}.
	data, err := httpPost(r.RegisterURL, coreIDData)
	if err != nil {
		goclog.Log.Printf("register[%s]: failed: %s", r.RegisterURL, err)
		return false
	}

	var decoded map[string](map[string]string)
	err = json.Unmarshal(data, &decoded)
	if err != nil {
		goclog.Log.Printf("register[%s]: failed: %s", r.RegisterURL, err)
		return false
	}

	value := decoded["data"]["regid"]
	if value == "" {
		goclog.Log.Printf("register[%s]: failed: got nothing", r.RegisterURL)
		return false
	}

	os.MkdirAll(path.Dir(r.RegidFilename), 0755)
	err = ioutil.WriteFile(r.RegidFilename, []byte(value), 0400)
	if err != nil {
		goclog.Log.Fatal("Could not write core.id.regid: ", err)
		return false
	}

	goclog.Log.Printf("register[%s]: got %s", r.RegisterURL, value)
	return true
}

func (r *Runner) push(pushURL string, collectedData gocdata.Data) bool {
	data, err := httpPost(pushURL, collectedData)
	if err != nil {
		goclog.Log.Printf("push[%s]: failed: %s", pushURL, err)
		return false
	}

	goclog.Log.Printf("push[%s]: got %s", pushURL, string(data))
	return true
}
