import os


def file_is_equal(file1, file2):
    if os.path.getsize(file1) != os.path.getsize(file2):
        return False
    with open(file1, 'rb') as fp1:
        with open(file2, 'rb') as fp2:
            while True:
                buf1 = fp1.read(8192)
                buf2 = fp2.read(8192)
                assert len(buf1) == len(buf2), (buf1, buf2)
                if buf1 != buf2:
                    return False
                if not buf1:
                    break
    return True


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
