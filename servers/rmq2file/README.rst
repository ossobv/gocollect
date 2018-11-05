GoCollect RMQ to file service
==================================

Consumes RabbitMQ GoCollect data and writes to a directory/file-based
storage.


Build docker image
------------------

Build in one directory level up::

    docker build --pull -t gocollect-srv:latest .


Configuration
-------------

Place this in ``/etc/docker/containers.d/gocollect-srv-rmq2file.conf``::

    NAME=gocollect-srv-rmq2file
    ARGS="-v /srv/gocollect-data:/srv/gocollect-data:rw \
      -e RMQ2FILE_QUEUE_URI=rmq://user:pass@host/vhost/exchange/queue \
      -e RMQ2FILE_COLLECTOR_PATH=/srv/gocollect-data \
      gocollect-srv:latest rmq2file"

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

    systemctl enable docker@gocollect-srv-rmq2file
    systemctl start docker@gocollect-srv-rmq2file

TODO: The canonical *OSSO B.V.* *Systemd* with *Docker* usage should be
specified somewhere else.
