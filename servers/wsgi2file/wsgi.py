# TODO: This is incomplete! This should call into handlers/directory/*.
# TODO: send_response() and friends should add Content-Length for haproxy
# keep-alive functioning.
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
import json
import os
import tempfile
import uuid

from datetime import datetime


class Registrar(DirectoryMixin):
    def __init__(self, seenip, bodylen, bodyfp):
        # TODO: Read body and determine whether we've seen this host before?
        # Should then fetch and return old regid? Ignore for now.
        self.seenip = seenip
        if bodylen is None:
            data = _read_chunked(bodyfp)
        else:
            data = bodyfp.read(bodylen)
        del data  # ignore for now..

    def register(self):
        self.regid = str(uuid.uuid4())
        self.get_nodedir()  # create if doesn't exist yet
        return self.regid


def application(environ, start_response):
    method = environ['REQUEST_METHOD']
    uri = environ['PATH_INFO']  # PATH_INFO is application-specific REQUEST_URI
    source = environ['REMOTE_ADDR']

    if method == 'HEAD':
        start_response('200 OK', [])
        yield b''

    elif method == 'POST':
        # FIXME: confirm that this is https?
        # FIXME: do auth? :)
        # FIXME: do we allow the user to pass a different IP? perhaps we do
        if environ.get('CONTENT_LENGTH', '').isdigit():
            length = int(environ['CONTENT_LENGTH'])
        else:
            length = None

        if uri == '/register/':
            registrar = Registrar(source, length, environ['wsgi.input'])
            regid = registrar.register()
            start_response(
                '200 OK', [('Content-Type', 'application/json')])
            yield b'{{"data": {{"regid": "{}"}}}}\n'.format(regid)

        elif uri.startswith('/update/'):
            head, update, regid, collector_key, tail = uri.split('/')
            assert head == '' and tail == '', (head, tail)
            collector = Collector(regid, collector_key, source,
                                  length, environ['wsgi.input'])
            collector.collect()
            start_response(
                '200 OK', [('Content-Type', 'application/json')])
            yield b'{"data": {}}\n'

        else:
            start_response(
                '404 Not Found', [('Content-Type', 'application/json')])
            yield b'{"error": "Bad URI"}\n'

    else:
        start_response('405 Not Allowed', [('Allowed', 'HEAD, POST')])
        yield b'405'


def _is_file_equal(file1, file2):
    if os.path.getsize(file1) != os.path.getsize(file2):
        return False
    with open(file1) as fp1:
        with open(file2) as fp2:
            while True:
                buf1 = fp1.read(8192)
                buf2 = fp2.read(8192)
                if buf1 != buf2:
                    return False
                if not buf1:
                    break
    return True


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
            start_response(
                '503 Broken Stuff', [('Content-Type', 'application/json')])
            yield '{"error": "Broken Stuff"}'

    port = 8000
    httpd = make_server('', port, wrapped_application)
    print('Serving on port {0}...'.format(port))
    httpd.serve_forever()
