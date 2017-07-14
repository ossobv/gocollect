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
        'FILE_SUBSCRIBER_AMQP_COLLECTOR_PATH', '/srv/gocollect-data')


def callback(ch, method, properties, body):
    try:
        if isinstance(body, bytes):
            body = body.decode('UTF-8')
        json_body = json.loads(body)

        regid = json_body.get('regid', None)

        if regid is None:
            logger.error('No regid found!!! %s', body)
            return

        # Collect stuff to directory structure.
        collector = MyCollector(
            environ,
            regid,
            json_body.get('collectkey', None),
            json_body.get('seenip', None),
            data=json.dumps(json_body.get('data', {})))
        collector.collect()
    except:  # Never crash
        logger.exception('Problem!')


def main():
    credentials = pika.credentials.PlainCredentials(
        environ.get('FILE_SUBSCRIBER_AMQP_USERNAME'),
        environ.get('FILE_SUBSCRIBER_AMQP_PASSWORD'))

    parameters = pika.ConnectionParameters(
        host=environ.get('FILE_SUBSCRIBER_AMQP_HOST'),
        heartbeat_interval=10,
        virtual_host=environ.get('FILE_SUBSCRIBER_AMQP_VIRTUAL_HOST'),
        credentials=credentials)

    consumer = RMQConsumer(
        parameters,
        callback,
        environ.get('FILE_SUBSCRIBER_AMQP_EXCHANGE_NAME'),
        environ.get('FILE_SUBSCRIBER_AMQP_ROUTING_KEY', '#'),
        environ.get('FILE_SUBSCRIBER_AMQP_QUEUENAME'))

    try:
        logger.info('Started')
        consumer.run()
    except (KeyboardInterrupt, SystemExit):
        consumer.stop()
        logger.info('Exited')
