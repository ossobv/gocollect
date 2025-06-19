from email.message import EmailMessage
import email.utils
import logging
import smtplib
import threading
import time
from urllib.parse import parse_qs


class BufferingSMTPHandler(logging.Handler):
    """
    A handler class which buffers logging records in memory. Logging events
    from the buffer are periodically sent via SMTP when there are no recent
    events or when the buffer capacity is reached.

    Based on the logging BufferingHandler and SMTPHandler.
    """
    def __init__(self, mailhost, fromaddr, toaddrs, subject,
                 capacity=50, credentials=None, secure=None, timeout=5.0,
                 flush_inactivity_timeout=10.0):
        """
        Initialize the handler.

        Initialize the instance with the from and to addresses and subject
        line of the email. To specify a non-standard SMTP port, use the
        (host, port) tuple format for the mailhost argument. To specify
        authentication credentials, supply a (username, password) tuple
        for the credentials argument. To specify the use of a secure
        protocol (TLS), pass in a tuple for the secure argument. This will
        only be used when authentication credentials are supplied. The tuple
        will be either an empty tuple, or a single-value tuple with the name
        of a keyfile, or a 2-value tuple with the names of the keyfile and
        certificate file. (This tuple is passed to the `starttls` method).
        A timeout in seconds can be specified for the SMTP connection (the
        default is one second).
        """
        logging.Handler.__init__(self)
        if isinstance(mailhost, (list, tuple)):
            self.mailhost, self.mailport = mailhost
        else:
            self.mailhost, self.mailport = mailhost, None
        if isinstance(credentials, (list, tuple)):
            self.username, self.password = credentials
        else:
            self.username = None
        self.fromaddr = fromaddr
        if isinstance(toaddrs, str):
            toaddrs = [toaddrs]
        self.toaddrs = toaddrs
        self.subject = subject
        self.secure = secure
        self.timeout = timeout

        self.buffer = []
        self.capacity = capacity

        self.last_log_time = 0
        # Start a background thread to flush the buffer periodically
        self.flush_inactivity_timeout = flush_inactivity_timeout
        self.flush_thread = threading.Thread(
            target=self._periodic_flush, daemon=True)
        self.flush_thread.start()

    def _periodic_flush(self):
        """
        Periodically flushes the buffer.

        This method runs in a separate thread and sends buffered logs
        every inactivity_flush_timeout.
        """
        # The main thread may have the lock so do not change instance variables
        # or read records from the buffer.
        # flush() will acquire the lock and is safeguarded from this.
        while True:
            time.sleep(self.flush_inactivity_timeout)
            if self.last_log_time:
                time_since_last_log = time.time() - self.last_log_time
            else:
                time_since_last_log = 0

            # Flush if buffer has records and it's been 10s of inactivity.
            if (self.buffer
                    and time_since_last_log > self.flush_inactivity_timeout):
                self.flush()

    def getSubject(self, buffer):
        """
        Determine the subject for the email.

        If you want to specify a subject line which is record-dependent,
        override this method.
        """
        last_message = buffer[-1].splitlines()[0]
        return (
            f'{self.subject}: {len(self.buffer)} message(s) : {last_message}')

    def sendEmail(self):
        """
        Formats and sends buffered log records via SMTP.
        """
        if not self.buffer:
            return

        port = self.mailport
        if not port:
            port = smtplib.SMTP_PORT
        smtp = smtplib.SMTP(self.mailhost, port, timeout=self.timeout)
        msg = EmailMessage()
        msg['From'] = self.fromaddr
        msg['To'] = ','.join(self.toaddrs)
        msg['Subject'] = self.getSubject(self.buffer)
        msg['Date'] = email.utils.localtime()
        msg.set_content('\n'.join(self.buffer))
        if self.username:
            if self.secure is not None:
                smtp.ehlo()
                smtp.starttls(*self.secure)
                smtp.ehlo()
            smtp.login(self.username, self.password)
        smtp.send_message(msg)
        smtp.quit()

    def shouldFlush(self, record):
        """
        Should the handler flush its buffer?

        Returns true if the buffer is up to capacity. This method can be
        overridden to implement custom flushing strategies.
        """
        return (len(self.buffer) >= self.capacity)

    def emit(self, record):
        """
        Emit a record.

        Append the record. If shouldFlush() tells us to, call flush() to
        process the buffer.
        """
        self.buffer.append(self.format(record))
        self.last_log_time = time.time()
        if self.shouldFlush(record):  # Too many records, flush now.
            self.flush()

    def flush(self):
        """
        Override to implement custom flushing behaviour.

        This version just zaps the buffer to empty.
        """
        self.acquire()
        try:
            self.sendEmail()
        except Exception:
            for record in self.buffer:
                self.handleError(record)
        finally:
            self.buffer.clear()
            self.release()

    def close(self):
        """
        Close the handler.

        This version just flushes and chains to the parent class' close().
        """
        try:
            self.flush()
        finally:
            logging.Handler.close(self)


def configure_smtp_handler(smtp_uri, subject):
    '''
    Configure a SMTPHandler with level=ERROR using smtp_uri.

    smtp_uri:
      smtp://sender@domain.example:pass@mailhost:port/?to=user@domain.example
    '''
    params = parse_qs(smtp_uri.query)
    if not params['to']:
        raise ValueError(
            'smtp_uri is missing "to" query param with email address')

    formatter = logging.Formatter(
        '%(asctime)s:%(levelname)s:%(name)s:%(message)s')
    # Using secure=() enables start tls.
    handler = BufferingSMTPHandler(
        mailhost=smtp_uri.hostname, fromaddr=smtp_uri.username,
        toaddrs=params['to'], subject=subject, secure=(), timeout=5,
        credentials=(smtp_uri.username, smtp_uri.password))
    handler.setFormatter(formatter)
    handler.setLevel(logging.ERROR)
    logging.getLogger('lib').addHandler(handler)
    handler = BufferingSMTPHandler(
        mailhost=smtp_uri.hostname, fromaddr=smtp_uri.username,
        toaddrs=params['to'], subject=subject, secure=(), timeout=5,
        credentials=(smtp_uri.username, smtp_uri.password))
    handler.setFormatter(formatter)
    handler.setLevel(logging.WARNING)
    logging.getLogger('service').addHandler(handler)
