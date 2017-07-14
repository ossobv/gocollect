import pika
from os import environ as env
import json
import logging
from handlers.directory.collector import Collector
from rmq.rmq_consumer import RMQConsumer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        collector = Collector(
            env,
            regid,
            json_body.get('collectkey', None),
            json_body.get('seenip', None),
            data=json.dumps(json_body.get('data', {})))
        collector.collect()
    except Exception as e:  # Never crash
        logger.error(e.message, exc_info=True)


def main():
    parameters = pika.ConnectionParameters(
        host=env.get('FILE_SUBSCRIBER_AMQP_HOST', None),
        heartbeat_interval=10,
        virtual_host=env.get('FILE_SUBSCRIBER_AMQP_VIRTUAL_HOST', None),
        credentials=pika.credentials.PlainCredentials(
            env.get('FILE_SUBSCRIBER_AMQP_USERNAME', None),
            env.get('FILE_SUBSCRIBER_AMQP_PASSWORD', None)))

    consumer = RMQConsumer(
        parameters,
        callback,
        env.get('FILE_SUBSCRIBER_AMQP_EXCHANGE_NAME', None),
        env.get('FILE_SUBSCRIBER_AMQP_ROUTING_KEY', '#'),
        env.get('FILE_SUBSCRIBER_AMQP_QUEUENAME', None))
    try:
        logger.info('Started')
        consumer.run()
    except KeyboardInterrupt:
        consumer.stop()
        logger.info('Exited')
