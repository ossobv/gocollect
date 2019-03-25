FROM ubuntu:xenial

RUN apt-get update -q && \
    apt-get install -qqy --no-install-recommends \
      python-dev python-pip libffi-dev libssl-dev

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

RUN mkdir -p /app /srv/gocollect-data
WORKDIR /app

ENV PYTHONPATH /app
COPY ["lib", "/app/lib"]
COPY ["rmq2file", "/app/rmq2file"]
COPY ["wsgi2file", "/app/wsgi2file"]

RUN chmod -R ga-w /app /srv/gocollect-data
USER www-data

ENTRYPOINT ["python"]
CMD ["-c", "import os;print('\\x0a'.join(sorted(os.listdir('/app'))))"]
# run as: gocollect-consumer rmq2file|wsgi2file
