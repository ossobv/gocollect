.. image:: https://raw.githubusercontent.com/ossobv/gocollect/master/artwork/gocollect-logo/horizontal_color.png
    :alt: GoCollect

----

.. image:: https://goreportcard.com/badge/github.com/ossobv/gocollect
    :target: https://goreportcard.com/report/github.com/ossobv/gocollect
.. image:: https://bettercodehub.com/edge/badge/ossobv/gocollect

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

    mkdir -p ~/go
    export GOPATH=~/go

And check this out inside that::

    git clone https://github.com/ossobv/gocollect \
      $GOPATH/src/github.com/ossobv/gocollect

And install prerequisites::

    go get github.com/kesselborn/go-getopt


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

Note that release candidate versions must be tagged as ``v1.2_rc3``.
gbp-buildpackage rewrites the underscore to a debian-style tilde.
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
- https://jamescun.com/golang/binary-size/


License
-------

The source code is licensed according to the GNU GPLv3+;
see `LICENSE
<https://github.com/ossobv/gocollect/blob/master/LICENSE>`_.

The artwork -- the GoCollect logo -- is licensed according to the
*Attribution-NonCommercial-ShareAlike 4.0 International* Creative Commons
license (CC BY-NC-SA 4.0);
see `LICENSE.CC.BY-NC-SA.4-0.txt
<https://github.com/ossobv/gocollect/blob/master/artwork/LICENSE.CC.BY-NC-SA.4-0.txt>`_.
