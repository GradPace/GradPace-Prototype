import os


def get_secret(secret_id, backup=None):
    # Docker/Swarm secrets convention: if <NAME>_FILE is set, it points to a
    # file (e.g. /run/secrets/<name>) whose contents are the actual value -
    # takes precedence over a plain <NAME> env var when both are present.
    file_path = os.getenv(f'{secret_id}_FILE')
    if file_path:
        with open(file_path) as f:
            return f.read().strip()
    return os.getenv(secret_id, backup)


if get_secret('PIPELINE') == 'production':
    from .prod import *

elif get_secret('PIPELINE') == 'test':
    from .test import *

else:
    from .dev import *
