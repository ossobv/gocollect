// Package collectors (gocollect) makes builtin collectors available.
package collectors

import (
	"github.com/ossobv/gocollect/gocdata"
)

func runCoreMeta(key string, runargs string) gocdata.Data {
	ret, _ := gocdata.New([]byte("{\"foo\":\"bar\"}"))
	return ret
}

func init() {
	gocdata.BuiltinCollectors["core.foo"] = gocdata.Collector{
		Run:       runCoreMeta,
		RunArgs:   "",
		IsEnabled: false,
	}
}
