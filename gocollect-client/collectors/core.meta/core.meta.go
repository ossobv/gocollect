// Package builtincollector (gocollect) is a builtin collector.
package builtincollector

import (
	"encoding/json"
	"io/ioutil"
	"path/filepath"
	"strings"

	// Using "gopkg.in/yaml.v2" yields us:
	// > json: unsupported type: map[interface {}]interface {}
	// when trying to json-encode YAML structures we merged into a new
	// map.
	"github.com/ghodss/yaml"

	"github.com/ossobv/gocollect/gocollect-client/data"
	"github.com/ossobv/gocollect/gocollect-client/log"
)

// Hardcoded paths for now.
const coreMetaJsPath = "/var/lib/gocollect/core.meta.js"
const coreMetaStarYamlPath = "/etc/gocollect/core.meta"

func collect(key string, runargs string) data.Collected {
	// If it exists, read JS file from /var/lib/gollect; old style.
	if collected, err := collectVarLibGocollectCoreMetaJs(); err == nil {
		return collected
	}

	// If it doesn't, read the combined YAML files from /etc; new style.
	if collected, err := collectEtcGocollectCoreMetaStarYaml(); err == nil {
		return collected
	}

	return data.EmptyCollected()
}

func collectVarLibGocollectCoreMetaJs() (data.Collected, error) {
	// If this fails here, ignore it silently.
	collected, err := ioutil.ReadFile(coreMetaJsPath)
	if err != nil {
		return nil, err
	}
	return data.NewCollected(collected)
}

func collectEtcGocollectCoreMetaStarYaml() (data.Collected, error) {
	// If this fails here, ignore it silently.
	yamlData, err := getYamlData(coreMetaStarYamlPath)
	if err != nil {
		return nil, err
	}

	// Past this point, we'll want to know that something was wrong.
	outDict := make(map[string]interface{})

	for key, yamlBytes := range yamlData {
		var yamlObj interface{}
		err := yaml.Unmarshal(yamlBytes, &yamlObj)
		if err != nil {
			log.Log.Printf("collector[core.meta]: yaml: %s", err)
		} else {
			outDict[key] = yamlObj
		}
	}

	jsonBytes, err := json.Marshal(&outDict)
	if err != nil {
		log.Log.Printf("collector[core.meta]: json: %s", err)
		return nil, err
	}

	return data.NewCollected(jsonBytes)
}

func getYamlData(filespath string) (map[string]([]byte), error) {
	ret := make(map[string]([]byte))

	// ReadDir reads the directory named by dirname and returns a list
	// of directory entries sorted by filename.
	filelist, err := ioutil.ReadDir(filespath)
	if err != nil {
		return nil, err
	}

	for _, fileinfo := range filelist {
		if !fileinfo.IsDir() {
			name := fileinfo.Name()
			if !strings.HasPrefix(name, ".") &&
				strings.HasSuffix(name, ".yaml") {
				fullpath := filepath.Join(filespath, name)
				data, err := ioutil.ReadFile(fullpath)
				if err != nil {
					log.Log.Printf("collector[core.meta]: %s: %s", fullpath,
						err)
				} else {
					nameWithoutYaml := name[0 : len(name)-5] // ".yaml"
					ret[nameWithoutYaml] = data
				}
			}
		}
	}
	return ret, nil
}

func init() {
	data.BuiltinCollectors["core.meta"] = data.Collector{
		Run:       collect,
		RunArgs:   "",
		IsEnabled: true,
	}
}
