FROM ubuntu:noble

RUN apt-get update -q && \
    apt-get install -qqy --no-install-recommends \
      python3-netaddr python3-pika python3-requests && \
    apt-get clean && \
    rm -rf /var/cache/apt /var/lib/apt

# COPY requirements.txt /tmp/requirements.txt
# RUN pip install --break-system-packages -r /tmp/requirements.txt

RUN mkdir -p /app /srv/gocollect-data
WORKDIR /app

ENV PYTHONPATH=/app
COPY ["lib", "/app/lib"]
COPY ["rmq2es", "/app/rmq2es"]
COPY ["rmq2file", "/app/rmq2file"]
COPY ["rmq2nb", "/app/rmq2nb"]
COPY ["wsgi2file", "/app/wsgi2file"]

RUN chmod -R ga-w /app /srv/gocollect-data
USER www-data

ENTRYPOINT ["python3"]
CMD ["-c", "import os;print('\\x0a'.join(sorted(cmd for cmd in os.listdir('/app') if cmd != 'lib')))"]
# run as: gocollect-consumer rmq2file|wsgi2file
