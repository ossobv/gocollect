// GoCollect daemon, collects data through supplied scripts, writes data
// to a central server.
package main

import (
	"bytes"
	"fmt"
	getopt "github.com/ossobv/go-getopt"
	"io/ioutil"
	golog "log"
	"log/syslog"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/ossobv/gocollect/gocollect-client/log"
	"github.com/ossobv/gocollect/gocollect-client/runner"
	"github.com/ossobv/gocollect/gocollect-client/runnerinst"

	// Import builtin collectors.
	_ "github.com/ossobv/gocollect/gocollect-client/collectors"
)

// Initialized by -X ldflag. (Should be const, but is not allowed by the
// language.)
var versionStr string

// The configfile consists of a series of key=value pairs where key is
// not unique. However, for keys where only a single value makes sense,
// only the *last* value found will be used.
type configMap map[string]([]string)

const defaultConfigFile = "/etc/gocollect.conf"
const defaultRegidFilename = "/var/lib/gocollect/core.id.regid"

func printVersionAndExit() {
	fmt.Printf(
		("gocollect (GoCollect sysinfo collector) %s\n" +
			"Copyright (C) 2016-2017 OSSO B.V.\n" +
			"License GPLv3+: GNU GPL version 3 or later " +
			"<http://gnu.org/licenses/gpl.html>.\n" +
			"This is free software: you are free to change " +
			"and redistribute it.\n" +
			"There is NO WARRANTY, to the extent permitted by law.\n" +
			"\n" +
			"Written by Walter Doekes. " +
			"See <https://github.com/ossobv/gocollect>.\n"),
		versionStr)
	os.Exit(0)
}

func printErrorAndExit(errstr string, optionDefinition getopt.Options) {
	fmt.Fprintf(
		os.Stderr, "%s: %s\n\n%s\nSee --help for more info.\n",
		filepath.Base(os.Args[0]), errstr,
		strings.TrimSpace(optionDefinition.Usage()))
	os.Exit(1)
}

func getOptionDefinition() getopt.Options {
	return getopt.Options{
		// ..4...8......16......24......32......40......48......56......64
		Description: ("GoCollect collects data through a series of scripts " +
			"and publishes it to\na central server."),
		Definitions: getopt.Definitions{
			{OptionDefinition: "config|c",
				Description:  "config file",
				Flags:        (getopt.Optional | getopt.ExampleIsDefault),
				DefaultValue: defaultConfigFile},
			{OptionDefinition: "one-shot|s",
				Description:  "run once and exit",
				Flags:        getopt.Flag,
				DefaultValue: false},
			{OptionDefinition: "test-key|k",
				Description:  "print single collector output on stdout",
				Flags:        getopt.Optional,
				DefaultValue: ""},
			{OptionDefinition: "without-root",
				Description:  "allow run as non-privileged user",
				Flags:        getopt.Flag,
				DefaultValue: false},
			{OptionDefinition: "version|V",
				Description:  "print version",
				Flags:        getopt.Flag,
				DefaultValue: false},
		},
	}
}

func parseArgsOrExit() (options map[string]getopt.OptionValue) {
	optionDefinition := getOptionDefinition()
	options, arguments, passThrough, e := optionDefinition.ParseCommandLine()

	// Check and print help before checking option syntax.
	if _, ok := options["help"]; ok {
		fmt.Print(optionDefinition.Help())
		os.Exit(0)
	} else if e != nil {
		printErrorAndExit(e.Error(), optionDefinition)
	} else if len(arguments) > 0 {
		printErrorAndExit("too many arguments", optionDefinition)
	} else if val, ok := options["version"]; ok && val.Bool {
		printVersionAndExit()
	} else if len(passThrough) != 0 {
		errstr := fmt.Sprintf("excess args after -- %#v", passThrough)
		printErrorAndExit(errstr, optionDefinition)
	}

	// debugPrintOptions(options)
	return options
}

func debugPrintOptions(options map[string]getopt.OptionValue) {
	for key, value := range options {
		fmt.Printf("%s = %v\n", key, value)
	}
}

func parseConfigOrExit(filename string) (config configMap) {
	data, e := ioutil.ReadFile(filename)
	if e != nil {
		fmt.Fprintf(
			os.Stderr, "%s: %s\n\nSee --help for more info.\n",
			filepath.Base(os.Args[0]), e.Error())
		os.Exit(1)
	}

	config = configMap{}
	config["config_path"] = []string{filepath.Dir(filename)}
	parseConfigWithIncludes(&config, filename, data, 0)
	// debugPrintConfig(config)
	return config
}

