"""Shared deadline validation and access to retained collections."""

from datetime import date, datetime, timezone
from bson import ObjectId

PRIORITIES = {"low", "medium", "high"}
STATUSES = {"pending", "in_progress", "completed"}
CATEGORIES = {"Personal", "Education", "Finance", "Health", "Work", "Other"}


def utcnow():
    return datetime.now(timezone.utc)


def checked_text(value, field, maximum, required=False):
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        raise ValueError(
            f"{field} must be text of at most {maximum} characters"
            + (" and cannot be empty." if required else ".")
        )
    return value.strip()


def validate_date(value):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("Choose a valid date in YYYY-MM-DD format.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError("Choose a valid calendar date.") from None
    if parsed.year < 1900 or parsed.year > 2199:
        raise ValueError("Choose a date between 1900 and 2199.")
    return parsed.isoformat()


def validate_fields(data, partial=False, government=False):
    if not isinstance(data, dict):
        raise ValueError("A JSON object is required.")
    result = {}
    defaults = {
        "description": "",
        "priority": "medium",
        "status": "pending",
        "category": "Personal",
        "reminder_days": [7, 3, 1, 0],
    }
    for field in (
        "title",
        "description",
        "due_date",
        "priority",
        "status",
        "category",
        "reminder_days",
    ):
        if government and field in ("status", "category", "reminder_days"):
            continue
        if field not in data and partial:
            continue
        value = data.get(field, defaults.get(field))
        if field in ("title", "description"):
            value = checked_text(
                value,
                field.capitalize(),
                120 if field == "title" else 3000,
                field == "title",
            )
        elif field == "due_date":
            value = validate_date(value)
        elif field in ("priority", "status"):
            if not isinstance(value, str):
                raise ValueError(f"Choose a valid {field}.")
            value = value.lower().replace(" ", "_")
            if value not in (PRIORITIES if field == "priority" else STATUSES):
                raise ValueError(f"Choose a valid {field}.")
        elif field == "category" and (not isinstance(value, str) or value not in CATEGORIES):
            raise ValueError("Choose a valid category.")
        elif field == "reminder_days":
            if (
                not isinstance(value, list)
                or len(value) > 5
                or any(type(d) is not int or d < 0 or d > 30 for d in value)
            ):
                raise ValueError("Choose up to 5 reminder days between 0 and 30.")
            value = sorted(set(value), reverse=True)
        result[field] = value
    if government:
        for field in ("department", "source_url"):
            if partial and field not in data:
                continue
            result[field] = checked_text(
                data.get(field, ""),
                field.replace("_", " ").capitalize(),
                120 if field == "department" else 500,
                field == "department",
            )
        url = result.get("source_url", "")
        if url:
            from urllib.parse import urlsplit

            parts = urlsplit(url)
            if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
                raise ValueError("The source link must be a valid HTTPS URL.")
    return result


def serialize(record, storage="main"):
    value = {key: val for key, val in record.items() if key not in ("_id", "subscribers")}
    value["id"] = str(record["_id"])
    value["_id"] = value["id"]
    value["storage"] = storage
    value["priority"] = str(record.get("priority", "medium")).lower()
    value["status"] = str(record.get("status", "pending")).lower().replace(" ", "_")
    value.setdefault("category", "Personal")
    value.setdefault("reminder_days", [7, 3, 1, 0])
    for field in ("title", "description", "due_date", "department", "source_url"):
        if field in value and not isinstance(value[field], str):
            value[field] = ""
    if value.get("priority") not in PRIORITIES:
        value["priority"] = "medium"
    if value.get("status") not in STATUSES:
        value["status"] = "pending"
    if not isinstance(value.get("category"), str):
        value["category"] = "Other"
    if not isinstance(value["reminder_days"], list) or any(
        type(d) is not int or not 0 <= d <= 30 for d in value["reminder_days"]
    ):
        value["reminder_days"] = [7, 3, 1, 0]
    for field in ("created_at", "updated_at"):
        if isinstance(value.get(field), datetime):
            value[field] = value[field].isoformat()
    return value


class DeadlineModel:
    def __init__(self, client, db_name=None, personal_db_name=None):
        import os

        self.client = client
        self.db = client[db_name or os.environ["DB_NAME"]]
        self.personal_db = client[personal_db_name or os.environ["PERSONAL_DB_NAME"]]
        self.collection = self.personal_db["deadlines"]
        self.storage = "legacy"

    def create_deadline(self, data):
        value = validate_fields(data)
        value.update(
            user_id=data["user_id"],
            type="personal",
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        return str(self.collection.insert_one(value).inserted_id)

    def get_all_deadlines(self, user_id):
        return [
            serialize(d, self.storage)
            for d in self.collection.find({"user_id": user_id}).sort("due_date", 1)
        ]

    get_user_deadlines = get_all_deadlines

    def get_deadline_by_id(self, deadline_id, user_id):
        record = self.collection.find_one({"_id": ObjectId(deadline_id), "user_id": user_id})
        return serialize(record, self.storage) if record else None

    def update_deadline(self, deadline_id, data, user_id):
        updates = validate_fields(data, partial=True)
        if not updates:
            raise ValueError("No supported fields were supplied.")
        updates["updated_at"] = utcnow()
        return (
            self.collection.update_one(
                {"_id": ObjectId(deadline_id), "user_id": user_id}, {"$set": updates}
            ).matched_count
            > 0
        )

    def delete_deadline(self, deadline_id, user_id):
        return (
            self.collection.delete_one(
                {"_id": ObjectId(deadline_id), "user_id": user_id}
            ).deleted_count
            > 0
        )

    def get_deadlines_by_date(self, value, user_id):
        day = validate_date(value)
        return [
            serialize(d, self.storage)
            for d in self.collection.find({"user_id": user_id, "due_date": day})
        ]
