from collections import namedtuple
from urllib.parse import urlparse


def _hide_secrets(secret_fields, namedtuple_):
    secret_fields = secret_fields.split()
    hidden_value = '***'

    def __repr__(self):
        args = [
            '{}={!r}'.format(
                i, (hidden_value if i in secret_fields else getattr(self, i)))
            for i in self._fields]
        return '{}({})'.format(self.__class__.__name__, ', '.join(args))

    namedtuple_.__repr__ = __repr__
    return namedtuple_


def rmq_uri(uri):
    RmqUriBase = _hide_secrets('username password', namedtuple(
        'RmqUri', 'host port username password vhost exchange queue'))

    class RmqUri(RmqUriBase):
        @property
        def routing_key(self):
            return '#'

    # TODO: SSL/TLS
    # RMQ_URI = rmq://HOST[:PORT]/VIRTUAL_HOST/EXCHANGE[/QUEUE]
    parsed = urlparse(uri)
    assert parsed.scheme == 'rmq', parsed
    host = parsed.hostname
    port = parsed.port or 5672
    path = parsed.path.split('/', 3)
    if len(path) == 3:
        (blank, vhost, exchange) = path
        queue = 'ha.{}'.format(exchange)  # "ha.EXCHANGE"
    elif len(path) == 4:
        (blank, vhost, exchange, queue) = path
    else:
        assert False, parsed
    if vhost == '' or vhost == '%2F':
        vhost = '/'
    assert blank == '', parsed
    (username, password) = (parsed.username, parsed.password)
    assert not parsed.query and not parsed.fragment, parsed
    assert bool(parsed.username) == bool(parsed.password), parsed
    return RmqUri(
        host=host, port=port, username=username, password=password,
        vhost=vhost, exchange=exchange, queue=queue)
