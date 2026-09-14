"""Custom AUTH_PASSWORD_VALIDATORS entries, alongside Django's built-in
MinimumLengthValidator/CommonPasswordValidator/UserAttributeSimilarityValidator
(see config/settings/base.py)."""

import hashlib
import re
import urllib.error
import urllib.request
from functools import lru_cache

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

SPECIAL_CHARACTERS = '!@#$%^&*'
RUN_LENGTH = 4  # reject 4+ repeated or sequential characters in a row


class UppercaseValidator:
    def validate(self, password, user=None):
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _('This password must contain at least 1 uppercase letter.'),
                code='password_no_upper',
            )

    def get_help_text(self):
        return _('Your password must contain at least 1 uppercase letter.')


class NumberValidator:
    def validate(self, password, user=None):
        if not re.search(r'\d', password):
            raise ValidationError(
                _('This password must contain at least 1 number.'),
                code='password_no_number',
            )

    def get_help_text(self):
        return _('Your password must contain at least 1 number.')


class SpecialCharacterValidator:
    def validate(self, password, user=None):
        if not any(char in SPECIAL_CHARACTERS for char in password):
            raise ValidationError(
                _('This password must contain at least 1 special character (%(chars)s).'),
                code='password_no_special',
                params={'chars': SPECIAL_CHARACTERS},
            )

    def get_help_text(self):
        return _('Your password must contain at least 1 of: %(chars)s') % {
            'chars': SPECIAL_CHARACTERS
        }


@lru_cache(maxsize=1)
def _dictionary_words():
    # Loaded once per process (validators are re-instantiated per validate()
    # call, so this can't live in __init__ without reloading the wordlist
    # every time someone registers or changes their password).
    from english_words import get_english_words_set

    return get_english_words_set(['web2'], lower=True)


class NoDictionaryWordValidator:
    """Rejects a password that is - ignoring case, digits, and punctuation -
    a single common English dictionary word (e.g. "Password1!")."""

    def validate(self, password, user=None):
        letters_only = re.sub(r'[^a-zA-Z]', '', password).lower()
        if letters_only in _dictionary_words():
            raise ValidationError(
                _("This password can't be a common dictionary word."),
                code='password_dictionary_word',
            )

    def get_help_text(self):
        return _("Your password can't be a common dictionary word.")


class NoRepeatedOrSequentialValidator:
    """Rejects a run of RUN_LENGTH+ identical characters ("aaaa") or
    ascending/descending characters ("abcd", "4321") - each individually
    satisfies the other rules but is trivially guessable."""

    def validate(self, password, user=None):
        lowered = password.lower()
        if self._has_repeated_run(lowered) or self._has_sequential_run(lowered):
            raise ValidationError(
                _(
                    "This password can't contain repeated or sequential "
                    'characters (e.g. "aaaa" or "abcd").'
                ),
                code='password_repeated_or_sequential',
            )

    def get_help_text(self):
        return _("Your password can't contain repeated or sequential characters.")

    @staticmethod
    def _has_repeated_run(password):
        for i in range(len(password) - RUN_LENGTH + 1):
            if len(set(password[i : i + RUN_LENGTH])) == 1:
                return True
        return False

    @staticmethod
    def _has_sequential_run(password):
        for i in range(len(password) - RUN_LENGTH + 1):
            codes = [ord(c) for c in password[i : i + RUN_LENGTH]]
            deltas = [b - a for a, b in zip(codes, codes[1:], strict=False)]
            if all(d == 1 for d in deltas) or all(d == -1 for d in deltas):
                return True
        return False


class PwnedPasswordValidator:
    """Checks the password against Have I Been Pwned's breached-password
    database via the k-anonymity range API - only a 5-char SHA-1 prefix is
    ever sent, never the password or its full hash. Fails open: if the API
    is unreachable, the check is skipped rather than blocking registration
    on a third-party outage."""

    def validate(self, password, user=None):
        if not getattr(settings, 'PWNED_PASSWORDS_CHECK_ENABLED', True):
            return

        sha1 = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        prefix, suffix = sha1[:5], sha1[5:]

        try:
            request = urllib.request.Request(
                f'https://api.pwnedpasswords.com/range/{prefix}',
                headers={'User-Agent': 'gradpace-backend'},
            )
            with urllib.request.urlopen(request, timeout=3) as response:
                body = response.read().decode('utf-8')
        except urllib.error.URLError, TimeoutError, OSError:
            return

        breached_suffixes = {line.split(':')[0] for line in body.splitlines()}
        if suffix in breached_suffixes:
            raise ValidationError(
                _(
                    'This password has appeared in a known data breach. '
                    'Please choose a different one.'
                ),
                code='password_pwned',
            )

    def get_help_text(self):
        return _("Your password can't be one that's appeared in a known data breach.")
