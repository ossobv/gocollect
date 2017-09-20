// Package gocdata (gocollect) holds the collected data to make it ready
// for submittal.
package gocdata

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"strings"

	"github.com/ossobv/gocollect/goclog"
)

// Data is the interface to operate on collected data. It molds
// collected bytes into something that implements HTTP POST method can
// read. Additionally, it allows alterations of top-level JSON key
// values.
type Data interface {
	// The same as the io.Reader interface; used when posting data
	// through HTTP.
	Read(p []byte) (n int, err error)

	// Get the data as a string.
	String() string

	// Methods that operate on the JSON dictionary.
	GetString(key string) string
	BuildString(template string, extra *map[string]string) string

	// Methods that alter the JSON dictionary.
	SetString(key string, value string) error
}

type collectedData struct {
	data    string // json-blob
	readpos int    // read-once position
}

// New creates a new Data object from the supplied bytes.
func New(data []byte) (Data, error) {
	// Compact the data and validate it at the same time.
	compacted := new(bytes.Buffer)
	e := json.Compact(compacted, data)
	if e != nil {
		// Parse error: invalid json, return null
		return nil, e
	}

	// Append a single linefeed which does no harm but is tremendously
	// beneficial for readability when storing the json as plaintext.
	compacted.WriteByte('\n')

	tmp := collectedData{data: compacted.String()}
	return &tmp, nil
}

// Empty creates a new empty Data object. Use when there is no data.
func Empty() Data {
	return &collectedData{data: ""}
}

func (c *collectedData) Read(p []byte) (n int, err error) {
	written := copy(p, []byte(c.data[c.readpos:]))
	c.readpos += written
	if c.readpos == len(c.data) {
		return written, io.EOF
	}
	return written, nil
}

func (c *collectedData) String() string {
	return c.data
}

// Get a single value from the key-values stored in the Data data.
// Data:	{"fqdn":"1.2.3.4","regid":"12345"}
// Key:		fqdn
// Returns:	1.2.3.4
func (c *collectedData) GetString(key string) string {
	decoded := make(map[string]string)
	e := json.Unmarshal([]byte(c.data), &decoded)
	if e != nil {
		// should have key here.. expand Data[] ?
		goclog.Log.Printf("unmarshal fail: %s", e.Error())
	} else if val, ok := decoded[key]; ok {
		return val
	}
	return ""
}

// Add/update a single string value in a Data object.
// Data:	{"fqdn":"1.2.3.4","regid":"12345"}
// Key:		gocollect
// Value:	1.2.3
// Returns:	error or updates Data to look like this:
//			{"fqdn":"1.2.3.4","regid":"12345","gocollect":"1.2.3"}
func (c *collectedData) SetString(key string, value string) error {
	// Check that no one has started reading already.
	if c.readpos != 0 {
		return errors.New("Cannot alter collected data after read")
	}

	decoded := make(map[string]string)
	e := json.Unmarshal([]byte(c.data), &decoded)
	if e != nil {
		return e
	}

	// Add/update the value.
	decoded[key] = value

	// NOTE: We assume here that:
	// (a) Marshal compacts the data.
	// (b) There is no non-string value in core.id, because if there was
	//	 our unmarshal above would have ignored it (right?).
	data, e := json.Marshal(decoded)
	if e != nil {
		return e
	}

	compacted := new(bytes.Buffer)
	compacted.Write(data)
	compacted.WriteByte('\n')
	c.data = compacted.String()

	return nil
}

// Long version of GetString: here you supply a string with {key} pieces
// which get replaced by the strings from the collected value.
// Data:	 {"fqdn":"1.2.3.4","regid":"12345"}
// Template: http://example.com/{regid}/{fqdn}/
// Returns:	 http://example.com/12345/1.2.3.4/
func (c *collectedData) BuildString(
	template string, extra *map[string]string) string {

	decoded := make(map[string]string)
	json.Unmarshal([]byte(c.data), &decoded) // ignore error-return

	parts := make([]string, 10)
	for {
		i := strings.IndexByte(template, '{')
		if i == -1 {
			parts = append(parts, template)
			break
		}
		parts = append(parts, template[0:i])
		// > Strings are actually very simple: they are just read-only
		// > slices of bytes with a bit of extra syntactic support from
		// > the language.
		// That means that I can cheaply do template[i:] here, which
		// I need because IndexByte doesn't take a start-parameter.
		j := strings.IndexByte(template[i:], '}')
		if j == -1 {
			goclog.Log.Printf("missing tailing brace: %s", template)
			break
		}
		j += i

		key := template[(i + 1):j]
		value, ok := (*extra)[key]
		if !ok {
			value = decoded[key]
		}
		parts = append(parts, value)

		template = template[(j + 1):]
	}

	return strings.Join(parts, "")
}
