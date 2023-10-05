// Package runner (gocollect) is the core of the GoCollect daemon. The
// Run() method will do the collecting and submitting to the central
// server.
package runner

import (
	"encoding/json"
	"io/ioutil"
	"os"
	"path/filepath"

	"github.com/ossobv/gocollect/gocollect-client/data"
	"github.com/ossobv/gocollect/gocollect-client/log"
	"github.com/ossobv/gocollect/gocollect-client/shcollectors"
)

type runInfo struct {
	runner     *Runner
	collectors *data.Collectors
	coreIDData data.Collected
}

type runStatus int

const (
	runSuccess runStatus = iota
	runFailedFirst
	runFailedSome
)

func newRunInfo(r *Runner) (ri runInfo) {
	ri.runner = r
	ri.collectors = data.MergeCollectors(
		&data.BuiltinCollectors, shcollectors.Find(r.CollectorsPaths))
	return ri
}

func (ri *runInfo) setCoreIDData() bool {
	ri.coreIDData = ri.collectors.Run("core.id")
	if ri.coreIDData == nil {
		return false
	}

	// Patch core.id with our version and optional apiKey.
	ri.coreIDData.SetString("gocollect", ri.runner.GoCollectVersion)
	if ri.runner.APIKey != "" {
		ri.coreIDData.SetString("gocollect-apikey", ri.runner.APIKey)
	}

	return true
}

func (ri *runInfo) needsRegister() bool {
	return ri.coreIDData.GetString("regid") == ""
}

func (ri *runInfo) runRegister() bool {
	regid := ri.coreIDData.GetString("regid")
	if regid == "" {
		// Post data, expect {"data":{"regid":"12345"}}.
		result := ri.register(ri.coreIDData)
		if !result {
			return false
		}

		// Re-get core.id data: this time we must have regid or core.id
		// is broken (or the registration helper).
		ri.coreIDData = ri.collectors.Run("core.id")
		if ri.coreIDData == nil {
			return false
		}

		regid = ri.coreIDData.GetString("regid")
		if regid == "" {
			log.Log.Fatal("No regid after register from core.id")
			return false
		}
	}

	return true
}

func (ri *runInfo) runAll() runStatus {
	ret := runSuccess
	collectors := 0

	// Run all collectors and push.
	extraContext := map[string]string{"_collector": "<value>"}
	for _, collectorKey := range ri.collectors.GetRunnable() {
		// Run a (patched) collector.
		collected := ri.runCollector(collectorKey)
		if collected == nil {
			// logger.Printf(
			//     "collector[%s]: exec fail", collectorKey)
			continue
		}

		// We update the pushURL for every push because the _collector
		// is in it, which changes continuously.
		extraContext["_collector"] = collectorKey
		pushURL := ri.coreIDData.BuildString(ri.runner.PushURL, &extraContext)

		if !ri.push(pushURL, collected) {
			log.Log.Printf("push: aborting early; assuming server is broken")
			if collectors == 0 {
				ret = runFailedFirst
			} else {
				ret = runFailedSome
			}
			break
		}

		collectors += 1
	}

	return ret
}

func (ri *runInfo) runCollector(collectorKey string) data.Collected {
	switch collectorKey {
	case "core.id":
		// Use helper.
		if ri.coreIDData == nil {
			ri.setCoreIDData()
		}
		return ri.coreIDData
	default:
		// Exec the collector.
		return ri.collectors.Run(collectorKey)
	}
}

func (ri *runInfo) register(coreIDData data.Collected) bool {
	registerURL := ri.runner.RegisterURL

	// Post data, expect {"data":{"regid":"12345"}}.
	data, err := httpPost(registerURL, ri.runner.GoCollectVersion, coreIDData)
	if err != nil {
		log.Log.Printf("register[url=%s]: failed: %s", registerURL, err)
		return false
	}

	var decoded map[string](map[string]string)
	err = json.Unmarshal(data, &decoded)
	if err != nil {
		log.Log.Printf("register[url=%s]: failed: %s", registerURL, err)
		return false
	}

	value := decoded["data"]["regid"]
	if value == "" {
		log.Log.Printf("register[url=%s]: failed: got nothing", registerURL)
		return false
	}

	os.MkdirAll(filepath.Dir(ri.runner.RegidFilename), 0755)
	err = ioutil.WriteFile(ri.runner.RegidFilename, []byte(value), 0400)
	if err != nil {
		log.Log.Fatal("Could not write core.id.regid: ", err)
		return false
	}

	log.Log.Printf("register[url=%s]: got %s", registerURL, value)
	return true
}

func (ri *runInfo) push(pushURL string, collectedData data.Collected) bool {
	if collectedData.IsEmpty() {
		log.Log.Printf("push[url=%s]: not pushing empty data", pushURL)
		return true
	}

	data, err := httpPost(pushURL, ri.runner.GoCollectVersion, collectedData)
	if err != nil {
		log.Log.Printf("push[url=%s]: failed: %s", pushURL, err)
		return false
	}

	log.Log.Printf("push[url=%s]: got %s", pushURL, string(data))
	return true
}
