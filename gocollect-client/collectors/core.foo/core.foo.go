// Package builtincollector (gocollect) is a builtin collector.
package builtincollector

import (
	"github.com/ossobv/gocollect/gocollect-client/data"
)

func runCoreMeta(key string, runargs string) data.Collected {
	ret, _ := data.NewCollected([]byte("{\"foo\":\"bar\"}"))
	return ret
}

func init() {
	data.BuiltinCollectors["core.foo"] = data.Collector{
		Run:       runCoreMeta,
		RunArgs:   "",
		IsEnabled: false,
	}
}
