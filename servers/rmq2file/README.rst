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
      -e RMQ2FILE_LOGLEVEL=INFO \
      -e RMQ2FILE_IDLE_TIMEOUT=1800 \
      gocollect-srv:latest rmq2file"

``RMQ2FILE_IDLE_TIMEOUT`` (default 1800, 0 disables) forces a
reconnect when no message was received for that many seconds.

The consumer reconnects by itself on connection loss. If the main loop
blocks for more than 5 minutes (e.g. a hanging filesystem), it exits
with status 1 so the supervisor can restart it.

Every 5 minutes it logs how many messages it received and how many
consumers the queue has. **There should be only one consumer per
queue.** If there are more, RabbitMQ round-robins the messages between
them, and each consumer sees only a part of them. Every service
(rmq2file, rmq2es, rmq2nb) needs its *own* queue on the exchange. When
no queue is set in the URI, it defaults to ``ha.EXCHANGE``, which is
the same for every service. Check with::

    rabbitmqctl list_queues -p VHOST name messages consumers
    rabbitmqctl list_consumers -p VHOST

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
