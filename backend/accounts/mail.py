import logging
import threading

logger = logging.getLogger(__name__)

# Tests wait on threads with this name before checking mail.outbox.
THREAD_NAME = 'send-email'


def send_in_background(email):
    """Send an EmailMessage on a separate thread, so the request doesn't wait
    on the mail server - and a slow send can't reveal (by response time) that
    an email address has an account. Fire-and-forget: a failure is logged,
    never raised to the caller, and a send in flight is lost if the worker
    restarts. Swap for a task queue if that ever matters."""
    thread = threading.Thread(target=_send, args=(email,), name=THREAD_NAME, daemon=True)
    thread.start()
    return thread


def _send(email):
    try:
        email.send()
    except Exception:
        logger.exception('Failed to send email to %s', email.to)
