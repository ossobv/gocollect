import json
import os
import tempfile
from datetime import datetime

from .directory_mixin import DirectoryMixin
from ..utils import read_chunked


def _is_file_equal(file1, file2):
    if os.path.getsize(file1) != os.path.getsize(file2):
        return False
    with open(file1) as fp1:
        with open(file2) as fp2:
            while True:
                buf1 = fp1.read(8192)
                buf2 = fp2.read(8192)
                assert len(buf1) == len(buf2), (buf1, buf2)
                if buf1 != buf2:
                    return False
                if not buf1:
                    break
    return True


class Collector(DirectoryMixin):
    def __init__(
            self, env, regid, collectkey, seenip,
            bodylen=None, bodyfp=None, data=None):
        self.env = env
        self.regid = regid
        self.collectkey = collectkey
        self.seenip = seenip
        self.bodylen = bodylen
        self.bodyfp = bodyfp
        self.data = data

        # Override path
        self.DATADIR = env.get(
            'FILE_SUBSCRIBER_AMQP_COLLECTOR_PATH', '/srv/gocollect-data')

    def get_keydir(self):
        return self.get_datadir(self.collectkey)

    def get_keylink(self):
        return self.get_datalink(self.collectkey)

    def write_temp(self):
        if self.data is None:
            if self.bodylen is None:
                body = read_chunked(self.bodyfp)
            else:
                body = self.bodyfp.read(self.bodylen)
        else:
            body = self.data

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
            # 5 data files. This is important for the app.lshw which is
            # prone to return slightly different/altered output every
            # call.
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
