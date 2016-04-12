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

- network-whitelist on the REST server
- redo debian-depends stuff
- add manpage


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

(Note that rcX versions must be tagged as ``v1.2_rc3`` where in Debian
the underscore is a tilde.)



Golang notes to self
--------------------

- https://golang.org/doc/code.html
- http://openmymind.net/
