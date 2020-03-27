package signal

import (
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func ExampleAlarm() {
	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs, syscall.Signal(syscall.SIGALRM))

	Alarm(1)

	t0 := time.Now().Unix()
	fmt.Println("... do work here ...")

	sig := <-sigs // wait for SIGALRM
	fmt.Printf("Got '%s' after %ds\n", sig.String(), time.Now().Unix()-t0)
	// Output: ... do work here ...
	// Got 'alarm clock' after 1s
}
