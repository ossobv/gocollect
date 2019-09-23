// Package shcollectors (gocollect) makes shell-script plugins available
// for collection.
package shcollectors

import (
	"io/ioutil"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/ossobv/gocollect/gocollect-client/data"
	"github.com/ossobv/gocollect/gocollect-client/log"
)

// Find returns a object that holds all runnable collector scripts found
// in the supplied paths.
//
// The paths are scanned in reverse order. The file name is the unique
// key name. If the file is not executable, the collector is disabled.
func Find(paths []string) *data.Collectors {
	ret := data.Collectors{}

	last := len(paths) - 1
	for i := range paths {
		readpath := paths[last-i]

		filelist, e := ioutil.ReadDir(readpath)
		if e == nil {
			for _, fileinfo := range filelist {
				name := fileinfo.Name()
				// Since we scan the items in reverse order, we only add
				// the file if it didn't exist yet.
				if _, exists := ret[name]; !exists {
					collector := fileToCollector(fileinfo, readpath)
					if collector != nil {
						ret[name] = *collector
					}
				}
			}
		}
	}
	return &ret
}

func fileToCollector(fileinfo os.FileInfo, readpath string) *data.Collector {
	// Ignore it if it's a directory.
	if fileinfo.IsDir() {
		return nil
	}

	// Create a new collector.
	return &data.Collector{
		// Our runner
		Run: runShellCollector,
		// Set full path
		RunArgs: filepath.Join(readpath, fileinfo.Name()),
		// If the file is not executable, disable it
		IsEnabled: isExecutable(fileinfo),
	}
}

// runShellCollector runs the collector named key, with specified
// execpath and returns a Data object.
func runShellCollector(key string, execpath string) data.Collected {
	// Create a clean environment without LC_ALL to mess up output.
	// But make sure there is a valid path so we can find useful
	// binaries like ip(1).
	pathEnv := os.Getenv("PATH")
	if pathEnv == "" {
		pathEnv = ("PATH=/usr/local/sbin:/usr/local/bin:" +
			"/usr/sbin:/usr/bin:/sbin:/bin")
	} else {
		pathEnv = "PATH=" + pathEnv
	}
	cleanEnv := []string{pathEnv}

	// Check if there is a timeout binary before defaulting to using it.
	cmd := exec.Command("timeout", "1s", "/bin/true")
	cmd.Env = cleanEnv
	stdout, e := cmd.Output()

	if e == nil {
		// TODO: point stderr to somewhere?
		cmd = exec.Command("timeout", "180s", execpath)
		cmd.Env = cleanEnv
		stdout, e = cmd.Output()
	} else {
		// Go without timeout.
		log.Log.Printf(
			"collector[%s]: no timeout binary found to use", key)
		cmd = exec.Command(execpath)
		cmd.Env = cleanEnv
		stdout, e = cmd.Output()
	}

	// If the process returned non-zero, then err is non-nil. However,
	// if we're using filters in the command, then we will probably get
	// a zero exit anyway. We'll have to check for valid JS too.
	if e == nil {
		// Really really valid?
		ret, e := data.NewCollected(stdout)
		if e == nil {
			return ret
		}

		// I guess not.
		log.Log.Printf(
			"collector[%s]: decode error: %s", key, e.Error())
		log.Log.Printf("collector[%s]: data: %s", key, stdout)
	} else {
		// Probably '!cmd.ProcessState.Success()'.
		log.Log.Printf(
			"collector[%s]: %s error: %s", key, execpath, e.Error())
	}

	// Tell the server that something is wrong here.
	ret, _ := data.NewCollected([]byte("{\"error\":\"EINVAL\"}\n"))
	return ret
}

func isExecutable(fileinfo os.FileInfo) bool {
	if fileinfo.IsDir() {
		return false
	}

	mode := fileinfo.Mode()
	if (mode & 0111) == 0 {
		return false
	}
	return true
}
