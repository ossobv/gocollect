GoCollect RMQ to Elasticsearch service
======================================

Consumes RabbitMQ GoCollect data and writes to a Elasticsearch storage.


Build docker image
------------------

Build in one directory level up::

    docker build --pull -t gocollect-srv:latest .


Configuration
-------------

Place this in ``/etc/docker/containers.d/gocollect-rmq2es.conf``::

    # systemd-env-file: Use quotes. Use backslashes.
    NAME=gocollect-rmq2es
    ARGS="-v /srv/gocollect-data:/srv/gocollect-data:rw \
        gocollect-srv:latest rmq2es"

Place this in ``/etc/docker/containers.d/gocollect-rmq2es.env``::

    # docker-env-file: Don't use quotes. Don't try line feeds.
    NAME=gocollect-rmq2es
    RMQ2ES_RMQ_URI=rmq://user:pass@host/vhost/exchange/queue
    RMQ2ES_ES_URI=https://user:password@host/index_name

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

    systemctl enable docker@gocollect-rmq2es
    systemctl start docker@gocollect-rmq2es

TODO: The canonical *OSSO B.V.* *Systemd* with *Docker* usage should be
specified somewhere else.


Elasticsearch mapping
---------------------

Create the Elasticsearch index with the mapping from ``mapping.json``::

    curl -X PUT https://user:pass@host/index --data-binary @mapping.json
      -H 'Content-Type: application/json'
