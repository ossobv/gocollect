import json
import os
import tempfile
from datetime import datetime

from lib.file import file_is_equal

from .directory_mixin import DirectoryMixin


class Collector(DirectoryMixin):
    def __init__(self, regid, collectkey, seenip, data):
        self.regid = regid
        self.collectkey = collectkey
        self.seenip = seenip
        self.data = data

    def get_keydir(self):
        return self.get_datadir(self.collectkey)

    def get_keylink(self):
        return self.get_datalink(self.collectkey)

    def write_temp(self):
        temp = tempfile.NamedTemporaryFile(
            mode='w+', dir=self.get_keydir(), delete=False)
        try:
            temp.write(self.data)

            # Always write trailing LF.
            if self.data and self.data[-1] != '\n':
                temp.write('\n')
        except Exception:
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
                if file_is_equal(tempname, lastfile):
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
                    except Exception:
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
