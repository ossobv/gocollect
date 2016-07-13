// GoCollect daemon, collects data through supplied scripts, writes data
// to a central server.
package gocollector

import (
    "io/ioutil"
    "os"
    "os/exec"
    "path"
    "sort"
)

type Collectors map[string]string

func NewFromPaths(paths []string) *Collectors {
    ret := Collectors{}

    last := len(paths) - 1
    for i := range paths {
        readpath := paths[last - i]

        filelist, e := ioutil.ReadDir(readpath)
        if e == nil {
            for _, fileinfo := range filelist {
                name := fileinfo.Name()
                if _, exists := ret[name]; !exists {
                    // We don't have this item yet. Add it. However, if
                    // it's non-executable, don't store the path because
                    // we won't run it: this can be used to block
                    // system defined collectors from a user-directory.
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

// Returns the keys that have a runnable collector.
func (c *Collectors) Runnable() (keys []string) {
    for key, value := range *c {
        if value != "" {
            keys = append(keys, key)
        }
    }
    sort.Strings(keys)
    return keys
}

func (c *Collectors) Run(key string) Collected {
    // Create a clean environment without LC_ALL to mess up output.
    // But make sure there is a valid path so we can find useful
    // binaries like ip(1).
    pathEnv := os.Getenv("PATH")
    if pathEnv == "" {
        pathEnv = (
            "PATH=/usr/local/sbin:/usr/local/bin:" +
            "/usr/sbin:/usr/bin:/sbin:/bin")
    } else {
        pathEnv = "PATH=" + pathEnv
    }
    cleanEnv := []string{pathEnv}

    // Check if there is a binary path; it's empty if it's non-
    // executable, which is a hint that we shouldn't run it.
    execpath := (*c)[key]
    if execpath == "" {
        logger.Printf("collector[%s]: no execpath", key)
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
        logger.Printf(
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
        // probably: !cmd.ProcessState.Success()
        logger.Printf(
            "collector[%s]: %s error: %s", key, execpath, e.Error())
        return nil
    }

    ret, e := NewCollected(stdout)
    if e != nil {
        logger.Printf(
            "collector[%s]: decode error: %s", key, e.Error())
        logger.Printf("collector[%s]: data: %s", key, stdout)
    }

    return ret
}

func isExecutable(fileinfo os.FileInfo) bool {
    if (fileinfo.IsDir()) {
        return false
    }

    mode := fileinfo.Mode()
    if (mode & 0111) == 0 {
        return false
    }
    return true
}
