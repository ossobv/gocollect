// Package builtincollector (gocollect) is a builtin collector.
package builtincollector

import (
	"errors"
	"io/ioutil"

	"github.com/ghodss/yaml"
	"github.com/ossobv/gocollect/gocollect-client/data"
	// "github.com/ossobv/gocollect/goclog"
)

func collect(key string, runargs string) data.Collected {
	// If it exists, read /var/lib/gocollect/core.meta.js.
	collected, e := collectVarLibGocollectCoreMetaJs()
	if e == nil {
		return collected
	}

	// Else, try the /etc/gocollect/core.meta/*.yaml files.
	// TODO!
	return data.EmptyCollected()
}

func collectVarLibGocollectCoreMetaJs() (data.Collected, error) {
	collected, e := ioutil.ReadFile("/var/lib/gocollect/core.meta.js")
	if e != nil {
		return data.EmptyCollected(), e
	}
	return data.NewCollected(collected)
}

func collectEtcGocollectCoreMetaStarYaml() (data.Collected, error) {
	// TODO: read /etc/gocollect/core.meta/*.yaml and create big json.
	y := []byte(`foo:
  - bar
  - baz: "bop"
`)
	j, err := yaml.YAMLToJSON(y)
	if err != nil || 1 == 1 {
		// handle log
		return data.EmptyCollected(), errors.New("error")
	}
	ret, _ := data.NewCollected(j)
	return ret, nil
}

func init() {
	data.BuiltinCollectors["core.meta"] = data.Collector{
		Run:       collect,
		RunArgs:   "",
		IsEnabled: true,
	}
}
