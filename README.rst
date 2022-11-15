|GoCollect|
===========

|bettercodehub| |goreportcard|

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

    go get github.com/ossobv/go-getopt

Possibly set env to old style module handling::

    # go.mod file not found in current directory or any parent directory...
    go env -w GO111MODULE=off  # sets ~/.config/go/env: GO111MODULE=off


Packaging for Debian
--------------------

Prerequisites:

.. code-block:: console

    $ sudo apt-get install git-buildpackage dh-make dh-systemd

Optional:

.. code-block:: console

    $ cat > .git/gbp.conf << EOF
    [DEFAULT]
    upstream-branch=main
    debian-branch=debian

    [buildpackage]
    upstream-tag = v%(version)s
    EOF

Running:

.. code-block:: console

    $ git checkout debian
    $ gbp buildpackage -sa \
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

    $ cd gocollect-client
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
<https://github.com/ossobv/gocollect/blob/main/LICENSE>`_.

The artwork |--| the GoCollect logo |--| is licensed according to the
*Attribution-NonCommercial-ShareAlike 4.0 International* Creative Commons
license (CC BY-NC-SA 4.0);
see `LICENSE.CC.BY-NC-SA.4-0.txt
<https://github.com/ossobv/gocollect/blob/main/artwork/LICENSE.CC.BY-NC-SA.4-0.txt>`_.



.. |GoCollect| image:: https://raw.githubusercontent.com/ossobv/gocollect/main/gocollect.png
    :alt: GoCollect
.. |bettercodehub| image:: https://bettercodehub.com/edge/badge/ossobv/gocollect
.. |goreportcard| image:: https://goreportcard.com/badge/github.com/ossobv/gocollect
    :target: https://goreportcard.com/report/github.com/ossobv/gocollect
.. |--| unicode:: U+2013   .. en dash
