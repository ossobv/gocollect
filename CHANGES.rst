Changes
-------

* v0.5.X [XXXXXXXXXX]:

  - core: Added 'api_key' key in the config file to set the API key to
    authenticate to the collector server.
  - core: Added 'include' directive in the config file (no globbing) to
    include single files like /etc/gocollect.conf.local.
  - core: Force really-really static go executable.

  - release: Experiment with increasing version numbers for releases of
    the same build on different operating system versions.

  - os.distro: Prefer os-release over lsb_release parsing.
  - os.storage: Reduce fluctuating listings (zfs, magicfs, tmpfs).

* v0.4.0 [2016-09-28]: The initial real release used in production.
