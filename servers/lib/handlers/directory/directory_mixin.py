import os


class DirectoryMixin(object):
    # DATADIR = os.path.abspath(os.path.dirname(sys.argv[0]))
    DATADIR = os.environ.get('GOCOLLECT_DATADIR', '/srv/gocollect-data')
    DIRMODE = 0o0700

    def makedirs(self, dir_):
        try:
            os.makedirs(dir_, self.DIRMODE)
        except OSError as e:
            if e.errno != 17:  # EEXIST
                raise

    def symlink(self, dest, link):
        # Always make relative symlinks.
        dest = self.relpath(dest, link)
        try:
            if os.readlink(link) == dest:
                return
        except OSError:
            pass
        else:
            # TODO: check if symlink?
            os.unlink(link)
        os.symlink(dest, link)

    def relpath(self, target, symlink):
        assert target[0] == os.sep  # abspath
        assert symlink[0] == os.sep  # abspath
        targetp = target.split(os.sep)
        symlinkp = symlink.split(os.sep)
        for idx in range(len(min(targetp, symlinkp))):
            if targetp[idx] != symlinkp[idx]:
                break
        # Don't count the SYMLINK basename (-1).
        targetp = ['..'] * (len(symlinkp) - idx - 1) + targetp[idx:]
        return os.sep.join(targetp)

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

# vim: set ts=8 sw=4 sts=4 et ai
