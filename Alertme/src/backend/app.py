"""Shared API for the native desktop client and same-origin web workspace."""

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from secrets import randbelow
import re
from uuid import uuid4

from bson import ObjectId
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    unset_jwt_cookies,
)
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

from .models.deadline import (
    DeadlineModel,
    checked_text,
    serialize,
    utcnow,
    validate_fields,
)
from .models.personal_deadline import PersonalDeadlineModel
from .services.notification_service import NotificationService

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "src" / "web"


def create_app(config=None, mongo_client=None, notifier=None):
    load_dotenv(ROOT / ".env")
    app = Flask(__name__, static_folder=str(WEB / "static"), static_url_path="/static")
    app.config.update(
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY", ""),
        MONGODB_URI=os.getenv("MONGODB_URI", ""),
        DB_NAME=os.getenv("DB_NAME", "alertme"),
        PERSONAL_DB_NAME=os.getenv("PERSONAL_DB_NAME", "alertme_personal"),
        ADMIN_EMAIL=os.getenv("ADMIN_EMAIL", "").strip().lower(),
        ADMIN_PASSWORD_HASH=os.getenv("ADMIN_PASSWORD_HASH", ""),
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=1),
        JWT_TOKEN_LOCATION=["headers", "cookies"],
        JWT_COOKIE_CSRF_PROTECT=True,
        JWT_COOKIE_SAMESITE="Lax",
        JWT_COOKIE_SECURE=os.getenv("ALERTME_ENV") == "production",
        MAX_CONTENT_LENGTH=128 * 1024,
        LIMITS_ENABLED=True,
        JSON_SORT_KEYS=False,
    )
    if config:
        app.config.update(config)
    secret = app.config["JWT_SECRET_KEY"]
    if (
        not isinstance(secret, str)
        or len(secret) < 32
        or secret.lower().startswith(("your", "change"))
    ):
        raise RuntimeError("Set JWT_SECRET_KEY to a unique random value of at least 32 characters")
    if not app.config["MONGODB_URI"] and mongo_client is None:
        raise RuntimeError("MONGODB_URI is required")
    client = (
        mongo_client
        if mongo_client is not None
        else MongoClient(
            app.config["MONGODB_URI"],
            serverSelectionTimeoutMS=4000,
            connectTimeoutMS=4000,
            socketTimeoutMS=5000,
            maxPoolSize=20,
        )
    )
    db, legacy = client[app.config["DB_NAME"]], client[app.config["PERSONAL_DB_NAME"]]
    users = db.users
    personal_model = PersonalDeadlineModel(client, db.name, legacy.name)
    legacy_model = DeadlineModel(client, db.name, legacy.name)
    service = notifier or NotificationService()
    app.extensions.update(
        mongo=client,
        database=db,
        legacy_database=legacy,
        personal_model=personal_model,
        legacy_model=legacy_model,
        notifier=service,
    )
    initialize_indexes(db, legacy)
    origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
    if "*" in origins:
        raise RuntimeError("CORS_ORIGINS requires explicit origins")
    if origins:
        CORS(app, origins=origins, supports_credentials=True)
    jwt = JWTManager(app)

    @jwt.token_in_blocklist_loader
    def token_invalid(header, claims):
        if db.revoked_tokens.find_one({"_id": claims["jti"]}):
            return True
        if claims.get("is_admin"):
            return (
                not app.config["ADMIN_EMAIL"]
                or claims.get("admin_email") != app.config["ADMIN_EMAIL"]
            )
        if not ObjectId.is_valid(claims.get("sub", "")):
            return True
        user = users.find_one({"_id": ObjectId(claims["sub"])})
        return not user or claims.get("version", 0) != user.get("token_version", 0)

    @jwt.unauthorized_loader
    def unauthorized(reason):
        return jsonify(message="Sign in to continue."), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify(message="Your session is invalid. Sign in again."), 401

    @jwt.expired_token_loader
    def expired(header, claims):
        return jsonify(message="Your session expired. Sign in again."), 401

    @jwt.revoked_token_loader
    def revoked(header, claims):
        return jsonify(message="Sign in again to continue."), 401

    def admin_required(function):
        @wraps(function)
        @jwt_required()
        def wrapped(*args, **kwargs):
            if not get_jwt().get("is_admin"):
                return jsonify(message="Administrator access required."), 403
            return function(*args, **kwargs)

        return wrapped

    def normal_user():
        if get_jwt().get("is_admin"):
            raise ValueError("Use a personal account for this action.")
        return users.find_one({"_id": ObjectId(get_jwt_identity())})

    def object_id(value):
        if not ObjectId.is_valid(value):
            raise ValueError("Invalid record identifier.")
        return ObjectId(value)

    def body():
        value = request.get_json(silent=True)
        if not isinstance(value, dict):
            raise ValueError("A JSON object is required.")
        return value

    def public_user(user):
        return {
            "id": str(user["_id"]),
            "name": user.get("name", ""),
            "email": user.get("email", ""),
            "phone": user.get("phone", ""),
            "email_verified": user.get("email_verified", False),
            "phone_verified": user.get("phone_verified", False),
            "preferences": user.get("preferences", {"email": False, "sms": False}),
        }

    def login_response(user=None, admin=False):
        token = create_access_token(
            identity="admin" if admin else str(user["_id"]),
            additional_claims={
                "is_admin": admin,
                **(
                    {"admin_email": app.config["ADMIN_EMAIL"]}
                    if admin
                    else {"version": user.get("token_version", 0)}
                ),
            },
        )
        account = (
            {
                "id": "admin",
                "name": "Administrator",
                "email": app.config["ADMIN_EMAIL"],
                "is_admin": True,
            }
            if admin
            else public_user(user)
        )
        response = jsonify(token=token, user=account)
        set_access_cookies(response, token)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.before_request
    def limits():
        if (
            request.path.startswith("/static")
            or request.path in ("/", "/health", "/ready")
            or not app.config["LIMITS_ENABLED"]
        ):
            return None
        minute = int(datetime.now(timezone.utc).timestamp() // 900)
        group = (
            "auth"
            if request.path in ("/login", "/signup", "/auth/api/admin/login")
            or "verification" in request.path
            else "api"
        )
        key = hmac.new(
            secret.encode(),
            f"{request.remote_addr}|{group}|{minute}".encode(),
            hashlib.sha256,
        ).hexdigest()
        counter = db.request_limits.find_one_and_update(
            {"_id": key},
            {
                "$inc": {"count": 1},
                "$setOnInsert": {"expires_at": utcnow() + timedelta(minutes=30)},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if counter["count"] > (30 if group == "auth" else 1000):
            response = jsonify(message="Too many requests. Please try again later.")
            response.status_code = 429
            response.headers["Retry-After"] = "900"
            return response

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        if request.path.startswith(("/api/", "/admin/", "/auth/")):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(ValueError)
    def validation_error(error):
        return jsonify(message=str(error)), 422

    @app.errorhandler(DuplicateKeyError)
    def duplicate(error):
        return jsonify(message="This account or entry already exists."), 409

    @app.errorhandler(PyMongoError)
    def database_error(error):
        return jsonify(message="Database unavailable. Please try again."), 503

    @app.errorhandler(Exception)
    def unexpected(error):
        if isinstance(error, HTTPException):
            return jsonify(message=error.description), error.code
        app.logger.error("request_failed method=%s status=500", request.method)
        return jsonify(message="The request could not be completed."), 500

    @app.get("/")
    def index():
        return send_from_directory(WEB, "index.html")

    @app.get("/health")
    def health():
        return jsonify(status="ok", service="AlertMe")

    @app.get("/ready")
    def ready():
        client.admin.command("ping")
        return jsonify(status="ready")

    @app.post("/signup")
    def signup():
        value = body()
        name = checked_text(value.get("name"), "Name", 80, True)
        email = valid_email(value.get("email"))
        password = valid_password(value.get("password"))
        phone = value.get("phone", "")
        if phone is None:
            phone = ""
        if not isinstance(phone, str):
            raise ValueError("Phone must be text.")
        if phone and (not isinstance(phone, str) or not re.fullmatch(r"\+[1-9][0-9]{7,14}", phone)):
            raise ValueError("Phone must include its country code, for example +919876543210.")
        if users.find_one({"email": {"$regex": "^" + re.escape(email) + "$", "$options": "i"}}):
            return jsonify(message="This email is already registered."), 409
        account_id = ObjectId()
        account = {
            "_id": account_id,
            "original_id": str(account_id),
            "name": name,
            "email": email,
            "password": generate_password_hash(password),
            "created_at": utcnow(),
            "token_version": 0,
            "email_verified": False,
            "phone_verified": False,
            "preferences": {"email": False, "sms": False},
        }
        if phone:
            account["phone"] = phone
        account["_id"] = users.insert_one(account).inserted_id
        response = login_response(account)
        response.status_code = 201
        return response

    @app.post("/login")
    def login():
        value = body()
        identifier = checked_text(value.get("identifier"), "Email or phone", 255, True)
        password = checked_text(value.get("password"), "Password", 128, True)
        account = users.find_one(
            {
                "$or": [
                    {
                        "email": {
                            "$regex": "^" + re.escape(identifier.lower()) + "$",
                            "$options": "i",
                        }
                    },
                    {"phone": identifier},
                ]
            }
        )
        if not account or not check_password_hash(account.get("password", ""), password):
            return jsonify(message="Email or password is incorrect."), 401
        return login_response(account)

    @app.post("/auth/api/admin/login")
    def admin_login():
        value = body()
        password = value.get("password")
        valid = (
            app.config["ADMIN_EMAIL"]
            and isinstance(password, str)
            and len(password) <= 128
            and isinstance(value.get("email"), str)
            and value["email"].lower() == app.config["ADMIN_EMAIL"]
            and app.config["ADMIN_PASSWORD_HASH"]
            and check_password_hash(app.config["ADMIN_PASSWORD_HASH"], password)
        )
        if not valid:
            return jsonify(message="Administrator credentials are incorrect."), 401
        return login_response(admin=True)

    @app.get("/auth/api/admin/verify")
    @admin_required
    def verify_admin():
        return jsonify(is_admin=True)

    @app.post("/logout")
    @jwt_required()
    def logout():
        claims = get_jwt()
        db.revoked_tokens.update_one(
            {"_id": claims["jti"]},
            {"$set": {"expires_at": datetime.fromtimestamp(claims["exp"], timezone.utc)}},
            upsert=True,
        )
        response = jsonify(message="Signed out.")
        unset_jwt_cookies(response)
        return response

    @app.route("/api/me", methods=["GET", "PUT"])
    @jwt_required()
    def me():
        if get_jwt().get("is_admin"):
            return jsonify(
                id="admin",
                name="Administrator",
                email=app.config["ADMIN_EMAIL"],
                is_admin=True,
            )
        user = normal_user()
        if request.method == "PUT":
            value = body()
            updates = {}
            if "name" in value:
                updates["name"] = checked_text(value["name"], "Name", 80, True)
            if "preferences" in value:
                prefs = value["preferences"]
                if not isinstance(prefs, dict) or any(
                    type(prefs.get(k, False)) is not bool for k in ("email", "sms")
                ):
                    raise ValueError("Choose valid reminder preferences.")
                for channel in ("email", "sms"):
                    if prefs.get(channel) and not user.get(
                        "email_verified" if channel == "email" else "phone_verified"
                    ):
                        raise ValueError(
                            f"Verify your {channel} contact before enabling reminders."
                        )
                    if prefs.get(channel) and not service.configured(channel):
                        return jsonify(
                            message=f"{channel.upper()} delivery is not configured."
                        ), 503
                updates["preferences"] = {k: prefs.get(k, False) for k in ("email", "sms")}
            if updates:
                users.update_one({"_id": user["_id"]}, {"$set": updates})
                user.update(updates)
        return jsonify(public_user(user))

    @app.post("/api/me/password")
    @jwt_required()
    def change_password():
        user, value = normal_user(), body()
        current = value.get("current_password")
        if (
            not isinstance(current, str)
            or len(current) > 128
            or not check_password_hash(user["password"], current)
        ):
            return jsonify(message="Current password is incorrect."), 400
        users.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "password": generate_password_hash(valid_password(value.get("new_password")))
                },
                "$inc": {"token_version": 1},
            },
        )
        response = jsonify(message="Password changed. Sign in again.")
        unset_jwt_cookies(response)
        return response

    @app.route("/api/me/verification", methods=["POST", "PUT"])
    @jwt_required()
    def verification():
        user, value = normal_user(), body()
        channel = value.get("channel")
        if channel not in ("email", "sms"):
            raise ValueError("Choose email or sms verification.")
        target = user.get("email" if channel == "email" else "phone")
        if not target:
            raise ValueError("No contact is set for this channel.")
        challenge_id = f"{user['_id']}:{channel}"
        if request.method == "POST":
            now = utcnow()
            reservation = uuid4().hex
            code = f"{randbelow(1000000):06d}"
            digest = hmac.new(
                secret.encode(), f"{challenge_id}:{code}".encode(), hashlib.sha256
            ).hexdigest()
            try:
                db.contact_challenges.find_one_and_update(
                    {
                        "_id": challenge_id,
                        "$or": [
                            {"sent_at": {"$lte": now - timedelta(seconds=60)}},
                            {"sent_at": {"$exists": False}},
                        ],
                    },
                    {
                        "$set": {
                            "target": target,
                            "hash": digest,
                            "reservation": reservation,
                            "attempts": 0,
                            "consumed": True,
                            "sent_at": now,
                            "expires_at": now + timedelta(minutes=5),
                        }
                    },
                    upsert=True,
                    return_document=ReturnDocument.AFTER,
                )
            except DuplicateKeyError:
                return jsonify(message="Wait a minute before requesting another code."), 429
            sent = (
                service.send_email_notification(
                    target,
                    "Verify your AlertMe email",
                    f"Your AlertMe code is {code}. It expires in 5 minutes.",
                )
                if channel == "email"
                else service.sms_verification(target)
            )
            if not sent:
                db.contact_challenges.delete_one({"_id": challenge_id, "reservation": reservation})
                return jsonify(
                    message="Verification delivery is unavailable. Check provider configuration."
                ), 503
            db.contact_challenges.update_one(
                {"_id": challenge_id, "reservation": reservation}, {"$set": {"consumed": False}}
            )
            return jsonify(message="Verification code sent.")
        code = value.get("code")
        if not isinstance(code, str) or not re.fullmatch(r"[0-9]{6}", code):
            raise ValueError("Enter the 6-digit verification code.")
        challenge = db.contact_challenges.find_one_and_update(
            {
                "_id": challenge_id,
                "consumed": False,
                "target": target,
                "attempts": {"$lt": 5},
                "expires_at": {"$gt": utcnow()},
            },
            {"$inc": {"attempts": 1}},
            return_document=ReturnDocument.AFTER,
        )
        if not challenge:
            return jsonify(message="Code expired or unavailable. Request a new one."), 400
        valid = (
            hmac.compare_digest(
                challenge["hash"],
                hmac.new(
                    secret.encode(), f"{challenge_id}:{code}".encode(), hashlib.sha256
                ).hexdigest(),
            )
            if channel == "email"
            else service.sms_verification(target, code)
        )
        if not valid:
            return jsonify(message="Verification code is incorrect."), 400
        claimed = db.contact_challenges.update_one(
            {"_id": challenge_id, "hash": challenge["hash"], "consumed": False},
            {"$set": {"consumed": True}},
        )
        if not claimed.modified_count:
            return jsonify(message="Code has already been used."), 400
        users.update_one(
            {"_id": user["_id"]},
            {"$set": {"email_verified" if channel == "email" else "phone_verified": True}},
        )
        return jsonify(message="Contact verified.")

    def personal_handler(model, identifier=None):
        user = normal_user()
        if identifier:
            object_id(identifier)
            if request.method == "GET":
                item = model.get_deadline_by_id(identifier, str(user["_id"]))
                return (
                    (jsonify(item), 200) if item else (jsonify(message="Deadline not found."), 404)
                )
            success = (
                model.update_deadline(identifier, body(), str(user["_id"]))
                if request.method == "PUT"
                else model.delete_deadline(identifier, str(user["_id"]))
            )
            return (
                (jsonify(message="Deadline saved."), 200)
                if success
                else (jsonify(message="Deadline not found."), 404)
            )
        if request.method == "GET":
            return jsonify(model.get_all_deadlines(str(user["_id"])))
        value = validate_fields(body())
        value["user_id"] = str(user["_id"])
        return jsonify(id=model.create_deadline(value), message="Deadline created."), 201

    for prefix, model in (
        ("/api/personal-deadlines", personal_model),
        ("/api/deadlines", legacy_model),
    ):

        def make_handler(current_model):
            @jwt_required()
            def handler(identifier=None):
                return personal_handler(current_model, identifier)

            return handler

        handler = make_handler(model)
        app.add_url_rule(prefix, prefix, handler, methods=["GET", "POST"])
        app.add_url_rule(
            prefix + "/<identifier>",
            prefix + "-item",
            handler,
            methods=["GET", "PUT", "DELETE"],
        )

    def government_rows(admin=False):
        user_id = None if admin or not get_jwt_identity() else get_jwt_identity()
        subscribed = (
            {str(d["deadline_id"]) for d in db.subscriptions.find({"user_id": user_id})}
            if user_id
            else set()
        )
        return [
            {
                **{
                    k: v
                    for k, v in serialize(d, "government").items()
                    if k
                    in (
                        "id",
                        "_id",
                        "title",
                        "description",
                        "due_date",
                        "priority",
                        "department",
                        "source_url",
                        "storage",
                        "status",
                        "created_at",
                        "updated_at",
                    )
                },
                "subscribed": str(d["_id"]) in subscribed,
                "subscriber_count": db.subscriptions.count_documents({"deadline_id": str(d["_id"])})
                if admin
                else None,
            }
            for d in db.government_deadlines.find().sort("due_date", 1)
        ]

    @app.get("/api/government-deadlines/public")
    @jwt_required(optional=True)
    def public_deadlines():
        return jsonify(deadlines=government_rows())

    @app.route("/admin/api/government-deadlines", methods=["GET", "POST"])
    @admin_required
    def government_admin():
        if request.method == "GET":
            return jsonify(deadlines=government_rows(admin=True))
        value = validate_fields(body(), government=True)
        value.update(created_at=utcnow(), updated_at=utcnow())
        return jsonify(
            id=str(db.government_deadlines.insert_one(value).inserted_id),
            message="Government deadline published.",
        ), 201

    @app.route("/admin/api/government-deadlines/<identifier>", methods=["PUT", "DELETE"])
    @admin_required
    def government_item(identifier):
        key = object_id(identifier)
        if request.method == "DELETE":
            result = db.government_deadlines.delete_one({"_id": key})
            return (
                (jsonify(message="Deadline deleted."), 200)
                if result.deleted_count
                else (jsonify(message="Deadline not found."), 404)
            )
        result = db.government_deadlines.update_one(
            {"_id": key},
            {
                "$set": {
                    **validate_fields(body(), partial=True, government=True),
                    "updated_at": utcnow(),
                }
            },
        )
        return (
            (jsonify(message="Deadline updated."), 200)
            if result.matched_count
            else (jsonify(message="Deadline not found."), 404)
        )

    @app.post("/api/government-deadlines/<identifier>/subscribe")
    @jwt_required()
    def subscribe(identifier):
        user, value = normal_user(), body()
        object_id(identifier)
        if not db.government_deadlines.find_one({"_id": ObjectId(identifier)}):
            return jsonify(message="Deadline not found."), 404
        enabled = value.get("subscribed", True)
        if type(enabled) is not bool:
            raise ValueError("Subscription must be true or false.")
        query = {"user_id": str(user["_id"]), "deadline_id": identifier}
        if enabled:
            db.subscriptions.update_one(
                query,
                {
                    "$setOnInsert": {
                        **query,
                        "created_at": utcnow(),
                        "reminder_days": [7, 3, 1, 0],
                    }
                },
                upsert=True,
            )
        else:
            db.subscriptions.delete_one(query)
        return jsonify(subscribed=enabled, message="Subscription updated.")

    @app.get("/api/user/subscribed-deadlines")
    @jwt_required()
    def subscribed_deadlines():
        return jsonify(deadlines=[r for r in government_rows() if r["subscribed"]])

    @app.get("/api/workspace")
    @jwt_required()
    def workspace():
        if get_jwt().get("is_admin"):
            return jsonify(
                user={
                    "name": "Administrator",
                    "email": app.config["ADMIN_EMAIL"],
                    "is_admin": True,
                },
                personal=[],
                government=government_rows(admin=True),
                notifications=[],
                delivery=delivery_status(),
            )
        user = normal_user()
        rows = personal_model.get_all_deadlines(str(user["_id"]))
        if db.name != legacy.name:
            rows += legacy_model.get_all_deadlines(str(user["_id"]))
        notifications = [
            {**{k: v for k, v in n.items() if k != "_id"}, "id": str(n["_id"])}
            for n in db.notification_deliveries.find({"user_id": str(user["_id"])})
            .sort("created_at", -1)
            .limit(100)
        ]
        for n in notifications:
            for key in ("created_at", "updated_at"):
                if isinstance(n.get(key), datetime):
                    n[key] = n[key].isoformat()
        return jsonify(
            user=public_user(user),
            personal=rows,
            government=government_rows(),
            notifications=notifications,
            delivery=delivery_status(),
        )

    def delivery_status():
        return {
            "email": service.configured("email"),
            "sms": service.configured("sms"),
            "sms_verification": bool(os.getenv("TWILIO_VERIFY_SERVICE_SID")),
        }

    return app


