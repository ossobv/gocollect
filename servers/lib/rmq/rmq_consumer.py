import logging
import pika

logger = logging.getLogger(__name__)


class RMQConsumer(object):
    def __init__(
            self, parameters, callback, exchange_name, routing_key,
            queue=None):
        self._connection = None
        self._channel = None
        self._queue = queue
        self._closing = False
        self._consumer_tag = None
        self._parameters = parameters
        self._callback = callback
        self._routing_key = routing_key
        self._exchange_name = exchange_name

    def connect(self):
        logger.info('Connecting to %s', self._parameters)
        return pika.SelectConnection(
            parameters=self._parameters,
            on_open_callback=self.on_connection_open,
            stop_ioloop_on_close=False)

    def on_connection_open(self, unused_connection):
        logger.info('Connection opened')
        self.add_on_connection_close_callback()
        self.open_channel()

    def add_on_connection_close_callback(self):
        logger.info('Adding connection close callback')
        self._connection.add_on_close_callback(self.on_connection_closed)

    def on_connection_closed(self, connection, reply_code, reply_text):
        self._channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            logger.warning(
                'Connection closed, reopening in 5 seconds: (%s) %s',
                reply_code, reply_text)
            self._connection.add_timeout(5, self.reconnect)

    def reconnect(self):
        # This is the old connection IOLoop instance, stop its ioloop
        self._connection.ioloop.stop()

        if not self._closing:
            # Create a new connection
            self._connection = self.connect()

            # There is now a new connection, needs a new ioloop to run
            self._connection.ioloop.start()

    def open_channel(self):
        logger.info('Creating a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        logger.info('Channel opened')
        channel.basic_qos(prefetch_count=1)
        self._channel = channel
        self.add_on_channel_close_callback()
        # self.setup_exchange(self.EXCHANGE)
        self.setup_queue()

    def add_on_channel_close_callback(self):
        logger.info('Adding channel close callback')
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reply_code, reply_text):
        logger.warning('Channel %i was closed: (%s) %s',
                       channel, reply_code, reply_text)
        self._connection.close()

    def setup_exchange(self, exchange_name):
        logger.info('Declaring exchange %s', exchange_name)

    def on_exchange_declareok(self, unused_frame):
        logger.info('Exchange declared')
        self.setup_queue(self._queue)

    def setup_queue(self):
        logger.info('Declaring queue')
        self._channel.queue_declare(
            self.on_queue_declareok,
            queue=self._queue,
            durable=True,
            exclusive=False)

    def on_queue_declareok(self, queue):
        self._queue = queue.method.queue
        logger.info(
            'Binding %s to %s with %s', self._exchange_name,
            self._queue, self._routing_key)

        self._channel.queue_bind(
            self.on_bindok,
            exchange=self._exchange_name,
            queue=self._queue,
            routing_key=self._routing_key)

    def on_bindok(self, unused_frame):
        logger.info('Queue bound')
        self.start_consuming()

    def start_consuming(self):
        self.add_on_cancel_callback()
        self._consumer_tag = self._channel.basic_consume(
            self.on_message, self._queue)
        logger.info('Ready for consuming')

    def add_on_cancel_callback(self):
        logger.info('Adding consumer cancellation callback')
        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)

    def on_consumer_cancelled(self, method_frame):
        logger.info('Consumer was cancelled remotely, shutting down: %r',
                    method_frame)
        if self._channel:
            self._channel.close()

    def on_message(self, ch, method, properties, body):
        # logger.info(
        #     'Received message # %s from %s', method.delivery_tag,
        #     properties.app_id)

        if self._callback:
            self._callback(ch, method, properties, body)
        self.acknowledge_message(method.delivery_tag)

    def acknowledge_message(self, delivery_tag):
        # logger.info('Acknowledging message %s', delivery_tag)
        self._channel.basic_ack(delivery_tag)

    def stop_consuming(self):
        if self._channel:
            logger.info('Sending a Basic.Cancel RPC command to RabbitMQ')
            self._channel.basic_cancel(self.on_cancelok, self._consumer_tag)

    def on_cancelok(self, unused_frame):
        logger.info('RabbitMQ acknowledged the cancellation of the consumer')
        self.close_channel()

    def close_channel(self):
        logger.info('Closing the channel')
        self._channel.close()

    def run(self):
        self._connection = self.connect()
        self._connection.ioloop.start()

    def stop(self):
        logger.info('Stopping')
        self._closing = True
        self.stop_consuming()
        self._connection.ioloop.start()
        logger.info('Stopped')

    def close_connection(self):
        logger.info('Closing connection')
        self._connection.close()
