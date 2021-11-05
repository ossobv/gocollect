import json
import logging
import pika
from os import environ

from lib.handlers.directory.collector import Collector
from lib.envparse import rmq_uri
from lib.rmq.rmq_consumer import RMQConsumer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MyCollector(Collector):
    """
    Override DATADIR to use our envvar.
    """
    DATADIR = environ.get(
        'RMQ2FILE_COLLECTOR_PATH', '/srv/gocollect-data')


def callback(ch, method, properties, body):
    try:
        if isinstance(body, bytes):
            body = body.decode('utf-8')
        json_body = json.loads(body)

        regid = json_body.get('regid')
        if regid is None:
            logger.error('No regid found!!! %s', body)
            return

        # Collect stuff to directory structure.
        collector = MyCollector(
            regid,
            json_body.get('collectkey'),
            json_body.get('seenip'),
            json.dumps(json_body.get('data', {})))
        collector.collect()

    except Exception:  # Never crash
        logger.exception('Problem!')


def main():
    # rmq://HOST[:PORT]/VIRTUAL_HOST/EXCHANGE[/QUEUE]
    uri = rmq_uri(environ.get('RMQ2FILE_QUEUE_URI', ''))

    credentials = pika.credentials.PlainCredentials(
        uri.username, uri.password)

    parameters = pika.ConnectionParameters(
        host=uri.host, heartbeat_interval=10, virtual_host=uri.vhost,
        credentials=credentials)

    consumer = RMQConsumer(
        parameters, callback, uri.exchange, uri.routing_key, uri.queue)

    try:
        logger.info('Started')
        consumer.run()
    except (KeyboardInterrupt, SystemExit):
        consumer.stop()
        logger.info('Exited')
