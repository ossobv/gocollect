"""
Example GoCollect wsgi server that stores the collected items in a
filesystem tree.

Default storage location: ``/srv/gocollect-data``

Example uwsgi config::

    [uwsgi]
    wsgi-file = /srv/http/gocollect.example.com/wsgi_to_filestorage.py
    workers = 2
    # You need may need full uwsgi restart after unsetting this.
    env = GOCOLLECT_DATADIR=/var/lib/gocollect

Example nginx config::

    location ~ ^/client/v1(/.*) {
        uwsgi_pass unix:/var/run/uwsgi/app/gocollect/socket;
        include uwsgi_params;
        # PATH_INFO shall contain only the application-specific path,
        # not the path to the application itself.
        # https://www.python.org/dev/peps/pep-0333/
        # https://www.python.org/dev/peps/pep-0444/
        uwsgi_param SCRIPT_NAME /client/v1;     # unset by default
        uwsgi_param PATH_INFO $1;               # remove "/client/v1"
        # Setting uwsgi_modifier1 along with the SCRIPT_NAME
        # above is also possible, but deprecated by uWSGI.
        #uwsgi_modifier1 30; # UWSGI_MODIFIER_MANAGE_PATH_INFO
    }
"""
import uuid

from lib.handlers.directory.collector import Collector
from lib.handlers.directory.directory_mixin import DirectoryMixin
from lib.http import read_chunked


class Registrar(DirectoryMixin):
    def __init__(self, seenip, data):
        # TODO: Read body and determine whether we've seen this host before?
        # Should then fetch and return old regid? Ignore for now.
        self.seenip = seenip
        del data  # ignore for now..

    def register(self):
        self.regid = str(uuid.uuid4())
        self.get_nodedir()  # create if doesn't exist yet
        return self.regid


def read_body(fp, length):
    if length is None:
        data = read_chunked(fp)
    else:
        data = fp.read(length)
    return data


def application(environ, start_response):
    def make_response(head, headers=[], ctype='text/plain', body=b''):
        start_response(head, headers + [
            ('Content-Length', str(len(body))),
            ('Content-Type', ctype)])
        return body

    method = environ['REQUEST_METHOD']
    uri = environ['PATH_INFO']  # PATH_INFO is application-specific REQUEST_URI
    source = environ['REMOTE_ADDR']

    if method == 'HEAD':
        yield make_response('200 OK')

    elif method == 'POST':
        # FIXME: confirm that this is https?
        # FIXME: do auth? :)
        # FIXME: do we allow the user to pass a different IP? perhaps we do
        if environ.get('CONTENT_LENGTH', '').isdigit():
            length = int(environ['CONTENT_LENGTH'])
        else:
            length = None

        if uri == '/register/':
            body = read_body(environ['wsgi.input'], length)
            registrar = Registrar(source, body)
            regid = registrar.register()
            yield make_response(
                '200 OK', ctype='application/json',
                body=b'{{"data": {{"regid": "{}"}}}}\n'.format(regid))

        elif uri.startswith('/update/'):
            head, update, regid, collector_key, tail = uri.split('/')
            assert head == '' and tail == '', (head, tail)
            body = read_body(environ['wsgi.input'], length)
            collector = Collector(regid, collector_key, source, body)
            collector.collect()
            yield make_response(
                '200 OK', ctype='application/json', body=b'{"data": {}}\n')

        else:
            yield make_response(
                '404 Not Found', ctype='application/json',
                body=b'{"error": "Bad URI"}\n')

    else:
        yield make_response(
            '405 Not Allowed', headers=[('Allowed', 'HEAD, POST')],
            body=b'405\n')


if __name__ == '__main__':
    # Quick and dirty WSGI test server on port 8000.
    from traceback import print_exc
    from wsgiref.simple_server import make_server

    def wrapped_application(environ, start_response):
        """
        Wrap application and do custom error handling. The wsgiref (at
        least Python 2.7) error handling is broken and reports other
        errors down the line.
        """
        try:
            for item in application(environ, start_response):
                yield item
        except:
            print_exc()
            body = b'{"error": "Broken Stuff"}'
            start_response(
                '503 Broken Stuff',
                [('Content-Length', str(len(body))),
                 ('Content-Type', 'application/json')])
            yield body

    port = 8000
    httpd = make_server('', port, wrapped_application)
    print('Serving on port {0}...'.format(port))
    httpd.serve_forever()
