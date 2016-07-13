# This file is part of GoCollect as a means to lock the APT/DPKG databases.
#
# [dpkg:doc/frontend.txt]
# Any frontend needing to make sure no write operation is currently happening,
# should lock the dpkg database by locking the file '<admindir>/lock' using
# file record locks (i.e. fcntl(2) advisory locking). The whole file should
# be locked, as that's the most portable way to perform this operation; this
# can be achieved by using start=0, len=0 and whence=SEEK_SET.
#
# Usage:
#
#   python lockf.py TIMEOUT LOCKFILES...
#   # fcntl F_SETLK(W) locks all the LOCKFILES
#   # then writes "LOCKED" to stdout
#   # it exits when its stdout is closed (i.e. when the destination pipe
#   # is done)
#
# Example:
#
#   python lockf.py 120 /var/lib/dpkg/lock |
#   while read x; do
#       # do stuff with /var/lib/dpkg/lock locked
#       exit 64
#   done
#   ret=$?  # 0=timeout, 64=locked and processed
#
import fcntl, signal, select, sys
signal.signal(signal.SIGALRM, (lambda *x, **y: None))
signal.alarm(int(sys.argv[1]))
for filename in sys.argv[2:]:
    fp = open(filename, 'w')
    fcntl.lockf(fp.fileno(), fcntl.LOCK_EX)  # LOCK_SH gives EBADF?
signal.alarm(0)
sys.stdout.write('LOCKED\n')
sys.stdout.flush()
outfp = sys.stdout.fileno()
ret = select.select([outfp], [], [outfp])  # wait for stdout close
