Changes
-------

* v0.7.3 [2019-06-03]:

  - core.id: Fix incorrect ip4 in core.id newer platforms.

* v0.7.2 [2019-05-10]:

  - core.id: Fix blank ip4 in core.id on platforms with sed 4.4+.
  - core.meta: Check for core.meta yaml files in path relative to the config
    file location: /etc/gocollect.conf -> /etc + ./gocollect/core.meta/

* v0.7.1 [2019-04-11]:

  - os.keys: Fix broken json when comments contained double quotes.

* v0.7.0 [2018-11-08]:

  - logs: Clarify that the bracketed things are urls.

  - app.lshw: Return "{}" when lshw(1) is not installed.
  - core.meta: Don't push the empty string.
  - os.distro: Cope with alternate Cumulus Linux os-release format.
  - os.keys: For older ssh-keygen output, add the comment back in
  - sys.cpu: Collect CPU vulns in sys.cpu.

* v0.6.0 [2017-09-21]:

  - build: Fix so 'go get' works. Note that you'll have to use a
    "proper" GOPATH now; even for debian builds.
  - cli: Add -k option to dump collector output to stdout.
  - config: Fix _regid/regid confusion in config file.
  - misc: A bunch of refactoring.

  - core.id: Fall back to hostname without -f if there is no FQDN.
  - core.meta: Make it a builtin (won't work in gocollect-fallback). Now
    it reads ``/var/lib/gocollect/core.meta.js`` if it exists. Or it
    reads ``/etc/gocollect/core.meta/*.yaml`` if they exist.

* v0.5.0 [2017-01-19]:

  - core: Added 'api_key' key in the config file to set the API key to
    authenticate to the collector server.
  - core: Added 'include' directive in the config file (no globbing) to
    include single files like /etc/gocollect.conf.local.
  - core: Force really-really static go executable.

  - release: Experiment with increasing version numbers for releases of
    the same build on different operating system versions.

  - core.meta: Add optional custom (node-specific) data to be passed.
  - os.distro: Prefer os-release over lsb_release parsing.
  - os.storage: Reduce fluctuating listings (zfs, magicfs, tmpfs).
  - app.lshw: Mask out the CPU clock speed that fluctuates.

* v0.4.0 [2016-09-28]: The initial real release used in production.
