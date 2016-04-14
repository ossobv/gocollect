// GoCollect daemon, collects data through supplied scripts, writes data
// to a central server.
package gocollector

import (
    "bytes"
    "encoding/json"
    "io"
    "strings"
)

type Collected interface {
    // The same as the io.Reader interface; used when posting data
    // through HTTP.
    Read(p []byte) (n int, err error)

    // Methods that operate on the JSON dictionary.
    GetString(key string) string
    BuildString(template string, extra *map[string]string) string
}

type CollectedData struct {
    data string  // json-blob
    readpos int  // read-once position
}

func NewCollected(data []byte) (Collected, error) {
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

    tmp := CollectedData{data: compacted.String()}
    return &tmp, nil
}

func (c *CollectedData) Read(p []byte) (n int, err error) {
    written := copy(p, []byte(c.data[c.readpos:]))
    c.readpos += written
    if c.readpos == len(c.data) {
        return written, io.EOF
    }
    return written, nil
}

// Get a single value from the key-values stored in the Collected data.
// Data:        {"fqdn":"1.2.3.4","regid":"12345"}
// Key:         fqdn
// Returns:     1.2.3.4
func (c *CollectedData) GetString(key string) string {
    decoded := make(map[string]string)
    e := json.Unmarshal([]byte(c.data), &decoded)
    if e != nil {
        // should have key here.. expand Collected[] ?
        logger.Printf("unmarshal fail: %s", e.Error())
    } else if val, ok := decoded[key]; ok {
        return val
    }
    return ""
}

// Long version of GetString: here you supply a string with {key} pieces
// which get replaced by the strings from the collected value.
// Data:        {"fqdn":"1.2.3.4","regid":"12345"}
// Template:    http://example.com/{regid}/{fqdn}/
// Returns:     http://example.com/12345/1.2.3.4/
func (c *CollectedData) BuildString(
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
            logger.Printf("missing tailing brace: %s", template)
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
