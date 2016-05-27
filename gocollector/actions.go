// GoCollect daemon, collects data through supplied scripts, writes data
// to a central server.
package gocollector

import (
    "encoding/json"
    "errors"
    "io/ioutil"
    "net/http"
    "os"
    "path"
    "time"
)

func CollectAndPostData(registerUrl string, pushUrl string,
                        collectorsPaths []string, regidFilename string,
                        gocollectVersion string) bool {

    // Collect all collectors based on the supplied paths.
    collectors := NewFromPaths(collectorsPaths)

    // Set default timeout to 45 seconds.
    http.DefaultClient.Timeout = 45 * time.Second

    // Fetch the core info -- which also fetches the regid.
    coreIdData := collectors.Run("core.id")
    if coreIdData == nil {
        return false
    }

    // Patch core.id with our version.
    coreIdData.SetString("gocollect", gocollectVersion)

    // Check if we need to register first.
    regid := coreIdData.GetString("regid")
    if regid == "" {
        // Post data, expect {"data":{"regid":"12345"}}.
        result := register(registerUrl, coreIdData, regidFilename)
        if !result {
            return false
        }

        // Re-get core.id data: this time we must have regid or core.id
        // is broken (or the registration helper).
        coreIdData = collectors.Run("core.id")
        if coreIdData == nil {
            return false
        }

        regid = coreIdData.GetString("regid")
        if regid == "" {
            logger.Fatal("No regid after register from core.id")
            return false
        }
    }

    // Run all collectors and push.
    extraContext := map[string]string{"_collector": "<value>"}
    for _, collectorKey := range collectors.Runnable() {
        var collected Collected

        switch collectorKey {
        case "core.id":
            // No need to fetch it again. And besides, we patched it
            // above to contain the version as well.
            collected = coreIdData
        default:
            // Exec the collector.
            collected = collectors.Run(collectorKey)
        }

        if collected == nil {
            //logger.Printf("collector[%s]: exec fail", collectorKey)
            continue
        }

        // We update the pushUrl for every push because the _collector
        // is in it, which changes continuously.
        extraContext["_collector"] = collectorKey
        tmpPushUrl := coreIdData.BuildString(pushUrl, &extraContext)

        push(tmpPushUrl, collected)
    }

    // TODO: call close on DefaultHttpHandler? Also before every return?

    return true
}

func httpPost(url string, data Collected) ([]byte, error) {
    resp, err := http.Post(url, "application/json", data)
    //var resp *http.Response
    //resp, err := nil, errors.New("test")
    //_ = http.Post

    var output []byte
    if resp != nil {
        output, err = ioutil.ReadAll(resp.Body)
        resp.Body.Close()
    } else {
        output = []byte("")
    }

    if err == nil && !(200 <= resp.StatusCode && resp.StatusCode < 400) {
        err = errors.New("non-2xx/3xx status")
    }

    return output, err
}

func register(registerUrl string, coreIdData Collected,
              regidFilename string) bool {
    // Post data, expect {"data":{"regid":"12345"}}.
    data, err := httpPost(registerUrl, coreIdData)
    if err != nil {
        logger.Printf("register[%s]: failed: %s", registerUrl, err)
        return false
    }

    var decoded map[string](map[string]string)
    err = json.Unmarshal(data, &decoded)
    if err != nil {
        logger.Printf("register[%s]: failed: %s", registerUrl, err)
        return false
    }

    value := decoded["data"]["regid"]
    if value == "" {
        logger.Printf("register[%s]: failed: got nothing", registerUrl)
        return false
    }

    os.MkdirAll(path.Dir(regidFilename), 0755)
    err = ioutil.WriteFile(
        "/var/lib/gocollect/core.id.regid", []byte(value), 0400)
    if err != nil {
        logger.Fatal("Could not write core.id.regid: ", err)
        return false
    }

    logger.Printf("register[%s]: got %s", registerUrl, value)
    return true
}

func push(pushUrl string, collectedData Collected) bool {
    data, err := httpPost(pushUrl, collectedData)
    if err != nil {
        logger.Printf("push[%s]: failed: %s", pushUrl, err)
        return false
    }

    logger.Printf("push[%s]: got %s", pushUrl, string(data))
    return true
}
