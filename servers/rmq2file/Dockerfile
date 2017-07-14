FROM ubuntu:xenial

RUN apt-get update \
 && apt-get install -y \
    python-dev \
    python-pip \
    libffi-dev \
    libssl-dev

ADD rmq2file/requirements.txt requirements.txt
RUN pip install -r requirements.txt

RUN mkdir -p /srv/app /srv/gocollect-data
WORKDIR /srv/app
ADD ["rmq2file", "/srv/app/rmq2file"]

CMD ["python", "rmq2file"]
