import json
import logging
import pika
from os import environ

from lib.handlers.directory.collector import Collector
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

    except:  # Never crash
        logger.exception('Problem!')


def main():
    credentials = pika.credentials.PlainCredentials(
        environ.get('RMQ2FILE_USERNAME'),
        environ.get('RMQ2FILE_PASSWORD'))

    parameters = pika.ConnectionParameters(
        host=environ.get('RMQ2FILE_HOST'),
        heartbeat_interval=10,
        virtual_host=environ.get('RMQ2FILE_VIRTUAL_HOST'),
        credentials=credentials)

    consumer = RMQConsumer(
        parameters,
        callback,
        environ.get('RMQ2FILE_EXCHANGE_NAME'),
        environ.get('RMQ2FILE_ROUTING_KEY', '#'),
        environ.get('RMQ2FILE_QUEUENAME'))

    try:
        logger.info('Started')
        consumer.run()
    except (KeyboardInterrupt, SystemExit):
        consumer.stop()
        logger.info('Exited')
