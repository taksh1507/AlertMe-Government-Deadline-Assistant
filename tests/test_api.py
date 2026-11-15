import re
from datetime import date, timedelta
import pytest
from bson import ObjectId
from flask_jwt_extended import decode_token
from werkzeug.security import check_password_hash
from Alertme.src.backend.app import create_app
from Alertme.src.backend.models.deadline import utcnow
from Alertme.src.backend.services.deadline_scanner import DeadlineScanner
from .conftest import register

ENTRY = {
    "title": "Renew documents",
    "description": "Check the requirements",
    "due_date": "2026-12-01",
    "priority": "high",
    "category": "Personal",
    "status": "pending",
    "reminder_days": [7, 3, 1, 0],
}


def test_signup_passwords_and_real_session_identity(backend, client):
    account, headers = register(client)
    user = backend.extensions["database"].users.find_one({"email": "owner@example.test"})
    assert user["password"] != "Local-test-password123"
    assert check_password_hash(user["password"], "Local-test-password123")
    assert client.get("/api/me", headers=headers).json["id"] == str(user["_id"])
    assert not user["email_verified"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": [], "email": "x"},
        {"name": "Test", "email": {"$ne": None}, "password": "Example1234"},
        {"name": "Test", "email": "x@example.test", "password": "short"},
        {"name": "Test", "email": "no email", "password": "Example1234"},
    ],
)
def test_invalid_signup_is_rejected_without_writes(backend, client, payload):
    assert client.post("/signup", json=payload).status_code in (400, 422)
    assert backend.extensions["database"].users.count_documents({}) == 0


def test_case_normalized_duplicate_email_is_not_registered(client):
    register(client)
    assert (
        client.post(
            "/signup",
            json={
                "name": "Other",
                "email": "OWNER@example.test",
                "password": "Local-test-password123",
            },
        ).status_code
        == 409
    )


