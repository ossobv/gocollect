"""
Example GoCollect wsgi server that stores the collected items in a filesystem tree.

Default storage location: ``/srv/data/gocollect``

Example uwsgi config::

    [uwsgi]
    wsgi-file = /srv/http/gocollect.example.com/wsgi_to_filestorage.py
    workers = 2

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


class DirectoryMixin(object):
    # DATADIR = os.path.abspath(os.path.dirname(sys.argv[0]))
    DATADIR = '/srv/data/gocollect'
    DIRMODE = 0o0700

    def makedirs(self, dir_):
        try:
            os.makedirs(dir_, self.DIRMODE)
        except OSError as e:
            if e.errno != 17:  # EEXIST
                raise

    def symlink(self, dest, link):
        try:
            if os.readlink(link) == dest:
                return
        except OSError:
            pass
        else:
            # TODO: check if symlink?
            os.unlink(link)
        os.symlink(dest, link)

    def check_key(self, key):
        """
        Ensure that the data-key is valid (and contains no filesystem unsafe
        characters).
        """
        if not key or any(
                i not in 'abcdefghijklmnopqrstuvwxyz0123456789.-'
                for i in key):
            raise ValueError('crap in key', key)

    def check_regid(self, regid):
        """
        Ensure that the node-regid is valid (and contains no filesystem unsafe
        characters).
        """
        if len(self.regid) != 36 or any(
                i not in '0123456789abcdef-' for i in self.regid):
            raise ValueError('crap in regid', self.regid)

    def get_nodedir(self):
        if not hasattr(self, '_nodedir'):
            self.check_regid(self.regid)
            dir_ = os.path.join(self.DATADIR, 'nodes', self.regid[0:2],
                                self.regid)
            self.makedirs(dir_)
            self._nodedir = dir_
        return self._nodedir

    def get_datadir(self, key):
        """
        Returns: nodes/id/_history/key (used as storage dir)
        """
        if not hasattr(self, '_datadir'):
            self.check_key(key)
            dir_ = os.path.join(self.get_nodedir(), '_history', key)
            self.makedirs(dir_)
            self._datadir = dir_
        return self._datadir

    def get_datalink(self, key):
        """
        Returns: nodes/id/key (used as symlink to latest data)
        """
        if not hasattr(self, '_datalink'):
            self.check_key(key)
            link = os.path.join(self.get_nodedir(), key)
            self._datalink = link
        return self._datalink

    def link_byhostname(self, hostname):
        assert '/' not in hostname, hostname

        parts = hostname.rsplit('.', 2)
        if len(parts) >= 2:
            domain = '.'.join(parts[-2:])
        else:
            domain = 'unknown.tld'

        dir_ = os.path.join(self.DATADIR, 'byhostname', domain)
        self.makedirs(dir_)
        link = os.path.join(dir_, hostname)
        # TODO: unlink old refs??
        self.symlink(self.get_nodedir(), link)

    def link_byip4(self, sourceip, ip4):
        assert '/' not in sourceip, sourceip
        assert '/' not in ip4, ip4

        if sourceip == ip4:
            identifier = sourceip
        else:
            identifier = os.path.join('{}-gw'.format(sourceip), ip4)

        a, b, c, rest = identifier.split('.', 3)
        link = os.path.join(
            self.DATADIR, 'byip4', '{}.{}.{}'.format(a, b, c), identifier)
        dir_ = os.path.dirname(link)
        self.makedirs(dir_)
        # TODO: unlink old refs??
        self.symlink(self.get_nodedir(), link)


class Registrar(DirectoryMixin):
    def __init__(self, seenip, bodylen, bodyfp):
        # TODO: Read body and determine whether we've seen this host before?
        # Should then fetch and return old regid? Ignore for now.
        self.seenip = seenip
        self.data = bodyfp.read(bodylen)

    def register(self):
        self.regid = str(uuid.uuid4())
        self.get_nodedir()  # create if doesn't exist yet
        return self.regid


class Collector(DirectoryMixin):
    def __init__(self, regid, collectkey, seenip, bodylen, bodyfp):
        self.regid = regid
        self.collectkey = collectkey
        self.seenip = seenip
        self.bodylen = bodylen
        self.bodyfp = bodyfp

    def get_keydir(self):
        return self.get_datadir(self.collectkey)

    def get_keylink(self):
        return self.get_datalink(self.collectkey)

    def write_temp(self):
        body = self.bodyfp.read(self.bodylen)
        temp = tempfile.NamedTemporaryFile(
            dir=self.get_keydir(), delete=False)
        try:
            temp.write(body)
        except:
            temp.close()
            os.unlink(temp.name)
            raise
        return temp.name

    def collect(self):
        tempname = self.write_temp()
        try:
            datadir = self.get_keydir()

            # Get old files and check if this file is different.
            allfiles = [
                i for i in os.listdir(datadir)
                if i.startswith('2')]  # starts with date
            allfiles.sort(reverse=True)
            if allfiles:
                # Is filedata equal?
                lastfile = os.path.join(datadir, allfiles[0])
                if _is_file_equal(tempname, lastfile):
                    os.utime(lastfile, None)  # touch time stamp
                    return

            # New file. Move it to the new location with a nice
            # timestamp.
            newfile = os.path.join(
                datadir, datetime.now().strftime('%Y-%m-%d_%H:%M'))
            os.rename(tempname, newfile)
            tempname = None

            # Fix symlink to new file.
            self.symlink(newfile, self.get_keylink())

            # Truncate the amount of history for the app.* keys; keeping
            # 5 data files.
            if self.collectkey.startswith('app.') and len(allfiles) > 4:
                for to_remove in allfiles[4:]:
                    try:
                        os.unlink(os.path.join(datadir, to_remove))
                    except:
                        pass  # not my problem
        finally:
            if tempname:
                os.unlink(tempname)

        # Update paths/symlinks if this is core.id.
        if self.collectkey == 'core.id':
            with open(newfile) as fp:
                decoded = json.load(fp)
            if 'fqdn' in decoded:
                self.link_byhostname(decoded['fqdn'])
            self.link_byip4(self.seenip, decoded.get('ip4', '0'))


def application(environ, start_response):
    method = environ['REQUEST_METHOD']
    uri = environ['PATH_INFO']  # PATH_INFO is application-specific REQUEST_URI
    source = environ['REMOTE_ADDR']
    length = int(environ.get('CONTENT_LENGTH') or '0')

    if method == 'HEAD':
        start_response('200 OK', [])
        yield ''

    elif method == 'POST':
        # FIXME: confirm that this is https?
        # FIXME: do auth? :)
        # FIXME: do we allow the user to pass a different IP? perhaps we do

        if uri == '/register/':
            registrar = Registrar(source, length, environ['wsgi.input'])
            regid = registrar.register()
            start_response(
                '200 OK', [('Content-Type', 'application/json')])
            yield '{{"data": {{"regid": "{}"}}}}\n'.format(regid)

        elif uri.startswith('/update/'):
            head, update, regid, collector_key, tail = uri.split('/')
            assert head == '' and tail == '', (head, tail)
            collector = Collector(regid, collector_key, source,
                                  length, environ['wsgi.input'])
            collector.collect()
            start_response(
                '200 OK', [('Content-Type', 'application/json')])
            yield '{"data": {}}\n'

        else:
            start_response(
                '404 Not Found', [('Content-Type', 'application/json')])
            yield '{"error": "Bad URI"}\n'

    else:
        start_response('405 Not Allowed', [('Allowed', 'HEAD, POST')])
        yield '405'


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

# vim: set ts=8 sw=4 sts=4 et ai:
