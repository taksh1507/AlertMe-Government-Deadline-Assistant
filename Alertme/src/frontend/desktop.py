"""Native desktop workspace. All network requests run through Qt's event loop."""

from datetime import date, timedelta
from pathlib import Path
from PyQt6.QtCore import Qt, QDate, QTimer, QUrl
from PyQt6.QtGui import QIcon, QColor, QTextCharFormat, QDesktopServices
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFrame,
    QLineEdit,
    QStackedWidget,
    QCheckBox,
    QFormLayout,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QTextEdit,
    QDateEdit,
    QCalendarWidget,
    QMessageBox,
    QFileDialog,
    QInputDialog,
)
from .api_client import ApiClient
from .theme import STYLE
from ..shared.exporting import as_csv, as_calendar

MARK = str(Path(__file__).parent / "assets" / "mark.svg")


def label(text="", name=None, wrap=False):
    result = QLabel(text)
    result.setTextFormat(Qt.TextFormat.PlainText)
    result.setWordWrap(wrap)
    if name:
        result.setObjectName(name)
        result.setProperty("tone", name)
    return result


def button(text, callback=None, primary=False, name=None):
    result = QPushButton(text)
    result.setCursor(Qt.CursorShape.PointingHandCursor)
    if name or primary:
        result.setObjectName(name or "primary")
    if primary:
        result.setProperty("primary", True)
    if callback:
        result.clicked.connect(callback)
    return result


def card(title=None):
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(14)
    if title:
        layout.addWidget(label(title, "sectionTitle"))
    return frame, layout


def remaining(item):
    try:
        days = (date.fromisoformat(item["due_date"]) - date.today()).days
    except (ValueError, KeyError):
        return "Date unavailable"
    if item.get("status") == "completed":
        return "Completed"
    return (
        "Today"
        if days == 0
        else f"{abs(days)} {'day' if abs(days) == 1 else 'days'} overdue"
        if days < 0
        else f"In {days} {'day' if days == 1 else 'days'}"
    )


def personal_path(item):
    return "/api/deadlines/" if item.get("storage") == "legacy" else "/api/personal-deadlines/"


class DeadlineEditor(QDialog):
    def __init__(self, owner, item=None, government=False):
        super().__init__(owner)
        self.owner, self.item, self.government = owner, item or {}, government
        self.setWindowTitle(
            ("Edit" if item else "New")
            + (" published deadline" if government else " personal deadline")
        )
        self.setMinimumWidth(470)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.addWidget(label(self.windowTitle(), "sectionTitle"))
        form = QFormLayout()
        form.setVerticalSpacing(14)
        self.title_input = QLineEdit(self.item.get("title", ""))
        self.title_input.setObjectName("deadline_title")
        self.title_input.setMaxLength(120)
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dd MMM yyyy")
        self.date_input.setDateRange(QDate(1900, 1, 1), QDate(2199, 12, 31))
        selected = QDate.fromString(self.item.get("due_date", ""), "yyyy-MM-dd")
        self.date_input.setDate(
            selected
            if selected.isValid()
            else owner.calendar.selectedDate()
            if owner.view == "Calendar"
            else QDate.currentDate().addDays(1)
        )
        self.date_input.setObjectName("deadline_date")
        self.priority = QComboBox()
        self.priority.addItems(["Low", "Medium", "High"])
        self.priority.setCurrentText(self.item.get("priority", "medium").title())
        self.priority.setObjectName("deadline_priority")
        self.description = QTextEdit()
        self.description.setAcceptRichText(False)
        self.description.setPlainText(self.item.get("description", ""))
        self.description.setFixedHeight(90)
        self.description.setObjectName("deadline_description")
        form.addRow("Title", self.title_input)
        form.addRow("Due date", self.date_input)
        form.addRow("Priority", self.priority)
        if government:
            self.department = QLineEdit(self.item.get("department", ""))
            self.department.setMaxLength(120)
            self.department.setObjectName("deadline_department")
            self.source = QLineEdit(self.item.get("source_url", ""))
            self.source.setPlaceholderText("https://official-source.example")
            self.source.setMaxLength(500)
            form.addRow("Department", self.department)
            form.addRow("Source URL", self.source)
        else:
            self.category = QComboBox()
            self.category.addItems(["Personal", "Education", "Finance", "Health", "Work", "Other"])
            self.category.setCurrentText(self.item.get("category", "Personal"))
            self.status = QComboBox()
            self.status.addItems(["Pending", "In progress", "Completed"])
            self.status.setCurrentText(
                self.item.get("status", "pending").replace("_", " ").capitalize()
            )
            self.reminder_days = QLineEdit(
                ", ".join(map(str, self.item.get("reminder_days", [7, 3, 1, 0])))
            )
            self.reminder_days.setMaxLength(30)
            self.reminder_days.setToolTip(
                "Days before the due date, separated by commas. 0 means the due date. Leave empty for no delivery reminders."
            )
            form.addRow("Category", self.category)
            form.addRow("Status", self.status)
            form.addRow("Reminder days", self.reminder_days)
        form.addRow("Notes", self.description)
        layout.addLayout(form)
        self.error = label("", "error", True)
        self.error.setObjectName("editor_error")
        layout.addWidget(self.error)
        actions = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.save_button = actions.button(QDialogButtonBox.StandardButton.Save)
        self.save_button.setObjectName("save_deadline")
        self.save_button.setProperty("primary", True)
        actions.accepted.connect(self.save)
        actions.rejected.connect(self.reject)
        layout.addWidget(actions)

    def save(self):
        if not self.title_input.text().strip():
            self.error.setText("Please enter a title.")
            return
        value = {
            "title": self.title_input.text().strip(),
            "due_date": self.date_input.date().toString("yyyy-MM-dd"),
            "description": self.description.toPlainText(),
            "priority": self.priority.currentText().lower(),
        }
        if self.government:
            value.update(department=self.department.text(), source_url=self.source.text())
        else:
            try:
                days = [int(n.strip()) for n in self.reminder_days.text().split(",") if n.strip()]
            except ValueError:
                self.error.setText("Use comma-separated whole numbers for reminder days.")
                return
            value.update(
                category=self.category.currentText(),
                status=self.status.currentText().lower().replace(" ", "_"),
                reminder_days=days,
            )
        prefix = (
            "/admin/api/government-deadlines"
            if self.government
            else personal_path(self.item).rstrip("/")
        )
        path = prefix + ("/" + self.item["id"] if self.item.get("id") else "")
        self.save_button.setEnabled(False)
        self.error.setText("Saving…")
        self.owner.api.request(
            "PUT" if self.item.get("id") else "POST",
            path,
            value,
            success=lambda _: self.saved(),
            failure=self.failed,
        )

    def saved(self):
        if not self.item and not self.government:
            self.owner.set_view("My deadlines")
        self.owner.refresh()
        self.owner.statusBar().showMessage("Deadline saved.", 5000)
        self.accept()

    def failed(self, message):
        self.save_button.setEnabled(True)
        self.error.setText(message)


