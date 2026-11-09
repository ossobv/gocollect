Known Bugs
----------

* On Debian/Jessie, the ``os.keys`` output might produce a bad "comment"
  field::

    # ssh-keygen -lf /path/to/authorized_keys
    256 5a:84:.. from="ALLOWED_IP_ADDRESSES" (ED25519)

  Instead of that "from=", you would expect the comment/name of the key
  there (the last field in the authorized_keys). The cause is an ancient
  6.7p1-5+deb8u4 ssh-keygen binary.

  Not fixing because that ssh client/server combo is too ancient.
