// Package gocshell (gocollect) makes shell-script plugins available for
// collection.
package gocshell

import (
	"io/ioutil"
	"os"
	"os/exec"
	"path"
	"sort"

	"github.com/ossobv/gocollect/gocdata"
	"github.com/ossobv/gocollect/goclog"
)

// Collectors holds a key/value map of strings where key is the
// collector name and value is the collector path. If a path is the
// empty string, it means the collector exists but was intentionally
// disabled.
type Collectors map[string]string

// FindShellCollectors returns a object that holds all runnable
// collector scripts found in the supplied paths.
//
// The paths are scanned in reverse order. The file name is the unique
// key name. If the file is not executable, the collector is stored
// without path to signify that it's disabled.
func FindShellCollectors(paths []string) *Collectors {
	ret := Collectors{}

	last := len(paths) - 1
	for i := range paths {
		readpath := paths[last-i]

		filelist, e := ioutil.ReadDir(readpath)
		if e == nil {
			for _, fileinfo := range filelist {
				name := fileinfo.Name()
				if _, exists := ret[name]; !exists {
					// We don't have this item yet. Add it. However, if
					// it's non-executable, don't store the path because
					// we won't run it: this can be used to block
					// system defined Collectors from a user-directory.
					fullpath := ""
					if isExecutable(fileinfo) {
						// Yes, executable. Make it runnable.
						fullpath = path.Join(readpath, name)
					}
					ret[name] = fullpath
				}
			}
		}
	}

	return &ret
}

// Runnable returns all keys that have a runnable collector.
func (c *Collectors) Runnable() (keys []string) {
	for key, value := range *c {
		if value != "" {
			keys = append(keys, key)
		}
	}
	sort.Strings(keys)
	return keys
}

// Run runs the collector named by key and returns a Data object.
func (c *Collectors) Run(key string) gocdata.Data {
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

	// Check if there is a binary path; it's empty if it's non-
	// executable, which is a hint that we shouldn't run it.
	execpath := (*c)[key]
	if execpath == "" {
		goclog.Log.Printf("collector[%s]: no execpath", key)
		return nil
	}

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
		goclog.Log.Printf(
			"collector[%s]: no timeout binary found to use", key)
		cmd = exec.Command(execpath)
		cmd.Env = cleanEnv
		stdout, e = cmd.Output()
	}

	// If the process returned non-zero, then err is non-nil.  However,
	// if we're using filters in the command, then we will probably get
	// a zero exit anyway.  We'll have to check for valid JS below
	// instead.
	if e != nil {
		// Probably: !cmd.ProcessState.Success()
		goclog.Log.Printf(
			"collector[%s]: %s error: %s", key, execpath, e.Error())
		return nil
	}

	ret, e := gocdata.New(stdout)
	if e != nil {
		goclog.Log.Printf(
			"collector[%s]: decode error: %s", key, e.Error())
		goclog.Log.Printf("collector[%s]: data: %s", key, stdout)
	}

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
