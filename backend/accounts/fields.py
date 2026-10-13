from django.db import models
from encrypted_fields import fields


class EncryptedCharField(fields.EncryptedCharField):
    """django-fernet-encrypted-fields' EncryptedCharField with two fixes.

    - Blank stays blank. Upstream stores every falsy value as NULL, which
      breaks our NOT NULL `blank=True, default=''` columns and turns the API's
      "" into null. An empty string reveals nothing, so it's stored as-is
      (reading it back can't decrypt it and returns it unchanged).
    - No `_already_decrypted` flag in clean(). Upstream sets it on the field
      instance, which every thread shares - under gunicorn's gthread workers an
      admin form being validated in one thread makes another thread's query
      skip decryption and return ciphertext. Not needed anyway: to_python()
      on a value that's already plaintext fails to decrypt and returns it
      unchanged.
    """

    def get_prep_value(self, value):
        if value == '':
            return value
        return super().get_prep_value(value)

    def clean(self, value, model_instance):
        return models.CharField.clean(self, value, model_instance)
