GoCollect RMQ to file service
==============================

Consumes RabbitMQ GoCollect data and writes to a directory/file-based
storage.


Build docker image
------------------

::

    docker build -f Dockerfile -t gocollect-rmq2file:latest ..


Configuration
-------------

Place this in ``/etc/docker/containers.d/gocollect-rmq2file.conf``::

    NAME=gocollect-rmq2file
    ARGS="-v /srv/gocollect-data:/srv/gocollect-data:rw \
      -e FILE_SUBSCRIBER_AMQP_HOST=IP_HERE \
      -e FILE_SUBSCRIBER_AMQP_VIRTUAL_HOST=VH_HERE \
      -e FILE_SUBSCRIBER_AMQP_USERNAME=USERNAME_HERE \
      -e FILE_SUBSCRIBER_AMQP_PASSWORD=PASSWORD_HERE \
      -e FILE_SUBSCRIBER_AMQP_EXCHANGE_NAME=EXCHANGE_HERE \
      -e FILE_SUBSCRIBER_AMQP_ROUTING_KEY=# \
      -e FILE_SUBSCRIBER_AMQP_QUEUENAME=QUEUENAME_HERE \
      -e FILE_SUBSCRIBER_AMQP_COLLECTOR_PATH=/srv/gocollect-data \
      gocollect-rmq2file:latest"

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
