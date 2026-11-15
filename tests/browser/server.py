"""Local-only browser fixture server; never used by application entry points."""

import os
import sys
from pathlib import Path
from urllib.parse import urlsplit
from datetime import date, timedelta
from werkzeug.security import generate_password_hash
from flask import jsonify, request
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from Alertme.src.backend.app import create_app
from tests.conftest import FakeNotifier

uri = os.environ.get("TEST_MONGODB_URI", "")
if (
    urlsplit(uri).hostname not in ("localhost", "127.0.0.1", "::1")
    or os.getenv("ALLOW_TEST_DATABASE_RESET") != "1"
):
    raise RuntimeError("Browser tests require explicitly resettable loopback MongoDB.")
client = MongoClient(uri, serverSelectionTimeoutMS=3000)
for name in ("alertme_browser_test", "alertme_browser_legacy_test"):
    client.drop_database(name)
notifier = FakeNotifier()
app = create_app(
    {
        "TESTING": True,
        "LIMITS_ENABLED": False,
        "JWT_SECRET_KEY": "browser-fixture-key-at-least-32-characters",
        "DB_NAME": "alertme_browser_test",
        "PERSONAL_DB_NAME": "alertme_browser_legacy_test",
        "ADMIN_EMAIL": "admin@example.test",
        "ADMIN_PASSWORD_HASH": generate_password_hash("Admin-test-password123"),
    },
    mongo_client=client,
    notifier=notifier,
)
for title, department, days in [
    ("Sample scholarship applications", "Education", 7),
    ("Sample annual filing", "Finance", 14),
]:
    app.extensions["database"].government_deadlines.insert_one(
        {
            "title": title,
            "description": "Synthetic test deadline. Confirm requirements with the actual publishing authority.",
            "department": department,
            "due_date": (date.today() + timedelta(days=days)).isoformat(),
            "priority": "medium",
            "source_url": "https://example.gov/apply",
        }
    )


@app.get("/_test/email-code")
def email_code():
    import re

    recipient = request.args.get("email")
    matches = [
        message
        for target, subject, message in notifier.emails
        if target == recipient and subject == "Verify your AlertMe email"
    ]
    return jsonify(code=re.search(r"\b\d{6}\b", matches[-1]).group() if matches else None)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=58762, debug=False, use_reloader=False)
