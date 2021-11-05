GoCollect RMQ to Netbox service
===============================

Consumes RabbitMQ GoCollect data and writes to a Netbox storage.


Build docker image
------------------

Build in one directory level up::

    docker build --pull -t gocollect-srv:latest .


Configuration
-------------

Create `Device Role`, `Device Type`, `Site` and `Cluster` records in
netbox which will be used as the defaults for gocollect nodes. Place
their ID's in the `gocollect-rmq2nb.env` below.

Place this in ``/etc/docker/containers.d/gocollect-rmq2nb.conf``::

    # systemd-env-file: Use quotes. Use backslashes.
    NAME=gocollect-rmq2nb
    ARGS="-v /srv/gocollect-data:/srv/gocollect-data:rw \
        gocollect-srv:latest rmq2nb"

Place this in ``/etc/docker/containers.d/gocollect-rmq2nb.env``::

    # docker-env-file: Don't use quotes. Don't try line feeds.
    NAME=gocollect-rmq2nb
    RMQ2ES_RMQ_URI=rmq://user:pass@host/vhost/exchange/queue
    RMQ2NB_NB_URI=https://user:token@host/
    # Configure the Device/VM defaults.
    RMQ2NB_NB_DEVICE_ROLE_ID=1
    RMQ2NB_NB_DEVICE_TYPE_ID=1
    RMQ2NB_NB_SITE_ID=1
    RMQ2NB_NB_VM_CLUSTER_ID=1
    # Separate roles with whitespace, partial matches are supported.
    RMQ2NB_NB_ROLES_SKIP_INTERFACES=
    RMQ2NB_LOGLEVEL=INFO
    # Test gocollect id and fqdn matching without writing to netbox.
    RMQ2NB_DRY_RUN=true

And use the following *Systemd* template service as
``/etc/systemd/system/docker@.service``::

    [Unit]
    Description=Docker Container: %i
    After=docker.service
    Requires=docker.service

    [Service]
    EnvironmentFile=/etc/docker/containers.d/%i.conf
    Type=simple
    ExecStartPre=-/usr/bin/docker rm %i
    ExecStartPre=/usr/bin/docker run -d --name %i --env-file /etc/docker/containers.d/%i.env $ARGS
    ExecStart=/usr/bin/docker logs -f %i
    ExecStop=/usr/bin/docker stop %i
    ExecStopPost=-/usr/bin/docker stop %i
    Restart=always
    RestartSec=5

    [Install]
    WantedBy=multi-user.target

Then start/enable the service as usual::

    systemctl enable docker@gocollect-rmq2nb
    systemctl start docker@gocollect-rmq2nb

TODO: The canonical *OSSO B.V.* *Systemd* with *Docker* usage should be
specified somewhere else.
