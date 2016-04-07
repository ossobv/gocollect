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

Short todo:

- dmidecode output (go or awk?, if go then we must allow lots of other
  collectors to be go-ified as well)

Long todo:

- network-whitelist on the REST server
- redo debian-depends stuff
- add manpage


Packaging for Debian
--------------------

.. code-block:: console

    $ sudo apt-get install git-buildpackage dh-make dh-systemd

    $ cat > .git/gbp.conf << EOF
    [DEFAULT]
    upstream-branch=master
    debian-branch=debian/jessie

    [buildpackage]
    upstream-tag = v%(version)s
    EOF

    $ git checkout debian/jessie
    $ gbp buildpackage --git-ignore-new -us -uc -sa


Golang notes to self
--------------------

- https://golang.org/doc/code.html
- http://openmymind.net/
