"""Explicit reminder worker for configured email/SMS delivery."""

import argparse
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from ..models.deadline import utcnow


class DeadlineScanner:
    def __init__(self, app):
        self.app = app
        self.db = app.extensions["database"]
        self.legacy = app.extensions["legacy_database"]
        self.service = app.extensions["notifier"]

    def scan_deadlines(self, today=None):
        today = today or datetime.now(ZoneInfo(os.getenv("APP_TIMEZONE", "UTC"))).date()
        due = [
            (record, "main")
            for record in self.db.deadlines.find({"status": {"$nin": ["completed", "Completed"]}})
        ]
        if self.db.name != self.legacy.name:
            due += [
                (record, "legacy")
                for record in self.legacy.deadlines.find(
                    {"status": {"$nin": ["completed", "Completed"]}}
                )
            ]
        for item, source in due:
            self.process(
                item,
                item.get("user_id"),
                source,
                item.get("reminder_days", [7, 3, 1, 0]),
                today,
            )
        for subscription in self.db.subscriptions.find():
            if not ObjectId.is_valid(subscription.get("deadline_id", "")):
                continue
            item = self.db.government_deadlines.find_one(
                {"_id": ObjectId(subscription["deadline_id"])}
            )
            if item:
                self.process(
                    item,
                    subscription["user_id"],
                    "government",
                    subscription.get("reminder_days", [7, 3, 1, 0]),
                    today,
                )

    def process(self, item, user_id, source, reminder_days, today):
        if not ObjectId.is_valid(user_id or ""):
            return
        user = self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return
        try:
            days = (datetime.strptime(item["due_date"], "%Y-%m-%d").date() - today).days
        except (ValueError, KeyError, TypeError):
            return
        if days not in reminder_days:
            return
        occurrence = f"{user_id}:{source}:{item['_id']}:{item['due_date']}:{days}"
        for channel in ("email", "sms"):
            verified = user.get("email_verified" if channel == "email" else "phone_verified")
            if not verified or not user.get("preferences", {}).get(channel):
                continue
            claim = {
                "occurrence": occurrence,
                "channel": channel,
                "user_id": user_id,
                "title": item.get("title", ""),
                "due_date": item["due_date"],
                "status": "sending",
                "created_at": utcnow(),
                "updated_at": utcnow(),
            }
            try:
                result = self.db.notification_deliveries.insert_one(claim)
            except DuplicateKeyError:
                continue
            subject = f"AlertMe reminder: {item['title']}"
            message = f"{item['title']} is due on {item['due_date']} ({days} days remaining).\n\n{item.get('description', '')}\n\nOpen AlertMe to review the details."
            try:
                success = (
                    self.service.send_email_notification(user["email"], subject, message)
                    if channel == "email"
                    else self.service.send_sms_notification(user["phone"], message)
                )
            except Exception:
                success = False
            self.db.notification_deliveries.update_one(
                {"_id": result.inserted_id},
                {
                    "$set": {
                        "status": "sent" if success else "failed",
                        "updated_at": utcnow(),
                    }
                },
            )


def main():
    from ..app import create_app

    parser = argparse.ArgumentParser(description="Deliver due AlertMe reminders.")
    parser.add_argument("--once", action="store_true", help="Scan once, then exit.")
    parser.add_argument("--interval", type=int, default=300)
    args = parser.parse_args()
    if not 30 <= args.interval <= 86400:
        parser.error("interval must be between 30 and 86400 seconds")
    app = create_app()
    scanner = DeadlineScanner(app)
    try:
        while True:
            scanner.scan_deadlines()
            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        app.extensions["mongo"].close()


if __name__ == "__main__":
    main()
