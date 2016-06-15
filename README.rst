GoCollect
=========

GoCollect collects various pieces of system info and publishes them to a
central server.

The intent of GoCollect is to create a map of your servers with slow and
never changing data items. Where you may use Zabbix for semi-realtime
monitoring of integer values like current CPU usage, *you use GoCollect
to collect values like hard drive serial numbers, IPMI IP-addresses and
versions of installed OS packages.*


Installing
----------

::

    make && make install
    cp /etc/gocollect.conf.sample /etc/gocollect.conf
    # edit /etc/gocollect.conf
    # then start/restart gocollect using your favorite init method

You may need to set up a go path first::

    mkdir -p ~/.local/go
    export GOPATH=~/.local/go

And install prerequisites::

    go get github.com/kesselborn/go-getopt


TODO list
---------

Doing now:

- [client] Add manpage.
- [packaging] Have gocollect packages depend on same-version-of-gocollect-or-higher?
- [packaging] Redo debian-depends makefile helpers. More automation.
- [server] Network whitelist.
- [server] Consolidate Jelle-code, RabbitMQ-code into this repo.

Not doing now:

- [client] Optional background job for pushing authlogs?
  ``journalctl -f -l SYSLOG_FACILITY=4 -o json``
- [client] Inotify (or similar) to watch changes.

Not doing ever:

- [client] Variable random extra sleep. It's preferable to know when to expect
  updates over easing (the little extra) load on the servers.


Packaging for Debian
--------------------

Prerequisites:

.. code-block:: console

    $ sudo apt-get install git-buildpackage dh-make dh-systemd

Optional:

.. code-block:: console

    $ cat > .git/gbp.conf << EOF
    [DEFAULT]
    upstream-branch=master
    debian-branch=debian

    [buildpackage]
    upstream-tag = v%(version)s
    EOF

Running:

.. code-block:: console

    $ git checkout debian
    $ gbp buildpackage -us -uc -sa \
        --git-debian-branch=debian --git-upstream-tag='v%(version)s'

Note that release candidate versions must be tagged as ``v1.2_rc3``
where in gbp rewrites the underscore is rewritten to a tilde.
Pre-release development versions shall be called ``v1.3_dev`` which
sorts before ``v1.3_rc1``, which in turn sorts before ``v1.3``.


Packaging a tarball
-------------------

To to create a tarball with the latest version, including a config file,
do this:

.. code-block:: console

    $ TGZ_CONFIG=/path/to/gocollect.conf make tgz
    ...
    Created: gocollect-v0.4~rc6+1.g83d4-md5conf-c0f48c3.tar.gz

You can then extract and run that archive on the target machine like
this:

.. code-block:: console

    $ cat gocollect-v0.4~rc6+1.g83d4-md5conf-c0f48c3.tar.gz | sudo tar -xzvC /
    $ sudo /etc/init.d/gocollect start

You may need to install additional dependencies first to get all
collectors to work properly. For example ``smartmontools`` or
``ipmitool``.


Golang notes to self
--------------------

- https://golang.org/doc/code.html
- http://openmymind.net/
