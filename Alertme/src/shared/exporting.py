import csv
import io
from datetime import date, datetime, timezone, timedelta


def as_csv(entries):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["Title", "Due date", "Priority", "Status", "Category", "Type"])
    for item in entries:
        values = [
            item.get(k, "")
            for k in ("title", "due_date", "priority", "status", "category", "storage")
        ]
        writer.writerow(
            [
                "'" + str(v) if str(v).lstrip().startswith(("=", "+", "-", "@")) else str(v)
                for v in values
            ]
        )
    return stream.getvalue()


def as_calendar(entries):
    def escape(value):
        return (
            str(value)
            .replace("\\", "\\\\")
            .replace("\r", "")
            .replace("\n", "\\n")
            .replace(",", "\\,")
            .replace(";", "\\;")
        )

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AlertMe//Deadline workspace//EN",
        "CALSCALE:GREGORIAN",
    ]
    for item in entries:
        try:
            due = date.fromisoformat(item["due_date"])
        except (KeyError, ValueError, TypeError):
            continue
        lines += [
            "BEGIN:VEVENT",
            f"UID:{item.get('storage', 'main')}-{item['id']}@alertme.local",
            "DTSTAMP:" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "DTSTART;VALUE=DATE:" + due.strftime("%Y%m%d"),
            "DTEND;VALUE=DATE:" + (due + timedelta(days=1)).strftime("%Y%m%d"),
            "SUMMARY:" + escape(item.get("title", "")),
            "DESCRIPTION:" + escape(item.get("description", "")),
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    folded = []
    for line in lines:
        buffer = ""
        for char in line:
            if len((buffer + char).encode("utf-8")) > 74:
                folded.append(buffer)
                buffer = " "
            buffer += char
        folded.append(buffer)
    return "\r\n".join(folded) + "\r\n"