def valid_email(value):
    value = checked_text(value, "Email", 254, True).lower()
    local, separator, domain = value.partition("@")
    if (
        not separator
        or not local
        or "@" in domain
        or "." not in domain
        or domain.startswith(".")
        or domain.endswith(".")
        or any(c.isspace() for c in value)
    ):
        raise ValueError("Enter a valid email address.")
    return value


def valid_password(value):
    if (
        not isinstance(value, str)
        or not 10 <= len(value) <= 128
        or not any(c.isalpha() for c in value)
        or not any(c.isdigit() for c in value)
    ):
        raise ValueError("Use 10–128 characters with at least one letter and one number.")
    return value


def initialize_indexes(db, legacy):
    db.users.create_index(
        "email",
        unique=True,
        name="idx_users_email_present",
        partialFilterExpression={"email": {"$type": "string"}},
    )
    db.users.create_index(
        "phone",
        unique=True,
        name="idx_users_phone_present",
        partialFilterExpression={"phone": {"$type": "string"}},
    )
    for collection in (db.deadlines, legacy.deadlines):
        collection.create_index([("user_id", 1), ("due_date", 1)])
    db.subscriptions.create_index([("user_id", 1), ("deadline_id", 1)], unique=True)
    db.government_deadlines.create_index("due_date")
    for name in ("revoked_tokens", "request_limits", "contact_challenges"):
        db[name].create_index("expires_at", expireAfterSeconds=0)
    db.notification_deliveries.create_index([("occurrence", 1), ("channel", 1)], unique=True)


if __name__ == "__main__":
    application = create_app()
    application.extensions["mongo"].admin.command("ping")
    application.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=False,
    )