def test_login_and_auth_errors(client):
    register(client)
    assert (
        client.post("/login", json={"identifier": {"$ne": None}, "password": "wrong"}).status_code
        == 422
    )
    assert (
        client.post(
            "/login", json={"identifier": "owner@example.test", "password": "wrong"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/login",
            json={
                "identifier": "OWNER@example.test",
                "password": "Local-test-password123",
            },
        ).status_code
        == 200
    )
    assert (
        client.get("/api/workspace", headers={"Authorization": "Bearer invalid"}).status_code == 401
    )


@pytest.mark.parametrize("endpoint", ["/api/deadlines", "/api/personal-deadlines"])
def test_owner_isolation_and_stable_updates(client, endpoint):
    owner, headers = register(client)
    created = client.post(endpoint, json=ENTRY, headers=headers)
    assert created.status_code == 201
    identifier = created.json["id"]
    _, other = register(client, "other@example.test")
    assert client.get(endpoint + "/" + identifier, headers=other).status_code == 404
    assert (
        client.put(
            endpoint + "/" + identifier, json={"title": "Claimed"}, headers=other
        ).status_code
        == 404
    )
    assert client.delete(endpoint + "/" + identifier, headers=other).status_code == 404
    updated = client.put(
        endpoint + "/" + identifier,
        json={"title": "Updated", "user_id": other["Authorization"]},
        headers=headers,
    )
    assert updated.status_code == 200
    result = client.get(endpoint + "/" + identifier, headers=headers).json
    assert result["title"] == "Updated"
    assert result["user_id"] == owner["user"]["id"]
    assert client.delete(endpoint + "/" + identifier, headers=headers).status_code == 200


@pytest.mark.parametrize(
    "change",
    [
        {"due_date": "2026-02-30"},
        {"priority": "critical"},
        {"status": "anything"},
        {"title": []},
        {"category": {}},
        {"reminder_days": [True]},
        {"reminder_days": [31]},
        {"description": "x" * 3001},
    ],
)
def test_edits_are_validated_before_existing_records_change(client, change):
    _, headers = register(client)
    identifier = client.post("/api/personal-deadlines", json=ENTRY, headers=headers).json["id"]
    assert (
        client.put(
            "/api/personal-deadlines/" + identifier, json=change, headers=headers
        ).status_code
        == 422
    )
    assert (
        client.get("/api/personal-deadlines/" + identifier, headers=headers).json["title"]
        == ENTRY["title"]
    )


def test_workspace_reads_both_retained_databases_without_moving_records(backend, client):
    account, headers = register(client)
    for endpoint in ("/api/deadlines", "/api/personal-deadlines"):
        assert client.post(endpoint, json=ENTRY, headers=headers).status_code == 201
    data = client.get("/api/workspace", headers=headers).json
    assert len(data["personal"]) == 2
    assert {d["storage"] for d in data["personal"]} == {"main", "legacy"}
    assert backend.extensions["database"].deadlines.count_documents({}) == 1
    assert backend.extensions["legacy_database"].deadlines.count_documents({}) == 1


def test_malformed_ids_and_nonobject_requests_are_client_errors(client):
    _, headers = register(client)
    assert client.delete("/api/deadlines/invalid", headers=headers).status_code == 422
    assert client.post("/api/personal-deadlines", json=[], headers=headers).status_code == 422


def admin(client):
    result = client.post(
        "/auth/api/admin/login",
        json={"email": "admin@example.test", "password": "Admin-test-password123"},
    )
    assert result.status_code == 200
    return {"Authorization": "Bearer " + result.json["token"]}


def test_administration_publication_and_private_subscriptions(backend, client):
    _, headers = register(client)
    assert (
        client.post("/admin/api/government-deadlines", json=ENTRY, headers=headers).status_code
        == 403
    )
    admin_headers = admin(client)
    payload = {
        **ENTRY,
        "department": "Education",
        "source_url": "https://example.gov/apply",
        "subscribers": ["hidden@example.test"],
    }
    created = client.post("/admin/api/government-deadlines", json=payload, headers=admin_headers)
    assert created.status_code == 201
    identifier = created.json["id"]
    assert (
        client.post(
            f"/api/government-deadlines/{identifier}/subscribe",
            json={"email": "stranger@example.test", "subscribed": True},
            headers=headers,
        ).status_code
        == 200
    )
    client.post(
        f"/api/government-deadlines/{identifier}/subscribe",
        json={"subscribed": True},
        headers=headers,
    )
    subscriptions = backend.extensions["database"].subscriptions
    assert subscriptions.count_documents({}) == 1
    assert (
        subscriptions.find_one({})["user_id"] == client.get("/api/me", headers=headers).json["id"]
    )
    public = client.get("/api/government-deadlines/public", headers=headers).json["deadlines"]
    assert public[0]["subscribed"]
    assert "subscribers" not in public[0]
    assert "hidden@example.test" not in str(public)
    assert (
        client.post(
            f"/api/government-deadlines/{identifier}/subscribe",
            json={"subscribed": False},
            headers=headers,
        ).status_code
        == 200
    )
    assert subscriptions.count_documents({}) == 0
    assert (
        client.put(
            "/admin/api/government-deadlines/" + identifier,
            json={"title": ENTRY["title"]},
            headers=admin_headers,
        ).status_code
        == 200
    )
    assert (
        client.delete(
            "/admin/api/government-deadlines/" + identifier, headers=admin_headers
        ).status_code
        == 200
    )


def test_unconfigured_admin_has_no_default_login(backend, client):
    backend.config["ADMIN_EMAIL"] = ""
    assert (
        client.post(
            "/auth/api/admin/login",
            json={"email": "admin@example.test", "password": "Admin-test-password123"},
        ).status_code
        == 401
    )


def test_source_links_require_https(client):
    headers = admin(client)
    result = client.post(
        "/admin/api/government-deadlines",
        json={**ENTRY, "department": "Test", "source_url": "javascript:alert(1)"},
        headers=headers,
    )
    assert result.status_code == 422


def test_logout_and_password_changes_revoke_sessions(client):
    account, headers = register(client)
    assert (
        client.post(
            "/api/me/password",
            json={
                "current_password": "Local-test-password123",
                "new_password": "A-new-password123",
            },
            headers=headers,
        ).status_code
        == 200
    )
    assert client.get("/api/me", headers=headers).status_code == 401
    session = client.post(
        "/login",
        json={"identifier": "owner@example.test", "password": "A-new-password123"},
    ).json
    current = {"Authorization": "Bearer " + session["token"]}
    assert client.post("/logout", json={}, headers=current).status_code == 200
    assert client.get("/api/me", headers=current).status_code == 401


def test_web_cookies_require_csrf_for_mutations(client):
    register(client)
    assert client.get("/api/me").status_code == 200
    assert client.post("/api/personal-deadlines", json=ENTRY).status_code == 401
    csrf = client.get_cookie("csrf_access_token").value
    assert (
        client.post(
            "/api/personal-deadlines", json=ENTRY, headers={"X-CSRF-TOKEN": csrf}
        ).status_code
        == 201
    )


def test_contact_codes_expire_replay_and_attempt_limits(backend, client, notifier):
    _, headers = register(client)
    assert (
        client.post("/api/me/verification", json={"channel": "email"}, headers=headers).status_code
        == 200
    )
    code = re.search(r"\b\d{6}\b", notifier.emails[-1][2]).group()
    for _ in range(5):
        wrong = "000000" if code != "000000" else "111111"
        assert (
            client.put(
                "/api/me/verification",
                json={"channel": "email", "code": wrong},
                headers=headers,
            ).status_code
            == 400
        )
    assert (
        client.put(
            "/api/me/verification",
            json={"channel": "email", "code": code},
            headers=headers,
        ).status_code
        == 400
    )
    backend.extensions["database"].contact_challenges.delete_many({})
    client.post("/api/me/verification", json={"channel": "email"}, headers=headers)
    code = re.search(r"\b\d{6}\b", notifier.emails[-1][2]).group()
    assert (
        client.put(
            "/api/me/verification",
            json={"channel": "email", "code": code},
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.put(
            "/api/me/verification",
            json={"channel": "email", "code": code},
            headers=headers,
        ).status_code
        == 400
    )
    assert client.get("/api/me", headers=headers).json["email_verified"]


def test_sms_checks_provider_status_instead_of_assuming_success(client, notifier):
    _, headers = register(client)
    assert (
        client.post("/api/me/verification", json={"channel": "sms"}, headers=headers).status_code
        == 200
    )
    assert (
        client.put(
            "/api/me/verification",
            json={"channel": "sms", "code": "654321"},
            headers=headers,
        ).status_code
        == 400
    )
    notifier.approved = True
    assert (
        client.put(
            "/api/me/verification",
            json={"channel": "sms", "code": "654321"},
            headers=headers,
        ).status_code
        == 200
    )


def test_delivery_failure_does_not_expose_code_or_issue_success(client, notifier):
    _, headers = register(client)
    notifier.available = False
    result = client.post("/api/me/verification", json={"channel": "email"}, headers=headers)
    assert result.status_code == 503
    assert "code" not in result.json
    assert (
        client.put("/api/me", json={"preferences": {"email": True}}, headers=headers).status_code
        == 422
    )


def test_reminder_scanner_deduplicates_and_records_actual_delivery(backend, client, notifier):
    account, headers = register(client)
    db = backend.extensions["database"]
    db.users.update_one(
        {"_id": ObjectId(account["user"]["id"])},
        {
            "$set": {
                "email_verified": True,
                "preferences": {"email": True, "sms": False},
            }
        },
    )
    payload = {**ENTRY, "due_date": date.today().isoformat()}
    client.post("/api/personal-deadlines", json=payload, headers=headers)
    scanner = DeadlineScanner(backend)
    scanner.scan_deadlines(date.today())
    scanner.scan_deadlines(date.today())
    assert len(notifier.emails) == 1
    assert db.notification_deliveries.count_documents({}) == 1
    assert db.notification_deliveries.find_one({})["status"] == "sent"
    notifier.available = False
    client.post("/api/personal-deadlines", json={**payload, "title": "Second"}, headers=headers)
    scanner.scan_deadlines(date.today())
    assert db.notification_deliveries.count_documents({"status": "failed"}) == 1


def test_tokens_have_bounded_lifetimes_and_readiness_is_real(backend, client):
    account, _ = register(client)
    with backend.app_context():
        claims = decode_token(account["token"])
    assert 0 < claims["exp"] - claims["iat"] <= 3600
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200


def test_rate_limits_and_body_bounds(backend, client):
    backend.config["LIMITS_ENABLED"] = True
    for _ in range(30):
        assert (
            client.post(
                "/login", json={"identifier": "none@example.test", "password": "wrong"}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/login", json={"identifier": "none@example.test", "password": "wrong"}
        ).status_code
        == 429
    )
    assert client.post(
        "/signup", data="x" * 150000, content_type="application/json"
    ).status_code in (413, 429)


def test_missing_required_configuration_refuses_startup(database):
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        create_app({"JWT_SECRET_KEY": ""}, mongo_client=database)


def test_expired_email_code_cannot_verify_contact(backend, client, notifier):
    _, headers = register(client)
    client.post("/api/me/verification", json={"channel": "email"}, headers=headers)
    code = re.search(r"\b\d{6}\b", notifier.emails[-1][2]).group()
    backend.extensions["database"].contact_challenges.update_many(
        {}, {"$set": {"expires_at": utcnow() - timedelta(seconds=1)}}
    )
    assert (
        client.put(
            "/api/me/verification",
            json={"channel": "email", "code": code},
            headers=headers,
        ).status_code
        == 400
    )
    assert not client.get("/api/me", headers=headers).json["email_verified"]


def test_existing_mirror_records_and_identifier_index_do_not_block_signup(database, notifier):
    db = database["alertme_test"]
    db.users.create_index("original_id", unique=True)
    db.users.insert_many([{"original_id": "legacy-one"}, {"original_id": "legacy-two"}])
    app = create_app(
        {
            "JWT_SECRET_KEY": "another-local-test-key-with-32-characters",
            "DB_NAME": "alertme_test",
            "PERSONAL_DB_NAME": "alertme_legacy_test",
            "TESTING": True,
            "LIMITS_ENABLED": False,
        },
        mongo_client=database,
        notifier=notifier,
    )
    client = app.test_client()
    register(client, "first@example.test")
    register(client, "second@example.test")
    assert db.users.count_documents({}) == 4
    assert db.users.count_documents({"email": {"$exists": False}}) == 2


def test_duplicate_phone_cannot_make_phone_login_ambiguous(client):
    account, headers = register(client)
    phone = account["user"]["phone"]
    response = client.post(
        "/signup",
        json={
            "name": "Another account",
            "email": "another@example.test",
            "phone": phone,
            "password": "Other-password123",
        },
    )
    assert response.status_code == 409
    assert (
        client.post(
            "/login", json={"identifier": phone, "password": "Local-test-password123"}
        ).status_code
        == 200
    )


def test_simultaneous_code_requests_share_one_delivery_reservation(
    backend, client, notifier, monkeypatch
):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    _, headers = register(client)
    started = threading.Event()
    release = threading.Event()
    original = notifier.send_email_notification

    def delayed(*args):
        started.set()
        assert release.wait(3)
        return original(*args)

    monkeypatch.setattr(notifier, "send_email_notification", delayed)

    def send():
        with backend.test_client() as worker:
            return worker.post(
                "/api/me/verification", json={"channel": "email"}, headers=headers
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(send)
        assert started.wait(3)
        second = pool.submit(send)
        try:
            assert second.result(timeout=3) == 429
        finally:
            release.set()
        assert first.result(timeout=3) == 200
    assert len(notifier.emails) == 1
