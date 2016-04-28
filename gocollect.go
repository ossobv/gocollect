// GoCollect daemon, collects data through supplied scripts, writes data
// to a central server.
package main

import (
    "bytes"
    "fmt"
    "io/ioutil"
    "log"
    "log/syslog"
    "os"
    "path"
    "strings"
    "time"
    getopt "github.com/kesselborn/go-getopt"
    "./gocollector"
)

// Initialized by -X ldflag. (Should be const, but is not allowed by the
// language.)
var versionStr string

// The configfile consists of a series of key=value pairs where key is
// not unique. However, for keys where only a single value makes sense,
// only the *last* value found will be used.
type configMap map[string]([]string)

const defaultConfigFile = "/etc/gocollect.conf"

var optionDefinition = getopt.Options{
    ("GoCollect collects data through a series of scripts and publishes it\n" +
     "to a central server."),
    getopt.Definitions{
        {"config|c", "config file", getopt.Optional, defaultConfigFile},
        {"one-shot|s", "run once and exit", getopt.Flag, false},
        {"without-root", "allow run as non-privileged user", getopt.Flag,
         false},
        {"version|V", "print version", getopt.Flag, false},
    },
}

func version() {
    fmt.Printf(
        ("gocollect (GoCollect sysinfo collector) %s\n" +
         "Copyright (C) 2016 OSSO B.V.\n" +
         "License GPLv3+: GNU GPL version 3 or later " +
         "<http://gnu.org/licenses/gpl.html>.\n" +
         "This is free software: you are free to change " +
         "and redistribute it.\n" +
         "There is NO WARRANTY, to the extent permitted by law.\n" +
         "\n" +
         "Written by Walter Doekes. " +
         "See <https://github.com/ossobv/gocollect>.\n"),
        versionStr)
}

func parseArgsOrExit() (options map[string]getopt.OptionValue) {
    options, arguments, passThrough, e := optionDefinition.ParseCommandLine()
    if _, ok := options["help"]; ok {
        fmt.Print(optionDefinition.Help())
        os.Exit(0)
    } else if e != nil || len(arguments) > 0 {
        errstr := "too many arguments"
        if e != nil {
            errstr = e.Error()
        }
	fmt.Fprintf(
            os.Stderr, "%s: %s\n\n%s\nSee --help for more info.\n",
            path.Base(os.Args[0]), errstr,
            strings.TrimSpace(optionDefinition.Usage()))
	os.Exit(1)
    } else if val, ok := options["version"]; ok && val.Bool {
        version()
	os.Exit(0)
    } else if len(passThrough) != 0 {
	fmt.Fprintf(
            os.Stderr,
            "%s: passthrough? %r\n\n%s\nSee --help for more info.\n",
            path.Base(os.Args[0]), passThrough,
            strings.TrimSpace(optionDefinition.Usage()))
	os.Exit(1)
    }

    if _, ok := options["config"]; !ok {
        options["config"] = getopt.OptionValue{String: defaultConfigFile}
    }

    return options
}

func parseConfigOrExit(filename string) (config configMap) {
    data, e := ioutil.ReadFile(filename)
    if e != nil {
	fmt.Fprintf(
            os.Stderr, "%s: %s\n\nSee --help for more info.\n",
            path.Base(os.Args[0]), e.Error())
	os.Exit(1)
    }

    config = configMap{}
    for i, line := range bytes.Split(data, []byte{'\n'}) {
        line = bytes.TrimSpace(line)
        if len(line) > 0 && line[0] != '#' {
            args := bytes.SplitN(line, []byte{'='}, 2)
            if len(args) == 2 {
                key := string(bytes.TrimSpace(args[0]))
                value := string(bytes.TrimSpace(args[1]))
                config[key] = append(config[key], value)
            } else {
                fmt.Fprintf(
                    os.Stderr, "%s:%d: missing equals sign\n", filename, i)
            }
        }
    }

    return config
}

func main() {
    // Check basic arguments.
    options := parseArgsOrExit()

    // Check config file.
    config := parseConfigOrExit(options["config"].String)

    // Passed options scan. Check that user is root.
    if os.Getuid() != 0 && !options["without-root"].Bool {
	fmt.Fprintf(
            os.Stderr,
            ("%s: Running gocollect as non-privileged user may " +
             "cause several\n" +
             "collectors to return too little info. Pass --without-root " +
             "to bypass this check.\n"),
            path.Base(os.Args[0]))
	os.Exit(1)
    }

    // Take options and config and extract relevant values.
    var registerUrl, pushUrl string
    if urls, ok := config["register_url"]; ok {
        registerUrl = urls[len(urls) - 1] // must have len>=1
    }
    if urls, ok := config["push_url"]; ok {
        pushUrl = urls[len(urls) - 1] // must have len>=1
    }
    collectorsPaths := config["collectors_path"]
    oneShot := options["one-shot"].Bool

    // TODO: fix hardcoded path?
    regidFilename := "/var/lib/gocollect/core.id.regid"

    // Drop stdin/stdout; we don't need 'm.
    os.Stdin.Close()
    os.Stdout.Close()

    // Initialize logger, based on oneshot boolean.
    var logger *log.Logger
    if oneShot {
        logger = log.New(os.Stderr, "", log.LstdFlags)
    } else {
        tmp, err := syslog.NewLogger(syslog.LOG_DAEMON | syslog.LOG_INFO, 0)
        if err == nil {
            logger = tmp
        } else {
            fmt.Fprintf(os.Stderr, "error opening syslog: %s\n", err)
            logger = log.New(os.Stderr, "", log.LstdFlags)
        }
    }

    // Time for some action.
    gocollector.SetLog(logger)
    for {
        ret := gocollector.CollectAndPostData(
            registerUrl, pushUrl, collectorsPaths, regidFilename)
        if oneShot {
            if !ret {
                log.Fatal("CollectAndPostData returned false")
            }
            return
        }

        time.Sleep(4 * 3600 * time.Second)
    }
}