class AlertMeWindow(QMainWindow):
    def __init__(self, api_url=None):
        super().__init__()
        self.setWindowTitle("AlertMe — Deadline workspace")
        self.setWindowIcon(QIcon(MARK))
        self.resize(1320, 880)
        self.setMinimumSize(960, 650)
        self.setStyleSheet(STYLE)
        self.api = ApiClient(api_url, self)
        self.api.session_expired.connect(self.session_expired)
        self.data = {
            "personal": [],
            "government": [],
            "notifications": [],
            "user": {},
            "delivery": {},
        }
        self.view = "Overview"
        self.refresh_serial = 0
        self.editor = None
        self.root = QStackedWidget()
        self.setCentralWidget(self.root)
        self.create_auth()
        self.create_workspace()
        self.root.setCurrentIndex(0)
        self.timer = QTimer(self)
        self.timer.setInterval(60000)
        self.timer.timeout.connect(self.auto_refresh)

    def create_auth(self):
        page = QWidget()
        row = QHBoxLayout(page)
        row.setContentsMargins(45, 40, 45, 40)
        row.setSpacing(50)
        hero = QFrame()
        hero.setObjectName("authHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(50, 45, 50, 45)
        hero_layout.addWidget(label("AlertMe", "brand"))
        hero_layout.addStretch()
        hero_layout.addWidget(label("A little ahead.\nA lot less to\nworry about.", "authHeading"))
        hero_layout.addSpacing(18)
        hero_layout.addWidget(
            label(
                "Keep important dates in sight.\nMake space for everything else.",
                "subtitle",
                True,
            )
        )
        hero_layout.addSpacing(35)
        note, content = card("Your next step, made clearer.")
        content.addWidget(
            label(
                "Personal plans. Published deadlines.\nOne calm place to stay on track.",
                "subtitle",
                True,
            )
        )
        hero_layout.addWidget(note)
        hero_layout.addStretch()
        hero_layout.addWidget(label("Native desktop + web. One connected workspace.", "caption"))
        row.addWidget(hero, 5)
        right = QWidget()
        column = QVBoxLayout(right)
        column.setContentsMargins(20, 30, 45, 30)
        column.setSpacing(14)
        column.addStretch()
        column.addWidget(label("WELCOME TO ALERTME", "eyebrow"))
        self.auth_title = label("Good to see you.", "heading", True)
        column.addWidget(self.auth_title)
        self.auth_subtitle = label("Sign in to pick up where you left off.", "subtitle", True)
        column.addWidget(self.auth_subtitle)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Your full name")
        self.name_input.setObjectName("signup_name")
        self.name_input.setAccessibleName("Full name")
        self.name_input.setMaxLength(80)
        self.name_input.hide()
        self.identifier = QLineEdit()
        self.identifier.setPlaceholderText("Email or phone")
        self.identifier.setObjectName("login_identifier")
        self.identifier.setAccessibleName("Email or phone")
        self.identifier.setMaxLength(254)
        self.phone = QLineEdit()
        self.phone.setPlaceholderText("Phone with country code (optional)")
        self.phone.setObjectName("signup_phone")
        self.phone.setAccessibleName("Phone number")
        self.phone.setMaxLength(16)
        self.phone.hide()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Password")
        self.password.setObjectName("login_password")
        self.password.setAccessibleName("Password")
        self.password.setMaxLength(128)
        self.admin_login = QCheckBox("Administrator sign-in")
        self.admin_login.setObjectName("admin_login")
        self.auth_error = label("", "error", True)
        self.auth_error.setObjectName("auth_error")
        self.signin = button("Sign in", self.authenticate, True, "signin_button")
        self.switch = button(
            "New here? Create an account", self.toggle_signup, name="switch_signup"
        )
        self.signup_mode = False
        for widget in (
            self.name_input,
            self.identifier,
            self.phone,
            self.password,
            self.admin_login,
            self.auth_error,
            self.signin,
            self.switch,
        ):
            column.addWidget(widget)
        self.password.returnPressed.connect(self.authenticate)
        column.addSpacing(12)
        column.addWidget(
            label(
                "Your desktop and browser use the same account.\nReminders can be enabled after contact verification.",
                "caption",
                True,
            )
        )
        column.addStretch()
        row.addWidget(right, 5)
        self.root.addWidget(page)

    def toggle_signup(self):
        self.signup_mode = not self.signup_mode
        self.name_input.setVisible(self.signup_mode)
        self.phone.setVisible(self.signup_mode)
        self.admin_login.setVisible(not self.signup_mode)
        self.admin_login.setChecked(False)
        self.auth_title.setText(
            "Make room for what matters." if self.signup_mode else "Good to see you."
        )
        self.signin.setText("Create account" if self.signup_mode else "Sign in")
        self.switch.setText(
            "Already have an account? Sign in"
            if self.signup_mode
            else "New here? Create an account"
        )
        self.identifier.setPlaceholderText("Email" if self.signup_mode else "Email or phone")
        self.auth_subtitle.setText(
            "Create your connected deadline workspace."
            if self.signup_mode
            else "Sign in to pick up where you left off."
        )
        self.auth_error.clear()

    def authenticate(self):
        if not self.identifier.text().strip() or not self.password.text():
            self.auth_error.setText("Enter your email and password to continue.")
            return
        if self.signup_mode:
            path = "/signup"
            payload = {
                "name": self.name_input.text(),
                "email": self.identifier.text().strip(),
                "phone": self.phone.text().strip(),
                "password": self.password.text(),
            }
        elif self.admin_login.isChecked():
            path, payload = (
                "/auth/api/admin/login",
                {
                    "email": self.identifier.text().strip(),
                    "password": self.password.text(),
                },
            )
        else:
            path, payload = (
                "/login",
                {
                    "identifier": self.identifier.text().strip(),
                    "password": self.password.text(),
                },
            )
        self.signin.setEnabled(False)
        self.auth_error.setText("Connecting…")
        self.api.request("POST", path, payload, self.signed_in, self.auth_failed)

    def signed_in(self, result):
        self.api.set_token(result["token"])
        self.data["user"] = result["user"]
        self.password.clear()
        self.auth_error.clear()
        self.signin.setEnabled(True)
        self.root.setCurrentIndex(1)
        self.timer.start()
        self.set_view("Government" if result["user"].get("is_admin") else "Overview")
        self.refresh()

    def auth_failed(self, message):
        self.signin.setEnabled(True)
        self.auth_error.setText(message)

    def session_expired(self):
        self.timer.stop()
        if self.signup_mode:
            self.toggle_signup()
        self.admin_login.setChecked(False)
        self.password.clear()
        self.identifier.clear()
        self.refresh_serial += 1
        if self.editor:
            self.editor.reject()
        self.data = {
            "personal": [],
            "government": [],
            "notifications": [],
            "user": {},
            "delivery": {},
        }
        self.root.setCurrentIndex(0)
        self.auth_error.setText("Your session ended. Sign in again to continue.")
        self.signin.setEnabled(True)

    def create_workspace(self):
        page = QWidget()
        page.setObjectName("workspace")
        root = QHBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(20, 30, 20, 22)
        side.setSpacing(8)
        side.addWidget(label("AlertMe", "brand"))
        side.addWidget(label("A LITTLE AHEAD, EVERY DAY", "caption"))
        side.addSpacing(38)
        side.addWidget(label("YOUR WORKSPACE", "eyebrow"))
        self.nav_buttons = {}
        for name in (
            "Overview",
            "My deadlines",
            "Government",
            "Calendar",
            "Reminders",
            "Settings",
        ):
            nav = button(
                name,
                lambda checked=False, target=name: self.set_view(target),
                name="nav",
            )
            nav.setCheckable(True)
            nav.setObjectName("nav_" + name.lower().replace(" ", "_"))
            nav.setStyleSheet(
                "QPushButton {text-align:left;border:0;background:transparent;padding:12px;color:#706981;} QPushButton:checked{background:#f0ecfb;color:#5946ad;font-weight:600;}"
            )
            side.addWidget(nav)
            self.nav_buttons[name] = nav
        side.addStretch()
        side.addWidget(label("Everything important,\na little more in focus.", "subtitle", True))
        side.addSpacing(22)
        self.account_label = label("Your workspace", "sectionTitle")
        side.addWidget(self.account_label)
        side.addWidget(button("Sign out", self.logout, name="logout_button"))
        root.addWidget(sidebar)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 26, 30, 20)
        layout.setSpacing(20)
        heading = QHBoxLayout()
        texts = QVBoxLayout()
        texts.addWidget(label("YOUR DEADLINE WORKSPACE", "eyebrow"))
        self.heading = label("A clearer view of what’s next.", "heading")
        self.subtitle = label("Stay on top of your plans, one step at a time.", "subtitle")
        texts.addWidget(self.heading)
        texts.addWidget(self.subtitle)
        heading.addLayout(texts, 1)
        self.refresh_button = button("Refresh", self.refresh, name="refresh_button")
        heading.addWidget(self.refresh_button)
        self.new_button = button("+ New deadline", self.new_deadline, True, "new_deadline")
        heading.addWidget(self.new_button)
        layout.addLayout(heading)
        self.notice = label("", "notice", True)
        self.notice.hide()
        layout.addWidget(self.notice)
        self.stats_container = QWidget()
        stats = QHBoxLayout(self.stats_container)
        stats.setContentsMargins(0, 0, 0, 0)
        stats.setSpacing(16)
        self.stats = {}
        for title in ("Upcoming", "Due this week", "Overdue", "Completed"):
            panel, body = card()
            body.addWidget(label(title, "statCaption"))
            value = label("0", "statValue")
            value.setObjectName("stat_" + title.lower().replace(" ", "_"))
            body.addWidget(value)
            self.stats[title] = value
            stats.addWidget(panel)
        layout.addWidget(self.stats_container)
        self.filters = QWidget()
        filter_row = QHBoxLayout(self.filters)
        filter_row.setContentsMargins(0, 0, 0, 0)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search deadlines or notes…")
        self.search.setAccessibleName("Search deadlines")
        self.search.setObjectName("deadline_search")
        self.search.setMaxLength(120)
        self.search.textChanged.connect(self.render)
        self.priority_filter = QComboBox()
        self.priority_filter.addItems(["All priorities", "High", "Medium", "Low"])
        self.priority_filter.currentTextChanged.connect(self.render)
        self.status_filter = QComboBox()
        self.status_filter.addItems(
            ["All statuses", "Pending", "In progress", "Completed", "Overdue"]
        )
        self.status_filter.currentTextChanged.connect(self.render)
        filter_row.addWidget(self.search, 1)
        filter_row.addWidget(self.priority_filter)
        filter_row.addWidget(self.status_filter)
        filter_row.addWidget(button("Export CSV", lambda: self.export("csv"), name="export_csv"))
        filter_row.addWidget(button("Calendar file", lambda: self.export("ics"), name="export_ics"))
        layout.addWidget(self.filters)
        self.body = QStackedWidget()
        self.table_page = QWidget()
        table_layout = QVBoxLayout(self.table_page)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_panel, table_body = card()
        self.table_title = label("Your deadlines", "sectionTitle")
        table_body.addWidget(self.table_title)
        self.table = QTableWidget(0, 5)
        self.table.setObjectName("deadlines_table")
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for index in range(1, 5):
            self.table.horizontalHeader().setSectionResizeMode(
                index, QHeaderView.ResizeMode.ResizeToContents
            )
        self.table.doubleClicked.connect(self.open_selected)
        self.table.itemSelectionChanged.connect(self.selection_actions)
        table_body.addWidget(self.table, 1)
        self.empty_label = label(
            "No deadlines here yet. Add your first deadline to get started.",
            "subtitle",
            True,
        )
        table_body.addWidget(self.empty_label)
        actions = QHBoxLayout()
        self.edit_button = button("Edit selected", self.open_selected, name="edit_selected")
        self.complete_button = button(
            "Mark completed", self.complete_selected, name="complete_selected"
        )
        self.delete_button = button("Delete selected", self.delete_selected, name="delete_selected")
        self.subscribe_button = button(
            "Subscribe / unsubscribe",
            self.subscribe_selected,
            name="subscribe_selected",
        )
        self.source_button = button("Open source", self.open_source)
        for item in (
            self.edit_button,
            self.complete_button,
            self.delete_button,
            self.subscribe_button,
            self.source_button,
        ):
            actions.addWidget(item)
        actions.addStretch()
        table_body.addLayout(actions)
        table_layout.addWidget(table_panel)
        self.body.addWidget(self.table_page)
        calendar_page = QWidget()
        calendar_layout = QHBoxLayout(calendar_page)
        calendar_layout.setContentsMargins(0, 0, 0, 0)
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(False)
        self.calendar.setMinimumWidth(380)
        self.calendar.setObjectName("deadline_calendar")
        self.calendar.selectionChanged.connect(self.render_calendar)
        calendar_layout.addWidget(self.calendar, 1)
        calendar_card, calendar_body = card("On this day")
        self.calendar_list = label("", "subtitle", True)
        self.calendar_list.setAlignment(Qt.AlignmentFlag.AlignTop)
        calendar_body.addWidget(self.calendar_list, 1)
        calendar_layout.addWidget(calendar_card, 1)
        self.body.addWidget(calendar_page)
        self.settings_page = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_page)
        self.settings_layout.setContentsMargins(0, 0, 0, 0)
        self.body.addWidget(self.settings_page)
        layout.addWidget(self.body, 1)
        root.addWidget(content, 1)
        self.root.addWidget(page)
        self.statusBar().showMessage("Connected workspace · Desktop and web share your account")

    def auto_refresh(self):
        if self.view != "Settings" and not (self.editor and self.editor.isVisible()):
            self.refresh()

    def refresh(self):
        if not self.api.token:
            return
        self.refresh_serial += 1
        serial = self.refresh_serial
        self.refresh_button.setEnabled(False)
        self.statusBar().showMessage("Refreshing deadlines…")

        def loaded(value):
            if serial != self.refresh_serial:
                return
            self.data = value
            self.refresh_button.setEnabled(True)
            self.notice.hide()
            self.render()
            self.statusBar().showMessage("Up to date · Refreshes every 60 seconds while open")

        def failed(message):
            if serial != self.refresh_serial:
                return
            self.refresh_button.setEnabled(True)
            self.notice.setText(message + " Your current view is retained. Use Refresh to retry.")
            self.notice.show()

        self.api.request("GET", "/api/workspace", success=loaded, failure=failed)

    def set_view(self, view):
        self.view = view
        self.search.clear()
        self.priority_filter.setCurrentIndex(0)
        self.status_filter.setCurrentIndex(0)
        self.render()

    def entries(self):
        if self.view == "Government" or (
            self.view == "Calendar" and self.data.get("user", {}).get("is_admin")
        ):
            return self.data.get("government", [])
        if self.view == "Reminders":
            return self.data.get("notifications", [])
        entries = self.data.get("personal", [])
        if self.view in ("Overview", "Calendar"):
            entries = entries + [d for d in self.data.get("government", []) if d.get("subscribed")]
        return entries

    def filtered(self):
        result = []
        query = self.search.text().lower()
        for item in self.entries():
            if (
                query
                not in (
                    item.get("title", "")
                    + " "
                    + item.get("description", "")
                    + " "
                    + item.get("department", "")
                ).lower()
            ):
                continue
            if (
                self.priority_filter.currentIndex()
                and item.get("priority") != self.priority_filter.currentText().lower()
            ):
                continue
            status = self.status_filter.currentText().lower().replace(" ", "_")
            if status == "overdue":
                if (
                    item.get("due_date", "9999") >= date.today().isoformat()
                    or item.get("status") == "completed"
                ):
                    continue
            elif self.status_filter.currentIndex() and item.get("status", "pending") != status:
                continue
            result.append(item)
        return sorted(result, key=lambda d: d.get("due_date", "9999"))

    def render(self, *args):
        if not hasattr(self, "table"):
            return
        admin = self.data.get("user", {}).get("is_admin", False)
        self.account_label.setText(self.data.get("user", {}).get("name", "Your workspace"))
        for name, item in self.nav_buttons.items():
            item.setChecked(name == self.view)
            item.setVisible(not admin or name in ("Government", "Calendar", "Settings"))
        headings = {
            "Overview": (
                "A clearer view of what’s next.",
                "Your important dates, all in one place.",
            ),
            "My deadlines": (
                "Make a little room for your plans.",
                "Add, organize and complete your personal deadlines.",
            ),
            "Government": (
                "Important dates. Clear next steps.",
                "Published by your administrator. Check the source for official details.",
            ),
            "Calendar": (
                "See the bigger picture.",
                "Your personal dates and subscribed deadlines, together.",
            ),
            "Reminders": (
                "A timely little nudge.",
                "Delivery history from the configured reminder worker.",
            ),
            "Settings": (
                "Make yourself at home.",
                "Your account and reminder preferences.",
            ),
        }
        self.heading.setText(headings[self.view][0])
        self.subtitle.setText(headings[self.view][1])
        self.new_button.setText("+ Publish deadline" if admin else "+ New deadline")
        self.new_button.setVisible(
            self.view not in ("Settings", "Reminders") and (not admin or self.view == "Government")
        )
        all_items = self.data.get("personal", []) + [
            d for d in self.data.get("government", []) if d.get("subscribed")
        ]
        active = [d for d in all_items if d.get("status") != "completed"]
        now = date.today().isoformat()
        next_week = (date.today() + timedelta(days=7)).isoformat()
        values = [
            sum(d.get("due_date", "") >= now for d in active),
            sum(now <= d.get("due_date", "") <= next_week for d in active),
            sum(d.get("due_date", now) < now for d in active),
            sum(d.get("status") == "completed" for d in all_items),
        ]
        for (name, widget), value in zip(self.stats.items(), values):
            widget.setText(str(value))
        self.stats_container.setVisible(self.view == "Overview" and not admin)
        is_calendar, is_settings = self.view == "Calendar", self.view == "Settings"
        self.filters.setVisible(not is_calendar and not is_settings)
        if is_calendar:
            self.body.setCurrentIndex(1)
            self.calendar.setDateTextFormat(QDate(), QTextCharFormat())
            for item in self.entries():
                selected = QDate.fromString(item.get("due_date", ""), "yyyy-MM-dd")
                if selected.isValid():
                    fmt = QTextCharFormat()
                    fmt.setBackground(QColor("#ede7fa"))
                    fmt.setForeground(QColor("#514182"))
                    self.calendar.setDateTextFormat(selected, fmt)
            self.render_calendar()
            return
        if is_settings:
            self.body.setCurrentIndex(2)
            self.render_settings()
            return
        self.body.setCurrentIndex(0)
        government, history = self.view == "Government", self.view == "Reminders"
        self.table_title.setText(
            "Published deadlines"
            if government
            else "Recent delivery attempts"
            if history
            else "What’s on your list"
        )
        self.table.setHorizontalHeaderLabels(
            ["Deadline", "Channel", "Due date", "Status", "Attempted"]
            if history
            else [
                "Deadline",
                "Department" if government else "Category",
                "Due date",
                "Priority",
                "Following" if government else "Status",
            ]
        )
        self.visible_rows = self.filtered()
        self.table.setRowCount(len(self.visible_rows))
        for row, item in enumerate(self.visible_rows):
            values = [
                item.get("title", ""),
                item.get("channel", "")
                if history
                else item.get("department" if government else "category", "Personal"),
                item.get("due_date", ""),
                item.get("status", "") if history else item.get("priority", "medium").title(),
                str(item.get("created_at", ""))[:16]
                if history
                else ("Subscribed" if item.get("subscribed") else "Not subscribed")
                if government
                else item.get("status", "pending").replace("_", " ").title(),
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setToolTip(item.get("description", "") if column == 0 else str(value))
                if column == 3 and not history:
                    cell.setForeground(
                        QColor(
                            {
                                "high": "#a44350",
                                "medium": "#8c682f",
                                "low": "#467457",
                            }.get(item.get("priority"), "#706981")
                        )
                    )
                self.table.setItem(row, column, cell)
            self.table.setRowHeight(row, 58)
        self.empty_label.setVisible(not self.visible_rows)
        self.empty_label.setText(
            "No delivery attempts yet. Enable a verified channel in Settings and run the reminder worker."
            if history
            else "No matching deadlines. Try different filters, or add a new deadline."
            if self.search.text()
            else "No deadlines here yet. Add your first deadline or follow a published deadline."
        )
        self.edit_button.setVisible(not history and (not government or admin))
        self.delete_button.setVisible(not history and (not government or admin))
        self.complete_button.setVisible(not government and not history and not admin)
        self.subscribe_button.setVisible(government and not admin)
        self.source_button.setVisible(government)
        self.selection_actions()

    def selection_actions(self):
        if not hasattr(self, "edit_button"):
            return
        row = self.table.currentRow()
        item = (
            self.visible_rows[row]
            if hasattr(self, "visible_rows") and 0 <= row < len(self.visible_rows)
            else None
        )
        personal = bool(item and item.get("storage") != "government")
        admin = self.data.get("user", {}).get("is_admin", False)
        self.edit_button.setEnabled(personal or bool(item and admin))
        self.delete_button.setEnabled(personal or bool(item and admin))
        self.complete_button.setEnabled(personal)
        self.subscribe_button.setEnabled(bool(item))
        self.source_button.setEnabled(
            bool(
                item
                and isinstance(item.get("source_url"), str)
                and item["source_url"].startswith("https://")
            )
        )

    def selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.visible_rows):
            self.statusBar().showMessage("Select a deadline first.", 5000)
            return None
        return self.visible_rows[row]

    def new_deadline(self):
        self.editor = DeadlineEditor(
            self, government=self.data.get("user", {}).get("is_admin", False)
        )
        self.editor.open()

    def open_selected(self, *args):
        item = self.selected()
        if not item or self.view == "Reminders":
            return
        if item.get("storage") == "government" and not self.data.get("user", {}).get("is_admin"):
            self.statusBar().showMessage(
                item.get("description") or "Open the source to review this published deadline.",
                10000,
            )
            return
        self.editor = DeadlineEditor(self, item, self.view == "Government")
        self.editor.open()

    def update_item(self, method, path, payload=None):
        self.api.request(
            method,
            path,
            payload,
            success=lambda _: self.refresh(),
            failure=lambda message: self.show_error(message),
        )

    def complete_selected(self):
        item = self.selected()
        if item and item.get("storage") != "government":
            self.update_item(
                "PUT",
                personal_path(item) + item["id"],
                {"status": "pending" if item.get("status") == "completed" else "completed"},
            )

    def delete_selected(self):
        item = self.selected()
        if not item:
            return
        if item.get("storage") == "government" and not self.data.get("user", {}).get("is_admin"):
            self.show_error("Published deadlines can only be removed by an administrator.")
            return
        if (
            QMessageBox.question(
                self,
                "Delete deadline",
                f"Delete “{item['title']}”? This cannot be undone.",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        prefix = (
            "/admin/api/government-deadlines/" if self.view == "Government" else personal_path(item)
        )
        self.update_item("DELETE", prefix + item["id"])

    def subscribe_selected(self):
        item = self.selected()
        if item:
            self.update_item(
                "POST",
                "/api/government-deadlines/" + item["id"] + "/subscribe",
                {"subscribed": not item.get("subscribed", False)},
            )

    def open_source(self):
        item = self.selected()
        if (
            item
            and isinstance(item.get("source_url"), str)
            and item["source_url"].startswith("https://")
        ):
            QDesktopServices.openUrl(QUrl(item["source_url"]))
        else:
            self.statusBar().showMessage(
                "No source link has been provided for this deadline.", 5000
            )

    def render_calendar(self):
        selected = self.calendar.selectedDate().toString("yyyy-MM-dd")
        entries = [d for d in self.entries() if d.get("due_date") == selected]
        self.calendar_list.setText(
            self.calendar.selectedDate().toString("dddd, d MMMM yyyy")
            + "\n\n"
            + (
                "\n\n".join(
                    f"{d['title']}\n{d.get('priority', 'medium').title()} priority · {remaining(d)}"
                    for d in entries
                )
                or "Nothing scheduled for this day. A little breathing room."
            )
        )

    def render_settings(self):
        while self.settings_layout.count():
            item = self.settings_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        user = self.data.get("user", {})
        panel, body = card("Account & reminders")
        body.addWidget(label(user.get("email", ""), "subtitle"))
        if user.get("is_admin"):
            body.addWidget(
                label(
                    "Publish deadlines from Government. Subscriber contact details are not displayed in the feed.",
                    "subtitle",
                    True,
                )
            )
            self.settings_layout.addWidget(panel)
            self.settings_layout.addStretch()
            return
        form = QFormLayout()
        self.profile_name = QLineEdit(user.get("name", ""))
        self.profile_name.setMaxLength(80)
        form.addRow("Display name", self.profile_name)
        body.addLayout(form)
        self.pref_email = QCheckBox("Email reminders")
        self.pref_sms = QCheckBox("SMS reminders")
        self.pref_email.setChecked(user.get("preferences", {}).get("email", False))
        self.pref_sms.setChecked(user.get("preferences", {}).get("sms", False))
        for channel, checkbox in (("email", self.pref_email), ("sms", self.pref_sms)):
            row = QHBoxLayout()
            row.addWidget(checkbox)
            verified = user.get("email_verified" if channel == "email" else "phone_verified", False)
            row.addWidget(label("Verified" if verified else "Verification needed", "caption"))
            row.addWidget(
                button(
                    "Verify contact",
                    lambda checked=False, c=channel: self.verify_contact(c),
                )
            )
            body.addLayout(row)
        body.addWidget(
            label(
                "External delivery requires configured providers and verified contacts. A separate reminder worker must be running. Reminders never submit an application or make a payment.",
                "subtitle",
                True,
            )
        )
        body.addWidget(button("Save preferences", self.save_preferences, True, "save_preferences"))
        self.settings_layout.addWidget(panel)
        help_panel, help_body = card("A few useful things to know")
        help_body.addWidget(
            label(
                "Add personal deadlines from any view. Double-click a row to edit it. Follow a published deadline to include it in your calendar. CSV and calendar-file exports contain the current filtered list. The native app refreshes every minute while open.",
                "subtitle",
                True,
            )
        )
        help_body.addWidget(button("Change password", self.change_password, name="change_password"))
        self.settings_layout.addWidget(help_panel)
        self.settings_layout.addStretch()

    def change_password(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Change password")
        dialog.setMinimumWidth(430)
        layout = QFormLayout(dialog)
        layout.setContentsMargins(25, 25, 25, 25)
        current = QLineEdit()
        current.setEchoMode(QLineEdit.EchoMode.Password)
        current.setMaxLength(128)
        replacement = QLineEdit()
        replacement.setEchoMode(QLineEdit.EchoMode.Password)
        replacement.setMaxLength(128)
        layout.addRow("Current password", current)
        layout.addRow("New password", replacement)
        error = label("Use 10–128 characters, including a letter and a number.", "subtitle", True)
        layout.addRow(error)
        actions = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        actions.rejected.connect(dialog.reject)

        def save():
            actions.button(QDialogButtonBox.StandardButton.Save).setEnabled(False)

            def done(result):
                dialog.accept()
                self.api.clear()
                self.session_expired()
                self.auth_error.setText("Password changed. Sign in again.")

            def failed(message):
                actions.button(QDialogButtonBox.StandardButton.Save).setEnabled(True)
                error.setText(message)

            self.api.request(
                "POST",
                "/api/me/password",
                {
                    "current_password": current.text(),
                    "new_password": replacement.text(),
                },
                done,
                failed,
            )

        actions.accepted.connect(save)
        layout.addRow(actions)
        self.password_dialog = dialog
        dialog.open()

    def save_preferences(self):
        self.update_item(
            "PUT",
            "/api/me",
            {
                "name": self.profile_name.text(),
                "preferences": {
                    "email": self.pref_email.isChecked(),
                    "sms": self.pref_sms.isChecked(),
                },
            },
        )

    def verify_contact(self, channel):
        def sent(result):
            code, accepted = QInputDialog.getText(
                self,
                "Verify contact",
                "Enter the 6-digit code sent to your " + channel + ":",
            )
            if accepted:
                self.update_item(
                    "PUT",
                    "/api/me/verification",
                    {"channel": channel, "code": code.strip()},
                )

        self.api.request(
            "POST", "/api/me/verification", {"channel": channel}, sent, self.show_error
        )

    def show_error(self, message):
        self.notice.setText(message)
        self.notice.show()

    def export(self, kind):
        if self.view == "Reminders":
            self.show_error("Switch to a deadline list to export deadlines.")
            return
        entries = self.filtered()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export deadlines",
            "alertme-deadlines." + kind,
            "CSV files (*.csv)" if kind == "csv" else "Calendar files (*.ics)",
        )
        if path:
            try:
                Path(path).write_text(
                    as_csv(entries) if kind == "csv" else as_calendar(entries),
                    encoding="utf-8",
                    newline="",
                )
                self.statusBar().showMessage("Export saved.", 5000)
            except OSError:
                self.show_error("The export could not be saved. Choose another location.")

    def logout(self):
        def done(_):
            self.api.clear()
            self.session_expired()
            self.auth_error.setText("You have signed out.")

        self.api.request("POST", "/logout", {}, done, self.show_error)

    def closeEvent(self, event):
        self.timer.stop()
        self.api.clear()
        super().closeEvent(event)
