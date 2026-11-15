from Alertme.src.shared.exporting import as_csv, as_calendar


def test_csv_quotes_text_and_preserves_records():
    value = as_csv(
        [
            {
                "id": "one",
                "title": '=HYPERLINK("https://example.test")',
                "due_date": "2026-11-15",
                "priority": "high",
            }
        ]
    )
    assert "'=HYPERLINK" in value
    assert "2026-11-15" in value


def test_calendar_exports_all_day_dates_with_exclusive_end_and_utf8_folding():
    value = as_calendar(
        [
            {
                "id": "one",
                "storage": "main",
                "title": "日本語" * 60,
                "description": "One; two, three\nnext",
                "due_date": "2024-02-29",
            }
        ]
    )
    assert "DTSTART;VALUE=DATE:20240229" in value
    assert "DTEND;VALUE=DATE:20240301" in value
    assert "One\\; two\\, three\\nnext" in value
    assert all(len(line.encode()) <= 74 for line in value.split("\r\n"))
    assert "BEGIN:VEVENT" in value and "END:VEVENT" in value
