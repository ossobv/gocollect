import os


def file_contents_equals(filename, content):
    """
    Return True if the file at filename holds exactly content (bytes).
    Checks the size first, so differing files are usually not read.
    """
    try:
        if os.path.getsize(filename) != len(content):
            return False
        with open(filename, 'rb') as fp:
            return fp.read() == content
    except FileNotFoundError:
        return False


def relpath(target, symlink):
    """
    Return relative path of TARGET to create a SYMLINK. The inverse of
    os.abspath().

        >>> relpath('/etc/systemd/system/ssh.service',
        ...         '/etc/systemd/system/multi-user.target.wants/ssh.service')
        '../ssh.service'
    """
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
