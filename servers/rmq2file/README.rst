GoCollect RMQ to file service
==================================

Consumes RabbitMQ GoCollect data and writes to a directory/file-based
storage.


Build docker image
------------------

Build in one directory level up::

    docker build --pull -t gocollect-server:latest ..


Configuration
-------------

Place this in ``/etc/docker/containers.d/gocollect-rmq2file.conf``::

    NAME=gocollect-rmq2file
    ARGS="-v /srv/gocollect-data:/srv/gocollect-data:rw \
      -e RMQ2FILE_HOST=IP_HERE \
      -e RMQ2FILE_VIRTUAL_HOST=VH_HERE \
      -e RMQ2FILE_USERNAME=USERNAME_HERE \
      -e RMQ2FILE_PASSWORD=PASSWORD_HERE \
      -e RMQ2FILE_EXCHANGE_NAME=EXCHANGE_HERE \
      -e RMQ2FILE_ROUTING_KEY=# \
      -e RMQ2FILE_QUEUENAME=QUEUENAME_HERE \
      -e RMQ2FILE_COLLECTOR_PATH=/srv/gocollect-data \
      gocollect-server:latest rmq2file"

And use the following *Systemd* template service as
``/etc/systemd/system/docker@.service``::

    [Unit]
    Description=Docker Container: %I
    Documentation=https://www.osso.nl/FIXME

    [Service]
    EnvironmentFile=/etc/docker/containers.d/%i.conf

    Type=simple
    ExecStartPre=-/usr/bin/docker rm $NAME
    ExecStartPre=/usr/bin/docker run -d --name $NAME $ARGS
    ExecStart=/usr/bin/docker logs -f $NAME
    ExecStop=/usr/bin/docker stop $NAME
    ExecStopPost=-/usr/bin/docker stop $NAME
    Restart=always
    RestartSec=5

    [Install]
    WantedBy=multi-user.target

Then start/enable the service as usual::

    systemctl enable docker@gocollect-rmq2file
    systemctl start docker@gocollect-rmq2file

TODO: The canonical *OSSO B.V.* *Systemd* with *Docker* usage should be
specified somewhere else.
