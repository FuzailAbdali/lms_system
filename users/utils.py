from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone


def send_verification_otp(user):
    subject = "Verify your LMS account"
    message = (
        f"Hello {user.first_name or user.username},\n\n"
        f"Your verification OTP is: {user.email_otp}\n"
        f"This OTP will expire in {settings.EMAIL_OTP_EXPIRY_MINUTES} minutes.\n\n"
        "If you did not create this account, please ignore this email."
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)


def is_otp_expired(user):
    if not user.email_otp_created_at:
        return True
    expiry_time = user.email_otp_created_at + timedelta(minutes=settings.EMAIL_OTP_EXPIRY_MINUTES)
    return timezone.now() > expiry_time
