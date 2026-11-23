"""Verifying that a new account's email address is real (spec 3.1.2.1.1).

Registering emails the new user a link to the frontend's /verify-email page.
The link carries a signed token (the user's id and email, signed with the
secret key and a timestamp - nothing is stored), and opening it makes the
frontend POST that token to /api/auth/verify-email/, which marks the account
verified. Opening the link again is harmless: it just reports the account is
already verified.

Verifying doesn't gate anything yet - an unverified account can still log in
- it only sets CustomUser.email_verified.
"""

from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from .mail import send_in_background

SALT = 'accounts.email-verification'
# How long the emailed link works. There is no "resend" yet, so be generous.
MAX_AGE = timedelta(days=7)


def make_token(user):
    return signing.dumps({'uid': str(user.pk), 'email': user.email}, salt=SALT)


def user_for_token(token, user_model):
    """The user a token was issued for, or None if it is forged, expired, or
    for an email address the account no longer has."""
    try:
        data = signing.loads(token, salt=SALT, max_age=MAX_AGE.total_seconds())
        user = user_model.objects.get(pk=data['uid'])
    except signing.BadSignature, KeyError, TypeError, ValueError, user_model.DoesNotExist:
        return None
    return user if user.email == data['email'] else None


def verification_url(user):
    return f'{settings.FRONTEND_URL}/verify-email?token={make_token(user)}'


def send_verification_email(user):
    """Fire-and-forget, like the password reset email: registration never
    waits on the mail server or fails because of it."""
    context = {'verify_url': verification_url(user), 'first_name': user.first_name}
    # Plain text first (some clients/spam filters want it), HTML as the alternative.
    email = EmailMultiAlternatives(
        subject='Verify your GradPace email address',
        body=render_to_string('accounts/emails/verify_email.txt', context),
        to=[user.email],  # from_email defaults to DEFAULT_FROM_EMAIL
    )
    email.attach_alternative(
        render_to_string('accounts/emails/verify_email.html', context), 'text/html'
    )
    return send_in_background(email)
