import requests
from Alertme.src.backend.services.notification_service import NotificationService


def test_missing_delivery_configuration_never_reports_success():
    service = NotificationService({"unused": True})
    assert not service.configured("email")
    assert not service.send_email_notification("person@example.test", "Test", "Message")
    assert not service.send_sms_notification("+15551234567", "Message")
    assert not service.sms_verification("+15551234567", "123456")


def test_sms_adapter_has_timeout_and_uses_actual_approval(monkeypatch):
    service = NotificationService(
        {
            "TWILIO_ACCOUNT_SID": "test-sid",
            "TWILIO_AUTH_TOKEN": "test-token",
            "TWILIO_PHONE_NUMBER": "+15550000000",
            "TWILIO_VERIFY_SERVICE_SID": "test-verify",
        }
    )
    calls = []

    class Response:
        status_code = 200

        def json(self):
            return {"status": "pending"}

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr(requests, "post", post)
    assert not service.sms_verification("+15551234567", "123456")
    assert calls[0][1]["timeout"] == 10
    assert calls[0][1]["allow_redirects"] is False


def test_sms_network_failure_is_a_failed_attempt(monkeypatch):
    service = NotificationService(
        {
            "TWILIO_ACCOUNT_SID": "test-sid",
            "TWILIO_AUTH_TOKEN": "test-token",
            "TWILIO_PHONE_NUMBER": "+15550000000",
        }
    )

    def fail(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr(requests, "post", fail)
    assert not service.send_sms_notification("+15551234567", "Message")


def test_email_adapter_requires_tls_and_bounded_connection(monkeypatch):
    import smtplib

    calls = []

    class Server:
        def __init__(self, host, port, **kwargs):
            calls.append(("connect", host, port, kwargs))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def starttls(self, **kwargs):
            calls.append(("tls", bool(kwargs.get("context"))))

        def login(self, *args):
            calls.append(("login",))

        def send_message(self, message):
            calls.append(("message", message["To"]))

    monkeypatch.setattr(smtplib, "SMTP", Server)
    service = NotificationService(
        {
            "SMTP_SERVER": "smtp.example.test",
            "SMTP_EMAIL": "sender@example.test",
            "SMTP_PASSWORD": "local-only",
        }
    )
    assert service.send_email_notification("recipient@example.test", "Test subject", "Test message")
    assert calls[0][3]["timeout"] == 10
    assert ("tls", True) in calls
