import os
import hashlib

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/alertme-qt-cache")
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from pymongo import MongoClient
from urllib.parse import urlsplit
from werkzeug.security import generate_password_hash
from Alertme.src.backend.app import create_app


class FakeNotifier:
    def __init__(self):
        self.emails, self.sms = [], []
        self.available = True
        self.approved = False

    def configured(self, channel):
        return self.available

    def send_email_notification(self, recipient, subject, message):
        self.emails.append((recipient, subject, message))
        return self.available

    def send_sms_notification(self, recipient, message):
        self.sms.append((recipient, message))
        return self.available

    def sms_verification(self, phone, code=None):
        return self.available if code is None else self.approved and code == "654321"


@pytest.fixture
def database():
    uri = os.getenv("TEST_MONGODB_URI", "")
    parsed = urlsplit(uri)
    if (
        parsed.hostname not in ("localhost", "127.0.0.1", "::1")
        or os.getenv("ALLOW_TEST_DATABASE_RESET") != "1"
    ):
        raise RuntimeError(
            "Set TEST_MONGODB_URI to a disposable loopback MongoDB and ALLOW_TEST_DATABASE_RESET=1. See README verification setup."
        )
    client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    client.admin.command("ping")
    for name in ("alertme_test", "alertme_legacy_test"):
        client.drop_database(name)
    yield client
    for name in ("alertme_test", "alertme_legacy_test"):
        client.drop_database(name)
    client.close()


@pytest.fixture
def notifier():
    return FakeNotifier()


@pytest.fixture
def backend(database, notifier):
    return create_app(
        {
            "TESTING": True,
            "LIMITS_ENABLED": False,
            "JWT_SECRET_KEY": "local-test-signing-key-with-at-least-32-characters",
            "DB_NAME": "alertme_test",
            "PERSONAL_DB_NAME": "alertme_legacy_test",
            "ADMIN_EMAIL": "admin@example.test",
            "ADMIN_PASSWORD_HASH": generate_password_hash("Admin-test-password123"),
        },
        mongo_client=database,
        notifier=notifier,
    )


@pytest.fixture
def client(backend):
    return backend.test_client()


def register(client, email="owner@example.test"):
    response = client.post(
        "/signup",
        json={
            "name": "Test Owner",
            "email": email,
            "password": "Local-test-password123",
            "phone": "+1555"
            + str(
                int.from_bytes(hashlib.sha256(email.encode()).digest()[:4], "big") % 10000000
            ).zfill(7),
        },
    )
    assert response.status_code == 201, response.json
    return response.json, {"Authorization": "Bearer " + response.json["token"]}
