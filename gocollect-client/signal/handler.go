package signal

import (
	"os"
	"os/signal"
	"syscall"
)

const (
	// MAXSIG is the largest number of non-realtime signals (on Linux).
	// 32..64 are realtime signals and irrelevant to us at this point.
	MAXSIG = 31
)

// Handler is used to handle the handle INT, TERM and CHLD signals.
type Handler struct {
	Chan chan os.Signal
}

// New initializes the signal handlers.  We now get events for all
// signals.  Read the Handler.Chan and handle them appropriately.
func New() Handler {
	signalChan := make(chan os.Signal, 1)
	for i := 1; i <= MAXSIG; i++ {
		signal.Notify(signalChan, syscall.Signal(i))
	}
	return Handler{Chan: signalChan}
}

// NewAlarmHupUsr1 initializes signal handlers for ALRM, HUP and USR1.
// Read the Handler.Chan and handle them appropriately.
func NewAlarmHupUsr1() Handler {
	signalChan := make(chan os.Signal, 1)
	signal.Notify(signalChan, syscall.SIGALRM)
	signal.Notify(signalChan, syscall.SIGHUP)
	signal.Notify(signalChan, syscall.SIGUSR1)
	return Handler{Chan: signalChan}
}
