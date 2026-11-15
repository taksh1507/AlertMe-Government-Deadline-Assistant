"""Bounded notification adapters. Provider failures are never reported as delivery."""

import os
import smtplib
import ssl
from email.message import EmailMessage
import requests


class NotificationService:
    def __init__(self, config=None):
        self.config = config or os.environ

    def configured(self, channel):
        keys = (
            ("SMTP_SERVER", "SMTP_EMAIL", "SMTP_PASSWORD")
            if channel == "email"
            else ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER")
        )
        return all(self.config.get(key) for key in keys)

    def send_email_notification(self, recipient, subject, message):
        if not self.configured("email"):
            return False
        mail = EmailMessage()
        mail["From"] = self.config["SMTP_EMAIL"]
        mail["To"] = recipient
        mail["Subject"] = subject
        mail.set_content(message)
        try:
            host = self.config["SMTP_SERVER"]
            port = int(self.config.get("SMTP_PORT", 587))
            if port == 465:
                connection = smtplib.SMTP_SSL(
                    host, port, timeout=10, context=ssl.create_default_context()
                )
            else:
                connection = smtplib.SMTP(host, port, timeout=10)
            with connection as server:
                if port != 465:
                    server.starttls(context=ssl.create_default_context())
                server.login(self.config["SMTP_EMAIL"], self.config["SMTP_PASSWORD"])
                server.send_message(mail)
            return True
        except (OSError, smtplib.SMTPException, ValueError):
            return False

    def send_sms_notification(self, phone_number, message):
        if not self.configured("sms"):
            return False
        try:
            response = requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{self.config['TWILIO_ACCOUNT_SID']}/Messages.json",
                data={
                    "To": phone_number,
                    "From": self.config["TWILIO_PHONE_NUMBER"],
                    "Body": message,
                },
                auth=(
                    self.config["TWILIO_ACCOUNT_SID"],
                    self.config["TWILIO_AUTH_TOKEN"],
                ),
                timeout=10,
                allow_redirects=False,
            )
            return response.status_code == 201
        except requests.RequestException:
            return False

    def sms_verification(self, phone, code=None):
        if not all(
            self.config.get(k)
            for k in (
                "TWILIO_ACCOUNT_SID",
                "TWILIO_AUTH_TOKEN",
                "TWILIO_VERIFY_SERVICE_SID",
            )
        ):
            return False
        try:
            endpoint = "VerificationCheck" if code is not None else "Verifications"
            payload = {
                "To": phone,
                **({"Code": code} if code is not None else {"Channel": "sms"}),
            }
            response = requests.post(
                f"https://verify.twilio.com/v2/Services/{self.config['TWILIO_VERIFY_SERVICE_SID']}/{endpoint}",
                data=payload,
                auth=(
                    self.config["TWILIO_ACCOUNT_SID"],
                    self.config["TWILIO_AUTH_TOKEN"],
                ),
                timeout=10,
                allow_redirects=False,
            )
            return response.status_code in (200, 201) and response.json().get("status") == (
                "approved" if code is not None else "pending"
            )
        except (requests.RequestException, ValueError):
            return False
