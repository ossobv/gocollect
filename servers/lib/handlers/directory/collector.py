import json
import logging
import os
import tempfile
from datetime import datetime

from lib.file import file_contents_equals

from .directory_mixin import DirectoryMixin

logger = logging.getLogger(__name__)


class Collector(DirectoryMixin):
    FILEMODE = 0o0640  # readable by group

    def __init__(self, regid, collectkey, seenip, data):
        self.regid = regid
        self.collectkey = collectkey
        self.seenip = seenip
        self.data = data

    def get_keydir(self):
        return self.get_datadir(self.collectkey)

    def get_keylink(self):
        return self.get_datalink(self.collectkey)

    def get_content(self):
        """
        Return the data as bytes, always with a trailing LF.
        """
        data = self.data
        if isinstance(data, str):
            data = data.encode('utf-8')
        if data and not data.endswith(b'\n'):
            data += b'\n'
        return data

    def write_file(self, filename, content):
        """
        Atomically write content to filename (via temp file + rename).
        """
        temp = tempfile.NamedTemporaryFile(
            mode='wb', dir=os.path.dirname(filename), delete=False)
        try:
            with temp:
                temp.write(content)
                os.fchmod(temp.fileno(), self.FILEMODE)
            os.rename(temp.name, filename)
        except Exception:
            os.unlink(temp.name)
            raise

    def collect(self):
        content = self.get_content()
        datadir = self.get_keydir()

        # Get old files and check if this data is different.
        allfiles = [
            i for i in os.listdir(datadir)
            if i.startswith('2')]  # starts with date
        allfiles.sort(reverse=True)
        if allfiles:
            # Is filedata equal?
            lastfile = os.path.join(datadir, allfiles[0])
            if file_contents_equals(lastfile, content):
                logger.debug('%s unchanged', lastfile)
                os.utime(lastfile, None)  # touch time stamp
                return

        # New data. Write it to the new location with a nice
        # timestamp.
        newfile = os.path.join(
            datadir, datetime.now().strftime('%Y-%m-%d_%H:%M'))
        self.write_file(newfile, content)
        logger.debug('%s changed', newfile)

        # Fix symlink to new file.
        self.symlink(newfile, self.get_keylink())

        # Truncate the amount of history for the app.* keys; keeping
        # 40 data files. This is important for the app.lshw which is
        # prone to return slightly different/altered output every
        # call. (Increased from 4 to 40 to allow for more history
        # for some app.* items.)
        if self.collectkey.startswith('app.'):
            for to_remove in allfiles[40:]:
                try:
                    os.unlink(os.path.join(datadir, to_remove))
                except Exception:
                    pass  # not my problem

        # Update paths/symlinks if this is core.id.
        if self.collectkey == 'core.id':
            decoded = json.loads(content.decode('utf-8'))
            if 'fqdn' in decoded:
                self.link_byhostname(decoded['fqdn'])
            self.link_byip4(self.seenip, decoded.get('ip4', '0'))
