import logging
import os
import threading
import time

import pika

logger = logging.getLogger(__name__)


class RMQConsumer(object):
    """
    Asynchronous (SelectConnection) RabbitMQ consumer that keeps running.

    - Any connection loss (socket error, missed heartbeats, broker
      Connection.Close, consumer cancel) makes the ioloop stop; run()
      then reconnects with a backoff of RECONNECT_MIN..RECONNECT_MAX
      seconds.
    - If no message was received for idle_timeout seconds while we were
      consuming, we force a reconnect: a consumer that is connected but
      gets no messages is either idle or silently broken; a reconnect is
      cheap either way.
    - A watchdog thread kills the process (exit 1, the supervisor should
      restart us) if the ioloop has not ticked for STALL_TIMEOUT seconds:
      something is blocking (a hanging callback or a hanging filesystem).
    - Every STATS_INTERVAL seconds we log how many messages we got and
      how many consumers the queue has. More than one consumer means
      RabbitMQ round-robins the messages between them, so we only get a
      part of them.
    """
    RECONNECT_MIN = 5
    RECONNECT_MAX = 60
    TICK_INTERVAL = 10
    STALL_TIMEOUT = 300
    STATS_INTERVAL = 300
    STOP_TIMEOUT = 5

    def __init__(
            self, parameters, callback, exchange_name, routing_key,
            queue=None, idle_timeout=None):
        self._connection = None
        self._channel = None
        self._queue = queue
        self._closing = False
        self._consuming = False
        self._consumer_tag = None
        self._parameters = parameters
        self._callback = callback
        self._routing_key = routing_key
        self._exchange_name = exchange_name

        self._idle_timeout = idle_timeout or None
        self._last_tick = time.monotonic()
        self._last_message = time.monotonic()
        self._msgs_since_stats = 0
        self._watchdog = None

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        self._start_watchdog()
        backoff = self.RECONNECT_MIN
        while not self._closing:
            self._consuming = False
            self._connection = self.connect()
            try:
                self._connection.ioloop.start()
            finally:
                self._consuming = False
            # Stopped normally (not by an exception, like
            # KeyboardInterrupt, after which stop() still needs the
            # ioloop). Release its resources before making a new one.
            self._connection.ioloop.close()

            if self._closing:
                break

            if self._consumer_tag is not None:
                # We got as far as consuming: reset the backoff.
                backoff = self.RECONNECT_MIN
            self._consumer_tag = None

            logger.warning('Reconnecting in %d seconds', backoff)
            self._sleep(backoff)
            backoff = min(backoff * 2, self.RECONNECT_MAX)

    def _sleep(self, seconds):
        # Sleep, but keep the watchdog happy.
        end = time.monotonic() + seconds
        while not self._closing:
            self._last_tick = time.monotonic()
            left = end - self._last_tick
            if left <= 0:
                break
            time.sleep(min(left, self.TICK_INTERVAL))

    def stop(self):
        logger.info('Stopping')
        self._closing = True
        conn = self._connection
        if conn is None or conn.is_closed:
            logger.info('Stopped')
            return
        if self._channel and self._channel.is_open and self._consumer_tag:
            self.stop_consuming()
        elif not conn.is_closing:
            conn.close()
        # Don't wait forever for an unresponsive broker.
        conn.ioloop.call_later(self.STOP_TIMEOUT, self._on_stop_timeout)
        conn.ioloop.start()  # until on_connection_closed stops it
        logger.info('Stopped')

    def _on_stop_timeout(self):
        logger.warning('Broker did not respond in time; stopping anyway')
        self._connection.ioloop.stop()

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self):
        logger.info('Connecting to %s', self._parameters)
        return pika.SelectConnection(
            parameters=self._parameters,
            on_open_callback=self.on_connection_open,
            on_open_error_callback=self.on_connection_open_error,
            on_close_callback=self.on_connection_closed)

    def on_connection_open(self, connection):
        logger.info('Connection opened')
        self._last_tick = time.monotonic()
        connection.ioloop.call_later(self.TICK_INTERVAL, self._tick)
        connection.ioloop.call_later(self.STATS_INTERVAL, self._stats)
        self.open_channel()

    def on_connection_open_error(self, connection, err):
        logger.error('Connection open failed: %r', err)
        connection.ioloop.stop()

    def on_connection_closed(self, connection, reason):
        self._channel = None
        if self._closing:
            logger.info('Connection closed: %s', reason)
        else:
            logger.warning('Connection closed: %s', reason)
        connection.ioloop.stop()

    def close_connection(self):
        conn = self._connection
        if conn and not (conn.is_closing or conn.is_closed):
            logger.info('Closing connection')
            conn.close()

    # ------------------------------------------------------------------
    # Channel/queue setup
    # ------------------------------------------------------------------

    def open_channel(self):
        logger.info('Creating a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        logger.info('Channel opened')
        channel.basic_qos(prefetch_count=1)
        self._channel = channel
        channel.add_on_close_callback(self.on_channel_closed)
        self.setup_queue()

    def on_channel_closed(self, channel, reason):
        logger.warning('Channel %i was closed: %s', channel, reason)
        self._channel = None
        self._consuming = False
        # Closing the channel by itself does not help us: drop the
        # connection so run() can start over.
        self.close_connection()

    def setup_queue(self):
        logger.info('Declaring queue %s', self._queue)
        self._channel.queue_declare(
            queue=self._queue,
            callback=self.on_queue_declareok,
            durable=True,
            exclusive=False)

    def on_queue_declareok(self, frame):
        self._queue = frame.method.queue
        logger.info(
            'Queue %s has %d messages and %d other consumers',
            self._queue, frame.method.message_count,
            frame.method.consumer_count)
        if frame.method.consumer_count:
            logger.warning(
                'Queue %s already has %d consumer(s)! RabbitMQ will '
                'round-robin the messages between us and them, so we '
                'will NOT see all messages',
                self._queue, frame.method.consumer_count)

        logger.info(
            'Binding %s to %s with %s', self._exchange_name,
            self._queue, self._routing_key)
        self._channel.queue_bind(
            queue=self._queue,
            exchange=self._exchange_name,
            routing_key=self._routing_key,
            callback=self.on_bindok)

    def on_bindok(self, unused_frame):
        logger.info('Queue bound')
        self.start_consuming()

    # ------------------------------------------------------------------
    # Consuming
    # ------------------------------------------------------------------

    def start_consuming(self):
        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)
        self._consumer_tag = self._channel.basic_consume(
            queue=self._queue,
            on_message_callback=self.on_message)
        self._consuming = True
        self._last_message = time.monotonic()  # idle counts from here
        logger.info('Ready for consuming')

    def on_consumer_cancelled(self, method_frame):
        logger.warning(
            'Consumer was cancelled remotely: %r', method_frame)
        self._consuming = False
        if self._channel and self._channel.is_open:
            self._channel.close()

    def on_message(self, ch, method, properties, body):
        logger.debug(
            'Received message # %s from %s: %r (maybe trunc)',
            method.delivery_tag, properties.app_id, body[0:100])
        self._last_message = time.monotonic()
        self._msgs_since_stats += 1
        if self._callback:
            self._callback(ch, method, properties, body)
        self.acknowledge_message(method.delivery_tag)

    def acknowledge_message(self, delivery_tag):
        self._channel.basic_ack(delivery_tag)

    def stop_consuming(self):
        if self._channel:
            logger.info('Sending a Basic.Cancel RPC command to RabbitMQ')
            self._channel.basic_cancel(
                consumer_tag=self._consumer_tag,
                callback=self.on_cancelok)

    def on_cancelok(self, unused_frame):
        logger.info('RabbitMQ acknowledged the cancellation of the consumer')
        self.close_channel()

    def close_channel(self):
        logger.info('Closing the channel')
        self._channel.close()

    # ------------------------------------------------------------------
    # Liveness
    # ------------------------------------------------------------------

    def _tick(self):
        # Runs in the ioloop. Proves to the watchdog that the ioloop is
        # not blocked, and checks for idleness.
        self._last_tick = time.monotonic()
        idle = self._last_tick - self._last_message
        if (self._idle_timeout and self._consuming
                and idle > self._idle_timeout):
            logger.warning(
                'No messages received for %d seconds; forcing reconnect',
                idle)
            self._consuming = False
            self.close_connection()
            return  # no new tick needed, the connection goes away
        self._connection.ioloop.call_later(self.TICK_INTERVAL, self._tick)

    def _stats(self):
        logger.info(
            'Received %d messages in the last %d seconds',
            self._msgs_since_stats, self.STATS_INTERVAL)
        self._msgs_since_stats = 0
        if self._channel and self._channel.is_open and self._consuming:
            self._channel.queue_declare(
                queue=self._queue, passive=True, callback=self._on_stats)
        self._connection.ioloop.call_later(self.STATS_INTERVAL, self._stats)

    def _on_stats(self, frame):
        # consumer_count includes us.
        if frame.method.consumer_count > 1:
            logger.warning(
                'Queue %s has %d consumers (we are one of them); we only '
                'get a share of the messages', self._queue,
                frame.method.consumer_count)
        else:
            logger.info(
                'Queue %s has %d messages ready and %d consumer(s)',
                self._queue, frame.method.message_count,
                frame.method.consumer_count)

    def _start_watchdog(self):
        if self._watchdog is not None:
            return

        def watchdog():
            while not self._closing:
                time.sleep(self.TICK_INTERVAL)
                stalled = time.monotonic() - self._last_tick
                if stalled > self.STALL_TIMEOUT and not self._closing:
                    logger.critical(
                        'Main loop stalled for %d seconds; exiting so we '
                        'can be restarted', stalled)
                    logging.shutdown()
                    os._exit(1)

        self._watchdog = threading.Thread(
            target=watchdog, name='rmq-watchdog', daemon=True)
        self._watchdog.start()