func parseConfigWithIncludes(config *configMap, filename string,
	data []byte, depth int) {
	if depth >= 10 {
		fmt.Fprintf(
			os.Stderr, "%s: Ridiculous include depth in %s config file!\n",
			filepath.Base(os.Args[0]), filename)
		os.Exit(1)
	}

	for i, line := range bytes.Split(data, []byte{'\n'}) {
		line = bytes.TrimSpace(line)
		if len(line) > 0 && line[0] != '#' {
			args := bytes.SplitN(line, []byte{'='}, 2)
			if len(args) == 2 {
				key := string(bytes.TrimSpace(args[0]))
				value := string(bytes.TrimSpace(args[1]))

				if key == "include" {
					newData, e := ioutil.ReadFile(value)
					if e == nil {
						parseConfigWithIncludes(config, value, newData,
							depth+1)
					}
				} else {
					(*config)[key] = append((*config)[key], value)
				}

			} else {
				fmt.Fprintf(
					os.Stderr, "%s:%d: missing equals sign\n", filename, i)
			}
		}
	}
}

func debugPrintConfig(config configMap) {
	for key := range config {
		for _, val := range config[key] {
			fmt.Printf("%s = %s\n", key, val)
		}
	}
}

func checkOptionsOrExit(options map[string]getopt.OptionValue) {
	// Check that user is root.
	if os.Getuid() != 0 && !options["without-root"].Bool {
		if _, ok := options["test-key"]; ok {
			fmt.Fprintf(
				os.Stderr,
				("%s: Beware, running the collector as non-superuser may " +
					"yield incomplete data.\n"),
				filepath.Base(os.Args[0]))
			// don't exit
		} else {
			fmt.Fprintf(
				os.Stderr,
				("%s: Running gocollect as non-privileged user may " +
					"cause several\n" +
					"collectors to return too little info. Pass " +
					"--without-root to bypass this check.\n"),
				filepath.Base(os.Args[0]))
			os.Exit(1)
		}
	}

	// Only allow --test-key with --one-shot.
	if _, ok := options["test-key"]; ok && !options["one-shot"].Bool {
		fmt.Fprintf(
			os.Stderr,
			"%s: --test-key only works together with --one-shot.\n",
			filepath.Base(os.Args[0]))
		os.Exit(1)
	}
}

func createCollectRunner(
	options map[string]getopt.OptionValue, config configMap) (
	ret runner.Runner) {

	// Take options and config and extract relevant values.
	if keys, ok := config["api_key"]; ok {
		ret.APIKey = keys[len(keys)-1] // must have len>=1
	}
	if urls, ok := config["register_url"]; ok {
		ret.RegisterURL = urls[len(urls)-1] // must have len>=1
	}
	if urls, ok := config["push_url"]; ok {
		ret.PushURL = urls[len(urls)-1] // must have len>=1
	}
	ret.ConfigPathBase = config["config_path"][0]
	ret.CollectorsPaths = config["collectors_path"]
	ret.RegidFilename = defaultRegidFilename
	ret.GoCollectVersion = versionStr

	return ret
}

func setupLogger(oneShot bool) *golog.Logger {
	// Drop stdin. We may need stdout/stderr though.
	os.Stdin.Close()

	// Initialize logger, based on oneshot boolean.
	var logger *golog.Logger
	if oneShot {
		logger = golog.New(os.Stderr, "", golog.LstdFlags)
	} else {
		tmp, err := syslog.NewLogger(syslog.LOG_DAEMON|syslog.LOG_INFO, 0)
		if err == nil {
			logger = tmp
		} else {
			fmt.Fprintf(os.Stderr, "error opening syslog: %s\n", err)
			logger = golog.New(os.Stderr, "", golog.LstdFlags)
		}
	}
	return logger
}

func main() {
	// Check basic arguments.
	options := parseArgsOrExit()
	oneShot := options["one-shot"].Bool
	// Check config file.
	config := parseConfigOrExit(options["config"].String)
	// Passed options scan.
	checkOptionsOrExit(options)
	// Extract arguments, creating a CollectRunner.
	collectRunner := createCollectRunner(options, config)
	runnerinst.SetRunner(&collectRunner)
	defer runnerinst.SetRunner(nil)
	// Create and set global logger.
	log.Log = setupLogger(oneShot)

	// Do the work.
	os.Chdir("/")

	// Single test key.
	if testKey, ok := options["test-key"]; ok {
		result := collectRunner.Get(testKey.String)
		if result == "" {
			os.Exit(1)
		}
		fmt.Print(result)
		return
	}

	// Do complete run.
	os.Stdout.Close()
	for {
		ret := collectRunner.Run()
		if oneShot {
			if !ret {
				golog.Fatal("CollectRunner.Run() returned false")
			}
			return
		}

		time.Sleep(4 * 3600 * time.Second)
	}
}
