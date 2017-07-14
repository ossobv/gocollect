try:
    import uwsgi
except ImportError:
    def read_chunked(fp):
        data = []
        num = []
        while True:
            byte = fp.read(1)
            if num and byte == '\n':
                length = int(''.join(num), 16)
                if not length:
                    break

                data.append(fp.read(length))
                num = []
            elif byte in '\t\r\n':
                pass
            elif byte in '0123456789abcdef':
                num.append(byte)
            else:
                assert False, byte

        return ''.join(data)
else:
    def read_chunked(fp):
        data = []
        while True:
            chunk = uwsgi.chunked_read()
            if chunk == '':
                break
            data.append(chunk)
        return ''.join(data)
