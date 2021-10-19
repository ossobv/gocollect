import json
import logging
import pika
from os import environ
from urllib.parse import urlparse
import re
import sys

from requests import Session

from lib.envparse import rmq_uri
from lib.rmq.rmq_consumer import RMQConsumer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

index_re = re.compile('^/[a-z][a-z-+_]*')


class Storage(object):
    ignore_keys = [
        'app.dmidecode',  # Messy output.
        'app.lldpctl',    # Unknown.
        'app.lshw',       # Cannot get nested mapping to work.
        'app.ps-kvmex1',  # Bad output, values as dict keys.
        'app.vzlist',     # Unknown.
        'app.vzlistex1',  # Unknown.
    ]

    def __init__(self, uri):
        self.session = Session()
        if uri.username or uri.password:
            self.session.auth = (uri.username, uri.password)
        # Drop the username/password.
        self.uri = uri._replace(netloc=uri.netloc.split('@')[-1])

    def store(self, regid, date, ip, collectkey, data):
        # ElasticSearch does not allow periods in key names as they are
        # ambiguous with path notations for nested objects.
        key = collectkey.replace('.', '_')
        # doc={key: data} are always partials of a bigger document.
        # Use doc as upsert to let ES merge it with an existing doc or insert
        # as new if it doesn't exist.
        doc = {
            'doc': {
                'regid': regid,
                'seenip': ip,
                'date': date,
                key: self.transform_data(collectkey, data),
            },
            'doc_as_upsert': True,
        }
        logger.info('Updating %s:%s from %s', regid, key, ip)
        response = self.session.post(
            '/'.join([self.uri.geturl(), '_update', regid]), json=doc)
        logger.info(response.content)
        response.raise_for_status()

    def transform_data(self, key, data):
        if key == 'app.lshw':
            self.kv2list(data, 'capabilities', 'name', 'description')
            self.kv2list(data, 'configuration', 'name', 'value')

        elif key == 'os.keys':
            for d in data.get('apt', []):
                # Date parser does not accept empty strings.
                if not d['created']:
                    d['created'] = None
                if not d['expires']:
                    d['expires'] = None

        elif key == 'os.network':
            data['interfaces'] = self.dict2list(
                'iface', data.get('interfaces'))

        elif key == 'os.pkg':
            data['installed'] = self.dict2list(
                'name', data.get('installed'))

        return data

    def dict2list(self, attr, data):
        if data is None:
            return []

        ret = []
        for name, dic in data.items():
            dic[attr] = name
            ret.append(dic)
        return ret

    def kv2list(self, data, key, kattr, vattr):
        if key in data:
            ret = []
            for k, v in data[key].items():
                ret.append({
                    kattr: k,
                    vattr: v,
                })
            data[key] = ret
        if 'children' in data:
            for child in data['children']:
                self.kv2list(child, key, kattr, vattr)

    def callback(self, ch, method, properties, body):
        try:
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            json_body = json.loads(body)

            regid = json_body.get('regid')
            if regid is None:
                logger.error('No regid found!!! %s', body)
                return

            collectkey = json_body.get('collectkey')
            if collectkey in self.ignore_keys:
                logger.debug('Skipping ignored collectkey %s', collectkey)
                return

            self.store(
                regid,
                json_body.get('date'),
                json_body.get('seenip'),
                collectkey,
                json_body.get('data', {}))
        except Exception:  # Never crash
            logger.exception('Error processing message body: %r', body)


def main():
    # rmq://HOST[:PORT]/VIRTUAL_HOST/EXCHANGE[/QUEUE]
    uri = rmq_uri(environ.get('RMQ2ES_RMQ_URI', ''))
    es_uri = urlparse(environ.get('RMQ2ES_ES_URI'))
    if not index_re.match(es_uri.path):
        raise ValueError('Invalid RMQ2ES_ES_URI, use '
                         'https://user:pass@host:port/index_name')

    if 'test' in sys.argv:
        storage = Storage(es_uri)
        data = json.loads(sys.stdin.read())
        for k, v in data.items():
            storage.transform_data(k, v)
        print(json.dumps(data))
        sys.exit()

    credentials = pika.credentials.PlainCredentials(
        uri.username, uri.password)

    parameters = pika.ConnectionParameters(
        host=uri.host, heartbeat_interval=10, virtual_host=uri.vhost,
        credentials=credentials)

    storage = Storage(es_uri)
    consumer = RMQConsumer(
        parameters, storage.callback, uri.exchange, uri.routing_key, uri.queue)

    try:
        logger.info('Started')
        consumer.run()
    except (KeyboardInterrupt, SystemExit):
        consumer.stop()
        logger.info('Exited')
