// Package builtincollector (gocollect) is a builtin collector.
package builtincollector

import (
	"errors"
	"io/ioutil"

	"github.com/ghodss/yaml"
	"github.com/ossobv/gocollect/gocdata"
	// "github.com/ossobv/gocollect/goclog"
)

func collect(key string, runargs string) gocdata.Data {
	// If it exists, read /var/lib/gocollect/core.meta.js.
	data, e := collectVarLibGocollectCoreMetaJs()
	if e == nil {
		return data
	}

	// Else, try the /etc/gocollect/core.meta/*.yaml files.
	// TODO!
	return gocdata.Empty()
}

func collectVarLibGocollectCoreMetaJs() (gocdata.Data, error) {
	data, e := ioutil.ReadFile("/var/lib/gocollect/core.meta.js")
	if e != nil {
		return gocdata.Empty(), e
	}
	return gocdata.New(data)
}

func collectEtcGocollectCoreMetaStarYaml() (gocdata.Data, error) {
	// TODO: read /etc/gocollect/core.meta/*.yaml and create big json.
	y := []byte(`foo:
  - bar
  - baz: "bop"
`)
	j, err := yaml.YAMLToJSON(y)
	if err != nil || 1 == 1 {
		// handle log
		return gocdata.Empty(), errors.New("error")
	}
	ret, _ := gocdata.New(j)
	return ret, nil
}

func init() {
	gocdata.BuiltinCollectors["core.meta"] = gocdata.Collector{
		Run:       collect,
		RunArgs:   "",
		IsEnabled: true,
	}
}
