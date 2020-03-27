package signal

import (
	"fmt"
	"os"
	"syscall"
)

// Alarm sets up a timer so a SIGALRM signal is fired after 'seconds'
// seconds.
func Alarm(seconds int) {
	if seconds < 0 || seconds > 86400 {
		fmt.Fprintf(os.Stderr,
			"ERR: Invalid value passed to Alarm()\n")
		return
	}

	_, _, err := syscall.RawSyscall(syscall.SYS_ALARM, uintptr(seconds), 0, 0)
	if err != 0 {
		fmt.Fprintf(os.Stderr,
			"ERR: syscall.RawSyscall(SYS_ALARM, ...) returned %d\n", err)
	}
}
