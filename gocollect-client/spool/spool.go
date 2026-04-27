// Package spool (gocollect) stores collector snapshots on disk and
// returns the most frequently occurring value (mode) across the last N
// snapshots. This is used by sampled collectors (e.g. app.*) to
// filter out transient changes.
package spool

import (
	"io/ioutil"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/ossobv/gocollect/gocollect-client/data"
	"github.com/ossobv/gocollect/gocollect-client/log"
)

// Save writes collected data to <spoolPath>/<key>/<timestamp>.json,
// then removes older files so that at most maxFiles are kept.
func Save(spoolPath, key string, collected data.Collected, maxFiles int) error {
	dir := filepath.Join(spoolPath, key)
	if err := os.MkdirAll(dir, 0700); err != nil {
		return err
	}

	filename := filepath.Join(
		dir, strconv.FormatInt(time.Now().Unix(), 10)+".json")
	if err := ioutil.WriteFile(filename, []byte(collected.String()), 0600); err != nil {
		return err
	}

	if maxFiles > 0 {
		trimOldFiles(dir, maxFiles)
	}
	return nil
}

// LoadMode reads the last n spool files for the given key and returns
// the most frequently occurring value as a data.Collected. Returns nil when
// no spool data exists yet.
func LoadMode(spoolPath, key string, n int) data.Collected {
	dir := filepath.Join(spoolPath, key)
	files, err := os.ReadDir(dir)
	if err != nil || len(files) == 0 {
		return nil
	}

	// os.ReadDir returns entries sorted by name; since names are
	// unix timestamps, newest entries are last. Take the last n.
	if len(files) > n {
		files = files[len(files)-n:]
	}

	counts := make(map[string]int)
	for _, f := range files {
		content, err := ioutil.ReadFile(filepath.Join(dir, f.Name()))
		if err == nil {
			counts[string(content)]++
		}
	}

	// Find the most frequent value. On a tie pick the lexicographically
	// larger string (deterministic, but still arbitrary; could be used by
	// a version index in front).
	var best string
	var bestCount int
	for content, count := range counts {
		if count > bestCount || (count == bestCount && content > best) {
			best = content
			bestCount = count
		}
	}

	if best == "" {
		return nil
	}

	collected, err := data.NewCollected([]byte(best))
	if err != nil {
		log.Log.Printf("spool[%s]: parse error: %s", key, err)
		return nil
	}
	return collected
}

// trimOldFiles deletes the oldest files in dir until at most keep
// remain.
func trimOldFiles(dir string, keep int) {
	files, err := os.ReadDir(dir)
	if err != nil || len(files) <= keep {
		return
	}
	for _, f := range files[:len(files)-keep] {
		os.Remove(filepath.Join(dir, f.Name()))
	}
}
