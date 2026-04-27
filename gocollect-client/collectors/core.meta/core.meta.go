// Package builtincollector (gocollect) is a builtin collector.
package builtincollector

import (
	"encoding/json"
	"io/ioutil"
	"os"
	"path/filepath"
	"strings"

	// Using "gopkg.in/yaml.v2" yields us:
	// > json: unsupported type: map[interface {}]interface {}
	// when trying to json-encode YAML structures we merged into a new
	// map.
	"github.com/ghodss/yaml"

	"github.com/ossobv/gocollect/gocollect-client/data"
	"github.com/ossobv/gocollect/gocollect-client/log"
	"github.com/ossobv/gocollect/gocollect-client/runnerinst"
	"github.com/ossobv/gocollect/gocollect-client/sanejoin"
)

// Hardcoded paths for now.
const coreMetaJsPath = "/var/lib/gocollect/core.meta.js"
const coreMetaStarYamlPath = "./gocollect/core.meta" // relative to conf

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
	// Get config path.
	yamlPath := coreMetaStarYamlPath
	runner := runnerinst.GetRunner()
	if runner != nil {
		yamlPath = sanejoin.Join((*runner).ConfigPathBase, yamlPath)
	}

	// If this fails here, ignore it silently.
	yamlData, err := getYamlData(yamlPath)
	if err != nil {
		return nil, err
	}

	jsonBytes, err := json.Marshal(&yamlData)
	if err != nil {
		log.Log.Printf("collector[core.meta]: json: %s", err)
		return nil, err
	}

	return data.NewCollected(jsonBytes)
}

func getYamlData(filespath string) (map[string]interface{}, error) {
	ret := make(map[string]interface{})

	// ReadDir reads the directory named by dirname and returns a list
	// of directory entries sorted by filename.
	filelist, err := os.ReadDir(filespath)
	if err != nil {
		return nil, err
	}

	for _, direntry := range filelist {
		name := direntry.Name()
		if direntry.IsDir() {
			if !strings.HasPrefix(name, ".") {
				subpath := sanejoin.Join(filespath, name)
				data, err := getYamlData(subpath)
				if err != nil {
					log.Log.Printf("collector[core.meta]: %s: %s", subpath,
						err)
				} else {
					ret[name] = data
				}
			}
		} else {
			if !strings.HasPrefix(name, ".") &&
				strings.HasSuffix(name, ".yaml") {
				fullpath := filepath.Join(filespath, name)
				data, err := ioutil.ReadFile(fullpath)
				if err != nil {
					log.Log.Printf("collector[core.meta]: %s: %s", fullpath,
						err)
				} else {
					var yamlObj interface{}
					err := yaml.Unmarshal(data, &yamlObj)
					if err != nil {
						log.Log.Printf("collector[core.meta]: %s: %s",
							fullpath, err)
					} else {
						nameWithoutYaml := name[0 : len(name)-5] // ".yaml"
						ret[nameWithoutYaml] = yamlObj
					}
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
