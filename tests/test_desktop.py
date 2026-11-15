import threading
import os
from datetime import date, timedelta
from pathlib import Path
import pytest
import requests
from werkzeug.serving import make_server
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import QLineEdit, QDialogButtonBox
from Alertme.src.frontend.desktop import AlertMeWindow
from .conftest import register


@pytest.fixture
def api_server(backend):
    server = make_server("127.0.0.1", 0, backend, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join(timeout=5)


@pytest.fixture
def window(qtbot, api_server):
    result = AlertMeWindow(api_server)
    qtbot.addWidget(result)
    result.show()
    return result


def sign_in(
    qtbot,
    window,
    email="owner@example.test",
    password="Local-test-password123",
    admin=False,
):
    window.identifier.setText(email)
    window.password.setText(password)
    window.admin_login.setChecked(admin)
    qtbot.mouseClick(window.signin, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(
        lambda: window.root.currentIndex() == 1 and window.refresh_button.isEnabled(),
        timeout=10000,
    )


def save_dialog(qtbot, window, title="Native deadline"):
    editor = window.editor
    editor.title_input.setText(title)
    editor.description.setPlainText("Created through the native desktop application.")
    qtbot.mouseClick(editor.save_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(
        lambda: not editor.isVisible() and window.refresh_button.isEnabled(),
        timeout=10000,
    )


def test_native_signup_and_full_deadline_workflow(qtbot, window, backend):
    qtbot.mouseClick(window.switch, Qt.MouseButton.LeftButton)
    window.name_input.setText("Native Account")
    window.identifier.setText("native@example.test")
    window.password.setText("Local-test-password123")
    qtbot.mouseClick(window.signin, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(
        lambda: window.root.currentIndex() == 1 and window.refresh_button.isEnabled(),
        timeout=10000,
    )
    qtbot.mouseClick(window.new_button, Qt.MouseButton.LeftButton)
    save_dialog(qtbot, window)
    assert window.table.rowCount() == 1
    window.table.selectRow(0)
    qtbot.mouseClick(window.edit_button, Qt.MouseButton.LeftButton)
    save_dialog(qtbot, window, "Updated native deadline")
    assert window.table.item(0, 0).text() == "Updated native deadline"
    window.table.selectRow(0)
    qtbot.mouseClick(window.complete_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: window.data["personal"][0]["status"] == "completed", timeout=10000)
    window.search.setText("nothing here")
    assert window.table.rowCount() == 0
    window.search.clear()
    assert window.table.rowCount() == 1
    qtbot.mouseClick(window.nav_buttons["Calendar"], Qt.MouseButton.LeftButton)
    item = window.data["personal"][0]
    window.calendar.setSelectedDate(QDate.fromString(item["due_date"], "yyyy-MM-dd"))
    assert "Updated native deadline" in window.calendar_list.text()
    window.logout()
    qtbot.waitUntil(lambda: window.root.currentIndex() == 0, timeout=10000)
    assert not window.api.token
    assert not window.signup_mode
    assert window.data["personal"] == []


def test_native_login_rejects_bad_password_then_recovers(qtbot, window, client):
    register(client)
    window.identifier.setText("owner@example.test")
    window.password.setText("Wrong-password123")
    qtbot.mouseClick(window.signin, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: window.signin.isEnabled(), timeout=10000)
    assert "incorrect" in window.auth_error.text()
    assert window.root.currentIndex() == 0
    sign_in(qtbot, window)
    assert window.account_label.text() == "Test Owner"


def test_native_and_http_client_share_the_same_records(qtbot, window, client, api_server):
    account, headers = register(client)
    sign_in(qtbot, window)
    response = requests.post(
        api_server + "/api/personal-deadlines",
        json={
            "title": "Created in another client",
            "due_date": date.today().isoformat(),
            "priority": "medium",
        },
        headers=headers,
        timeout=5,
    )
    assert response.status_code == 201
    window.refresh()
    qtbot.waitUntil(lambda: window.table.rowCount() == 1, timeout=10000)
    assert window.table.item(0, 0).text() == "Created in another client"
    window.table.selectRow(0)
    window.open_selected()
    save_dialog(qtbot, window, "Edited on desktop")
    result = requests.get(api_server + "/api/personal-deadlines", headers=headers, timeout=5)
    assert result.json()[0]["title"] == "Edited on desktop"


def test_native_forms_keep_draft_after_api_validation_error(qtbot, window, client):
    register(client)
    sign_in(qtbot, window)
    window.new_deadline()
    editor = window.editor
    editor.title_input.setText("Keep my draft")
    editor.reminder_days.setText("99")
    qtbot.mouseClick(editor.save_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: editor.save_button.isEnabled(), timeout=10000)
    assert editor.isVisible()
    assert "reminder" in editor.error.text().lower()
    assert editor.title_input.text() == "Keep my draft"
    assert window.table.rowCount() == 0
    editor.reminder_days.setText("1,0")
    save_dialog(qtbot, window, "Keep my draft")
    assert window.table.rowCount() == 1


def test_native_admin_publishes_and_personal_account_subscribes(qtbot, window, client):
    register(client)
    sign_in(qtbot, window, "admin@example.test", "Admin-test-password123", True)
    assert window.view == "Government"
    window.new_deadline()
    editor = window.editor
    editor.title_input.setText("Scholarship applications")
    editor.department.setText("Education")
    editor.source.setText("https://example.gov/scholarship")
    qtbot.mouseClick(editor.save_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: not editor.isVisible() and window.table.rowCount() == 1, timeout=10000)
    window.logout()
    qtbot.waitUntil(lambda: window.root.currentIndex() == 0, timeout=10000)
    sign_in(qtbot, window)
    window.set_view("Government")
    window.table.selectRow(0)
    qtbot.mouseClick(window.subscribe_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: window.data["government"][0]["subscribed"], timeout=10000)
    window.set_view("Calendar")
    day = window.data["government"][0]["due_date"]
    window.calendar.setSelectedDate(QDate.fromString(day, "yyyy-MM-dd"))
    assert "Scholarship applications" in window.calendar_list.text()


def test_native_renders_laptop_sizes_with_live_fixture_data(qtbot, window, client, tmp_path):
    account, headers = register(client)
    names = [
        "Renew identity documents",
        "Submit scholarship application",
        "Review insurance renewal",
        "Prepare tax documents",
        "Medical appointment",
        "Course registration",
        "Update address details",
    ]
    for index, title in enumerate(names):
        result = client.post(
            "/api/personal-deadlines",
            json={
                "title": title,
                "due_date": (date.today() + timedelta(days=index - 1)).isoformat(),
                "priority": ["high", "medium", "low"][index % 3],
                "category": ["Personal", "Education", "Finance"][index % 3],
            },
            headers=headers,
        )
        assert result.status_code == 201
    sign_in(qtbot, window)
    directory = Path(os.environ.get("ALERTME_SCREENSHOT_DIR", str(tmp_path / "screenshots")))
    directory.mkdir(parents=True, exist_ok=True)
    for width, height in [(1440, 960), (1024, 768)]:
        window.resize(width, height)
        qtbot.wait(100)
        assert window.width() == width
        assert window.table.rowCount() == 7
        window.grab().save(str(directory / f"overview-{width}.png"))
    window.set_view("Calendar")
    window.grab().save(str(directory / "calendar.png"))


def test_native_password_change_requires_a_new_login(qtbot, window, client):
    register(client)
    sign_in(qtbot, window)
    old = window.api.token
    window.set_view("Settings")
    window.change_password()
    dialog = window.password_dialog
    fields = dialog.findChildren(QLineEdit)
    fields[0].setText("Local-test-password123")
    fields[1].setText("New-native-password123")
    actions = dialog.findChild(QDialogButtonBox)
    qtbot.mouseClick(
        actions.button(QDialogButtonBox.StandardButton.Save), Qt.MouseButton.LeftButton
    )
    qtbot.waitUntil(lambda: window.root.currentIndex() == 0, timeout=10000)
    assert client.get("/api/me", headers={"Authorization": "Bearer " + old}).status_code == 401
    assert (
        client.post(
            "/login",
            json={
                "identifier": "owner@example.test",
                "password": "New-native-password123",
            },
        ).status_code
        == 200
    )


def test_native_exports_write_real_csv_and_calendar_files(
    qtbot, window, client, tmp_path, monkeypatch
):
    from PyQt6.QtWidgets import QFileDialog

    _, headers = register(client)
    client.post(
        "/api/personal-deadlines",
        json={
            "title": "Export this deadline",
            "due_date": "2026-12-01",
            "priority": "high",
        },
        headers=headers,
    )
    sign_in(qtbot, window)
    window.set_view("My deadlines")
    for kind in ("csv", "ics"):
        target = tmp_path / f"export.{kind}"
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(target), "")
        )
        window.export(kind)
        assert target.exists()
        assert "Export this deadline" in target.read_text()
