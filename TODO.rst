TODO list
---------

Doing now:

- [server] Network whitelist.
- [server] Consolidate Jelle-code, RabbitMQ-code into this repo. Partially
  completed by moving the rmq2file here.

Not doing now:

- [docs] Docs from manpage into README. More docs about installing on
  non-standard systems through make tgz.
- [client] Fix so the installer prefers /usr/local by default.
- [client] Optional background job for pushing authlogs?
  ``journalctl -f -l SYSLOG_FACILITY=4 -o json``
- [client] Inotify (or similar) to watch changes.
- [packaging] Redo debian-depends makefile helpers. More automation.

Not doing ever:

- [client] Variable random extra sleep. It's preferable to know when to expect
  updates over easing (the little extra) load on the servers.
