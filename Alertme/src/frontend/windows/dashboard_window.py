from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLabel, QFrame, QStackedWidget,
                            QCalendarWidget, QListWidget, QListWidgetItem,
                            QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
                            QSpacerItem, QSizePolicy, QCheckBox, QGridLayout,
                            QDialog, QMessageBox, QProgressBar, QGraphicsOpacityEffect,
                            QComboBox, QFormLayout, QMenu)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QSize, QDate, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPointF
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPalette, QTextCharFormat, QFont, QPainter, QPen
import requests
from datetime import datetime, timedelta
import sys
from functools import lru_cache
import threading
import time
import math

class DeadlineDialog(QDialog):
    def __init__(self, parent=None, deadline_data=None, token=None):
        super().__init__(parent)
        self.setModal(True)
        self.deadline_data = deadline_data or {}
        self.token = token
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Add/Edit Deadline")
        layout = QFormLayout(self)

        self.title_input = QLineEdit(self.deadline_data.get('title', ''))
        layout.addRow("Title:", self.title_input)

        self.description_input = QLineEdit(self.deadline_data.get('description', ''))
        layout.addRow("Description:", self.description_input)

        self.due_date_label = QLabel(self.deadline_data.get('due_date', QDate.currentDate().toString("yyyy-MM-dd")))
        self.due_date_calendar = QCalendarWidget()
        self.due_date_calendar.setGridVisible(True)
        if self.deadline_data.get('due_date'):
            due_date = QDate.fromString(self.deadline_data['due_date'], "yyyy-MM-dd")
            if due_date.isValid():
                self.due_date_calendar.setSelectedDate(due_date)
        else:
            self.due_date_calendar.setSelectedDate(QDate.currentDate())
        self.due_date_calendar.clicked.connect(self.update_due_date_label)
        layout.addRow("Due Date:", self.due_date_label)
        layout.addRow(self.due_date_calendar)

        self.priority_input = QComboBox()
        self.priority_input.addItems(["High", "Medium", "Low"])
        priority = self.deadline_data.get('priority', 'Medium')
        self.priority_input.setCurrentText(priority.capitalize())
        layout.addRow("Priority:", self.priority_input)

        self.status_input = QLineEdit(self.deadline_data.get('status', 'Pending'))
        self.status_input.setVisible(bool(self.deadline_data))
        layout.addRow("Status:", self.status_input)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addRow(buttons)

    def update_due_date_label(self, date):
        self.due_date_label.setText(date.toString("yyyy-MM-dd"))

    def get_data(self):
        return {
            'title': self.title_input.text(),
            'description': self.description_input.text(),
            'due_date': self.due_date_label.text(),
            'status': self.status_input.text() if self.deadline_data else 'Pending',
            'priority': self.priority_input.currentText()
        }

class PieChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.high = 0
        self.medium = 0
        self.low = 0
        self.setMinimumSize(200, 200)

    def set_data(self, high, medium, low):
        self.high = high
        self.medium = medium
        self.low = low
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        total = max(self.high + self.medium + self.low, 1)
        
        rect = self.rect().adjusted(10, 10, -10, -10)
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2
        
        start_angle = 0
        colors = [QColor("#ef4444"), QColor("#f59e0b"), QColor("#10b981")]
        values = [self.high, self.medium, self.low]
        labels = ["High", "Medium", "Low"]

        for i, (value, color) in enumerate(zip(values, colors)):
            span = int((value / total) * 5760)  # 5760 = 360 degrees in 16ths
            painter.setBrush(color)
            painter.drawPie(rect, start_angle, span)
            start_angle += span

        # Legend
        painter.setFont(QFont("Segoe UI", 10))
        for i, (label, color) in enumerate(zip(labels, colors)):
            painter.setPen(QPen(color))
            painter.drawText(10, 20 + i * 20, f"{label}: {values[i]}")

class DashboardWindow(QMainWindow):
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data or {}
        self.dark_mode = False
        self.setWindowTitle("AlertMe Dashboard")
        self.showMaximized()
        
        self.request_timeout = 10
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.user_data.get("token", "")}',
            'Content-Type': 'application/json'
        })
        
        self.data_cache = {
            'personal_deadlines': [],
            'govt_deadlines': [],
            'last_updated': 0,
            'govt_last_updated': None
        }
        self.cache_timeout = 300
        
        self.predefined_questions = [
            "How do I add a new deadline?",
            "How do I subscribe to government deadlines?",
            "How do I use the calendar view?",
            "Can I edit my deadlines?",
            "How do I get notifications?",
            "Show my deadlines",  # New question
            "Subscribe to a deadline",  # New question
            "Unsubscribe from a deadline"  # New question
        ]
        
        self.chatbot_responses = {
            "how do i add a new deadline?": "To add a new deadline:\n1. Click the '➕ Add New Deadline' button\n2. Fill in the deadline details\n3. Click Save",
            "how do i subscribe to government deadlines?": "To subscribe to government deadlines:\n1. Go to the Deadlines tab\n2. Find the government deadline\n3. Check the 'Subscribe' checkbox",
            "how do i use the calendar view?": "The calendar view shows:\n• Blue: Deadline dates\n• Red: 1-day reminders\n• Orange: 15-day reminders\n• Green: 30-day reminders\nClick any date to see related deadlines.",
            "can i edit my deadlines?": "Yes! To edit a deadline:\n1. Go to the Deadlines tab\n2. Find your deadline\n3. Click the '✏️ Edit' button\n4. Update the details and save",
            "how do i get notifications?": "The system will notify you:\n• 30 days before deadline\n• 15 days before deadline\n• 1 day before deadline\n• On the deadline day",
            "show my deadlines": "",  # Will be dynamically handled
            "subscribe to a deadline": "",  # Will be dynamically handled
            "unsubscribe from a deadline": ""  # Will be dynamically handled
        }

        self.init_ui()
        
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(300000)
        self.is_loading = False
        
        self.load_dashboard_data_async()
        self.apply_entry_animation()

    def apply_entry_animation(self):
        try:
            self.opacity_effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(self.opacity_effect)
            self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
            self.animation.setDuration(500)
            self.animation.setStartValue(0)
            self.animation.setEndValue(1)
            self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
            self.animation.start()
        except Exception as e:
            print(f"Animation error: {str(e)}")

    def init_ui(self):
        try:
            main_widget = QWidget()
            self.setCentralWidget(main_widget)
            main_layout = QHBoxLayout(main_widget)
            main_layout.setSpacing(0)
            main_layout.setContentsMargins(0, 0, 0, 0)

            nav_frame = QFrame()
            nav_frame.setObjectName("navFrame")
            nav_frame.setMaximumWidth(280)
            nav_layout = QVBoxLayout(nav_frame)
            nav_layout.setSpacing(10)
            nav_layout.setContentsMargins(20, 20, 20, 20)

            self.profile_widget = QWidget()
            self.profile_widget.setObjectName("profileWidget")
            profile_layout = QVBoxLayout(self.profile_widget)
            
            self.avatar_label = QLabel("👤")
            self.avatar_label.setFont(QFont("Segoe UI", 48))
            self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.avatar_label.setFixedSize(100, 100)
            
            self.welcome_label = QLabel(f"Welcome, {self.user_data.get('name', 'User')}")
            self.welcome_label.setObjectName("welcome")
            self.welcome_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
            
            self.email_label = QLabel(self.user_data.get('email', ''))
            self.email_label.setObjectName("email")
            self.email_label.setWordWrap(True)
            
            profile_layout.addWidget(self.avatar_label)
            profile_layout.addWidget(self.welcome_label)
            profile_layout.addWidget(self.email_label)
            nav_layout.addWidget(self.profile_widget)

            self.nav_buttons = []
            nav_items = [
                ("🏠 Dashboard", self.show_dashboard),
                ("📅 Deadlines", self.show_deadlines),
                ("📆 Calendar", self.show_calendar),
                ("📊 Analytics", self.show_analytics),
                ("🤖 Chatbot", self.show_chatbot),
                ("⚙️ Settings", self.show_settings),
                ("🚪 Logout", self.handle_logout)
            ]
            
            for text, handler in nav_items:
                btn = QPushButton(text)
                btn.setObjectName("navBtn")
                btn.setCheckable(True)
                btn.clicked.connect(handler)
                btn.setMinimumHeight(50)
                self.nav_buttons.append(btn)
                nav_layout.addWidget(btn)
            
            nav_layout.addStretch()
            main_layout.addWidget(nav_frame)

            self.content_area = QStackedWidget()
            self.content_area.setObjectName("contentArea")
            main_layout.addWidget(self.content_area)
            
            self.loading_label = QLabel("Loading...", self)
            self.loading_label.setObjectName("loadingLabel")
            self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.loading_label.setVisible(False)
            
            self.init_dashboard_page()
            self.init_deadlines_page()
            self.init_calendar_page()
            self.init_analytics_page()
            self.init_chatbot_page()
            self.init_settings_page()
            
            self.show_dashboard()
            self.apply_theme()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"UI Initialization failed: {str(e)}")

    def apply_theme(self):
        stylesheet = """
            QMainWindow { background-color: #f8fafc; }
            #navFrame { background-color: #1e3a8a; border-right: 1px solid #e2e8f0; }
            #profileWidget { background-color: rgba(255, 255, 255, 0.1); border-radius: 15px; padding: 15px; }
            #welcome { color: #ffffff; font-family: 'Segoe UI'; padding: 5px; }
            #email { color: #dbeafe; font-size: 14px; padding: 5px; }
            QPushButton#navBtn { background-color: transparent; color: #dbeafe; border: none; border-radius: 8px; padding: 12px 20px; font-size: 16px; font-family: 'Segoe UI'; text-align: left; }
            QPushButton#navBtn:hover { background-color: rgba(255, 255, 255, 0.1); }
            QPushButton#navBtn:checked { background-color: #3b82f6; color: #ffffff; }
            #contentArea { padding: 20px; background-color: #ffffff; }
            QLabel#pageHeader { color: #1e3a8a; font-size: 28px; font-weight: bold; }
            QFrame#card { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 15px; padding: 20px; }
            QFrame#card QLabel { color: #1e40af; }
            QProgressBar { border: 2px solid #e2e8f0; border-radius: 5px; background-color: #f1f5f9; text-align: center; }
            QProgressBar::chunk { background-color: #3b82f6; }
            QLineEdit { background-color: #ffffff; color: #1e40af; border: 2px solid #e2e8f0; padding: 12px; border-radius: 8px; }
            QComboBox { background-color: #ffffff; color: #1e40af; border: 2px solid #e2e8f0; padding: 8px; border-radius: 8px; }
            QComboBox::drop-down { border: none; }
            QComboBox::down-arrow { width: 10px; height: 10px; }
            QComboBox QAbstractItemView { background-color: #ffffff; color: #1e40af; selection-background-color: #e2e8f0; }
            QListWidget { background-color: #ffffff; border: 1px solid #e2e8f0; color: #1e40af; padding: 10px; border-radius: 8px; }
            QListWidget::item { padding: 5px; }
            QPushButton#actionBtn { 
                background-color: #3b82f6; 
                color: #ffffff; 
                border: none; 
                border-radius: 8px; 
                padding: 6px 12px; 
                font-size: 10px; 
                min-width: 50px; 
                min-height: 20px; 
                margin: 4px;
                text-align: center;
                font-weight: bold;
            }
            QPushButton#actionBtn:hover { 
                background-color: #1d4ed8;
            }
            QPushButton#actionBtn:pressed { 
                background-color: #1e40af;
            }
            QMenu { 
                background-color: #ffffff; 
                border: 1px solid #e2e8f0; 
                border-radius: 8px; 
                padding: 5px; 
            }
            QMenu::item { 
                padding: 5px 20px; 
                color: #1e40af; 
            }
            QMenu::item:selected { 
                background-color: #e2e8f0; 
            }
        """ if not self.dark_mode else """
            QMainWindow { background-color: #1e293b; }
            #navFrame { background-color: #0f172a; border-right: 1px solid #334155; }
            #profileWidget { background-color: rgba(255, 255, 255, 0.03); border-radius: 15px; padding: 15px; }
            #welcome { color: #f1f5f9; font-family: 'Segoe UI'; padding: 5px; }
            #email { color: #cbd5e1; font-size: 14px; padding: 5px; }
            QPushButton#navBtn { background-color: transparent; color: #cbd5e1; border: none; border-radius: 8px; padding: 12px 20px; font-size: 16px; font-family: 'Segoe UI'; text-align: left; }
            QPushButton#navBtn:hover { background-color: rgba(255, 255, 255, 0.05); }
            QPushButton#navBtn:checked { background-color: #3b82f6; color: #ffffff; }
            #contentArea { padding: 20px; background-color: #1e293b; }
            QLabel#pageHeader { color: #f1f5f9; font-size: 28px; font-weight: bold; }
            QFrame#card { background-color: #1e293b; border: 1px solid #334155; border-radius: 15px; padding: 20px; }
            QFrame#card QLabel { color: #f1f5f9; }
            QProgressBar { border: 2px solid #334155; border-radius: 5px; background-color: #334155; text-align: center; color: #f1f5f9; }
            QProgressBar::chunk { background-color: #60a5fa; }
            QLineEdit { background-color: #1e293b; color: #f1f5f9; border: 2px solid #334155; padding: 12px; border-radius: 8px; }
            QComboBox { background-color: #1e293b; color: #f1f5f9; border: 2px solid #334155; padding: 8px; border-radius: 8px; }
            QComboBox::drop-down { border: none; }
            QComboBox::down-arrow { width: 10px; height: 10px; }
            QComboBox QAbstractItemView { background-color: #1e293b; color: #f1f5f9; selection-background-color: #334155; }
            QListWidget { background-color: #1e293b; border: 1px solid #334155; color: #f1f5f9; padding: 10px; border-radius: 8px; }
            QListWidget::item { padding: 5px; }
            QPushButton#actionBtn { 
                background-color: #60a5fa; 
                color: #ffffff; 
                border: none; 
                border-radius: 10px; 
                padding: 6px 12px; 
                font-size: 10px; 
                font-family: 'Segoe UI'; 
                font-weight: bold; 
                min-width: 50px; 
                min-height: 20px; 
                text-align: center; 
            }
            QPushButton#actionBtn:hover { 
                background-color: #3b82f6; 
            }
            QPushButton#actionBtn:pressed { 
                background-color: #2563eb; 
            }
            QMenu { 
                background-color: #1e293b; 
                border: 1px solid #334155; 
                border-radius: 8px; 
                padding: 5px; 
            }
            QMenu::item { 
                padding: 5px 20px; 
                color: #f1f5f9; 
            }
            QMenu::item:selected { 
                background-color: #334155; 
            }
        """
        self.setStyleSheet(stylesheet)
        self.update()

    def init_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)

        header = QLabel("🏠 Dashboard Overview")
        header.setObjectName("pageHeader")
        layout.addWidget(header)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        left_section = QVBoxLayout()
        left_section.setSpacing(20)

        stats_grid = QGridLayout()
        stats_grid.setSpacing(20)
        stats_data = [
            ("Total Tasks", "0", "📊", "#3b82f6"),
            ("In Progress", "0", "⏳", "#10b981"),
            ("Completed", "0", "✅", "#6366f1"),
            ("Urgent", "0", "⚠️", "#ef4444")
        ]

        self.stat_cards = []
        for i, (title, value, icon, color) in enumerate(stats_data):
            card = QFrame()
            card.setObjectName(f"statCard_{i}")
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(10)

            icon_label = QLabel(icon)
            icon_label.setFont(QFont("Segoe UI", 24))
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            title_label = QLabel(title)
            title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
            title_label.setStyleSheet("color: #1e293b;" if not self.dark_mode else "color: #f1f5f9;")

            value_label = QLabel(value)
            value_label.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
            value_label.setStyleSheet(f"color: {color};")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            progress = QProgressBar()
            progress.setValue(0)

            card_layout.addWidget(icon_label)
            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)
            card_layout.addWidget(progress)
            stats_grid.addWidget(card, i // 2, i % 2)
            self.stat_cards.append((value_label, progress))

        left_section.addLayout(stats_grid)

        activities_frame = QFrame()
        activities_frame.setObjectName("card")
        activities_layout = QVBoxLayout(activities_frame)
        activities_layout.setSpacing(10)

        activities_header = QLabel("Recent Activities")
        activities_header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))

        self.activities_list = QListWidget()
        activities_layout.addWidget(activities_header)
        activities_layout.addWidget(self.activities_list)

        left_section.addWidget(activities_frame)
        content_layout.addLayout(left_section, 2)

        right_section = QVBoxLayout()
        right_section.setSpacing(20)

        calendar_frame = QFrame()
        calendar_frame.setObjectName("card")
        calendar_layout = QVBoxLayout(calendar_frame)
        calendar_layout.setSpacing(10)

        calendar_header = QLabel("📅 Calendar")
        calendar_header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))

        self.mini_calendar = QCalendarWidget()
        self.mini_calendar.setGridVisible(True)
        self.mini_calendar.clicked.connect(self.update_date_deadlines)

        calendar_layout.addWidget(calendar_header)
        calendar_layout.addWidget(self.mini_calendar)

        actions_frame = QFrame()
        actions_frame.setObjectName("card")
        actions_layout = QVBoxLayout(actions_frame)
        actions_layout.setSpacing(10)

        actions_header = QLabel("⚡ Quick Actions")
        actions_header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))

        quick_actions = [
            ("Add New Deadline", "➕", self.show_deadline_dialog),
            ("View All Deadlines", "📋", self.show_deadlines),
            ("Check Government Updates", "🏛️", self.check_government_updates),
            ("View Analytics", "📊", self.show_analytics)
        ]

        for text, icon, handler in quick_actions:
            btn = QPushButton(f"{icon} {text}")
            btn.setObjectName("actionBtn")
            btn.clicked.connect(handler)
            actions_layout.addWidget(btn)

        right_section.addWidget(calendar_frame)
        right_section.addWidget(actions_frame)
        content_layout.addLayout(right_section, 1)

        layout.addLayout(content_layout)
        self.content_area.addWidget(page)

    def init_deadlines_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)

        header = QLabel("📅 Deadlines")
        header.setObjectName("pageHeader")
        layout.addWidget(header)

        controls = QHBoxLayout()
        controls.setSpacing(15)

        add_btn = QPushButton("➕ Add New Deadline")
        add_btn.setObjectName("actionBtn")
        add_btn.clicked.connect(self.show_deadline_dialog)
        controls.addWidget(add_btn)

        search_box = QLineEdit()
        search_box.setPlaceholderText("🔍 Search deadlines...")
        search_box.textChanged.connect(self.filter_deadlines)
        controls.addWidget(search_box)

        refresh_btn = QPushButton("🔄 Refresh Updates")
        refresh_btn.setObjectName("actionBtn")
        refresh_btn.clicked.connect(self.refresh_government_updates)
        controls.addWidget(refresh_btn)

        layout.addLayout(controls)

        personal_frame = QFrame()
        personal_frame.setObjectName("card")
        personal_layout = QVBoxLayout(personal_frame)
        personal_layout.setSpacing(10)

        personal_label = QLabel("Personal Deadlines")
        personal_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))

        self.deadlines_table = QTableWidget()
        self.deadlines_table.setColumnCount(6)
        self.deadlines_table.setHorizontalHeaderLabels(["Title", "Description", "Due Date", "Status", "Priority", "Actions"])
        self.deadlines_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.deadlines_table.setColumnWidth(5, 200)
        for i in range(5):
            self.deadlines_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        personal_layout.addWidget(personal_label)
        personal_layout.addWidget(self.deadlines_table)
        layout.addWidget(personal_frame)

        govt_frame = QFrame()
        govt_frame.setObjectName("card")
        govt_layout = QVBoxLayout(govt_frame)
        govt_layout.setSpacing(10)

        govt_label = QLabel("Available Government Deadlines")
        govt_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        
        self.govt_last_updated_label = QLabel("Last Updated: N/A")
        self.govt_last_updated_label.setFont(QFont("Segoe UI", 12))

        self.govt_table = QTableWidget()
        self.govt_table.setColumnCount(7)
        self.govt_table.setHorizontalHeaderLabels(["Title", "Department", "Due Date", "Priority", "Description", "Subscribe", "Actions"])
        self.govt_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        govt_layout.addWidget(govt_label)
        govt_layout.addWidget(self.govt_last_updated_label)
        govt_layout.addWidget(self.govt_table)
        layout.addWidget(govt_frame)

        subscribed_frame = QFrame()
        subscribed_frame.setObjectName("card")
        subscribed_layout = QVBoxLayout(subscribed_frame)
        subscribed_layout.setSpacing(10)

        subscribed_label = QLabel("Subscribed Government Deadlines")
        subscribed_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))

        self.subscribed_table = QTableWidget()
        self.subscribed_table.setColumnCount(6)
        self.subscribed_table.setHorizontalHeaderLabels(["Title", "Department", "Due Date", "Priority", "Description", "Actions"])
        self.subscribed_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        subscribed_layout.addWidget(subscribed_label)
        subscribed_layout.addWidget(self.subscribed_table)
        layout.addWidget(subscribed_frame)

        self.content_area.addWidget(page)

    def init_calendar_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)

        header = QLabel("📆 Calendar")
        header.setObjectName("pageHeader")
        layout.addWidget(header)

        calendar_frame = QFrame()
        calendar_frame.setObjectName("card")
        calendar_layout = QVBoxLayout(calendar_frame)
        calendar_layout.setSpacing(10)

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)

        self.highlight_formats = {
            'deadline': self.create_highlight_format("#60a5fa"),
            'day1': self.create_highlight_format("#ef4444"),
            'day15': self.create_highlight_format("#f59e0b"),
            'day30': self.create_highlight_format("#10b981")
        }

        legend_layout = QHBoxLayout()
        legend_items = [
            ("Deadline", "#60a5fa"),
            ("1 Day Notice", "#ef4444"),
            ("15 Days Notice", "#f59e0b"),
            ("30 Days Notice", "#10b981")
        ]

        for text, color in legend_items:
            label = QLabel(f"⬤ {text}")
            label.setStyleSheet(f"color: {color}; font-size: 14px;")
            legend_layout.addWidget(label)

        calendar_layout.addLayout(legend_layout)
        calendar_layout.addWidget(self.calendar)

        deadlines_frame = QFrame()
        deadlines_frame.setObjectName("card")
        deadlines_layout = QVBoxLayout(deadlines_frame)
        deadlines_layout.setSpacing(10)

        deadlines_header = QLabel("Deadlines & Reminders")
        deadlines_header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))

        self.date_deadlines = QListWidget()
        deadlines_layout.addWidget(deadlines_header)
        deadlines_layout.addWidget(self.date_deadlines)

        layout.addWidget(calendar_frame)
        layout.addWidget(deadlines_frame)
        self.calendar.clicked.connect(self.update_date_deadlines)
        self.content_area.addWidget(page)
        self.update_calendar_dates()

    def init_analytics_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)

        header = QLabel("📊 Analytics")
        header.setObjectName("pageHeader")
        layout.addWidget(header)

        controls = QHBoxLayout()
        self.time_filter = QComboBox()
        self.time_filter.addItems(["All Time", "Last 30 Days", "Last 7 Days"])
        self.time_filter.currentTextChanged.connect(self.update_analytics_display)
        controls.addWidget(QLabel("Filter by:"))
        controls.addWidget(self.time_filter)
        controls.addStretch()

        refresh_btn = QPushButton("🔄 Refresh Analytics")
        refresh_btn.setObjectName("actionBtn")
        refresh_btn.clicked.connect(self.refresh_data)
        controls.addWidget(refresh_btn)
        layout.addLayout(controls)

        analytics_frame = QFrame()
        analytics_frame.setObjectName("card")
        analytics_layout = QVBoxLayout(analytics_frame)
        analytics_layout.setSpacing(20)

        analytics_header = QLabel("Deadline Insights")
        analytics_header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        analytics_layout.addWidget(analytics_header)

        self.analytics_grid = QGridLayout()
        self.analytics_grid.setSpacing(20)

        # Completion Rate
        self.completion_card = QFrame()
        self.completion_card.setObjectName("card")
        completion_layout = QVBoxLayout(self.completion_card)
        self.completion_label = QLabel("Completion Rate: 0%")
        self.completion_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.completion_bar = QProgressBar()
        completion_layout.addWidget(self.completion_label)
        completion_layout.addWidget(self.completion_bar)
        self.analytics_grid.addWidget(self.completion_card, 0, 0)

        # Overdue Tasks
        self.overdue_card = QFrame()
        self.overdue_card.setObjectName("card")
        overdue_layout = QVBoxLayout(self.overdue_card)
        self.overdue_label = QLabel("Overdue Tasks: 0")
        self.overdue_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.overdue_bar = QProgressBar()
        overdue_layout.addWidget(self.overdue_label)
        overdue_layout.addWidget(self.overdue_bar)
        self.analytics_grid.addWidget(self.overdue_card, 0, 1)

        # Priority Distribution
        self.priority_card = QFrame()
        self.priority_card.setObjectName("card")
        priority_layout = QVBoxLayout(self.priority_card)
        self.priority_label = QLabel("Priority Distribution")
        self.priority_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.priority_pie = PieChartWidget()
        priority_layout.addWidget(self.priority_label)
        priority_layout.addWidget(self.priority_pie)
        self.analytics_grid.addWidget(self.priority_card, 1, 0)

        # Average Completion Time
        self.avg_time_card = QFrame()
        self.avg_time_card.setObjectName("card")
        avg_time_layout = QVBoxLayout(self.avg_time_card)
        self.avg_time_label = QLabel("Avg. Completion Time: N/A")
        self.avg_time_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        avg_time_layout.addWidget(self.avg_time_label)
        self.analytics_grid.addWidget(self.avg_time_card, 1, 1)

        analytics_layout.addLayout(self.analytics_grid)
        layout.addWidget(analytics_frame)
        layout.addStretch()
        self.content_area.addWidget(page)
        self.update_analytics_display()

    def init_chatbot_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)

        header = QLabel("🤖 Chatbot")
        header.setObjectName("pageHeader")
        layout.addWidget(header)

        chat_frame = QFrame()
        chat_frame.setObjectName("card")
        chat_layout = QVBoxLayout(chat_frame)
        chat_layout.setSpacing(10)

        chat_header = QLabel("Ask me anything!")
        chat_header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        chat_layout.addWidget(chat_header)

        self.chat_history = QListWidget()
        self.chat_history.setWordWrap(True)
        self.chat_history.setSpacing(5)
        chat_layout.addWidget(self.chat_history)

        welcome_item = QListWidgetItem("🤖 Hello! I'm here to help. Click the menu above to select a question or type your own below.")
        welcome_item.setFont(QFont("Segoe UI", 12))
        self.chat_history.addItem(welcome_item)

        input_frame = QFrame()
        input_layout = QVBoxLayout(input_frame)
        input_layout.setSpacing(10)

        # Replace QComboBox with QMenu sliding above input
        self.question_menu_button = QPushButton("📝 Questions")
        self.question_menu_button.setObjectName("actionBtn")
        self.question_menu = QMenu(self)
        for question in self.predefined_questions:
            action = QAction(question, self)
            action.triggered.connect(lambda checked, q=question: self.handle_predefined_question(q))
            self.question_menu.addAction(action)
        self.question_menu_button.setMenu(self.question_menu)
        input_layout.addWidget(self.question_menu_button, alignment=Qt.AlignmentFlag.AlignTop)

        input_widget = QWidget()
        input_h_layout = QHBoxLayout(input_widget)
        input_h_layout.setContentsMargins(0, 0, 0, 0)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type your question here...")
        self.chat_input.returnPressed.connect(self.handle_custom_question)
        input_h_layout.addWidget(self.chat_input)

        send_btn = QPushButton("Send")
        send_btn.setObjectName("actionBtn")
        send_btn.clicked.connect(self.handle_custom_question)
        input_h_layout.addWidget(send_btn)

        input_layout.addWidget(input_widget)

        layout.addWidget(chat_frame)
        layout.addWidget(input_frame)
        self.content_area.addWidget(page)

    def init_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)

        header = QLabel("⚙️ Settings")
        header.setObjectName("pageHeader")
        layout.addWidget(header)

        user_frame = QFrame()
        user_frame.setObjectName("card")
        user_layout = QVBoxLayout(user_frame)
        user_layout.setSpacing(10)

        user_header = QLabel("👤 User Information")
        user_header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))

        self.user_info_table = QTableWidget()
        self.user_info_table.setColumnCount(2)
        self.user_info_table.setRowCount(4)
        self.user_info_table.setHorizontalHeaderLabels(["Field", "Value"])
        self.user_info_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.user_info_table.verticalHeader().setVisible(False)

        self.update_user_info_table()

        user_layout.addWidget(user_header)
        user_layout.addWidget(self.user_info_table)

        self.theme_btn = QPushButton("🌙 Toggle Dark Mode" if not self.dark_mode else "☀️ Toggle Light Mode")
        self.theme_btn.setObjectName("actionBtn")
        self.theme_btn.clicked.connect(self.toggle_theme)
        user_layout.addWidget(self.theme_btn)

        layout.addWidget(user_frame)
        layout.addStretch()
        self.content_area.addWidget(page)

    def update_user_info_table(self):
        info_fields = [
            ("Name", self.user_data.get('name', 'N/A')),
            ("Email", self.user_data.get('email', 'N/A')),
            ("Phone", self.user_data.get('phone', 'N/A')),
            ("Account Type", "Regular User")
        ]
        for row, (field, value) in enumerate(info_fields):
            self.user_info_table.setItem(row, 0, QTableWidgetItem(field))
            self.user_info_table.setItem(row, 1, QTableWidgetItem(str(value)))

    def update_analytics_display(self):
        try:
            personal_deadlines = self.data_cache['personal_deadlines']
            govt_deadlines = self.data_cache['govt_deadlines']
            user_email = self.user_data.get('email', '')
            subscribed_deadlines = [d for d in govt_deadlines if user_email in d.get('subscribers', [])]
            all_deadlines = personal_deadlines + subscribed_deadlines

            filter_period = self.time_filter.currentText()
            current_date = QDate.currentDate()
            if filter_period == "Last 30 Days":
                cutoff_date = current_date.addDays(-30)
                all_deadlines = [d for d in all_deadlines if QDate.fromString(d.get('due_date', ''), "yyyy-MM-dd").isValid() and
                                 QDate.fromString(d.get('due_date', ''), "yyyy-MM-dd") >= cutoff_date]
            elif filter_period == "Last 7 Days":
                cutoff_date = current_date.addDays(-7)
                all_deadlines = [d for d in all_deadlines if QDate.fromString(d.get('due_date', ''), "yyyy-MM-dd").isValid() and
                                 QDate.fromString(d.get('due_date', ''), "yyyy-MM-dd") >= cutoff_date]

            total = len(all_deadlines)
            completed = len([d for d in personal_deadlines if d.get('status', '').lower() == 'completed'])
            overdue = sum(1 for d in all_deadlines if QDate.fromString(d.get('due_date', ''), "yyyy-MM-dd").isValid() and
                          current_date > QDate.fromString(d.get('due_date', ''), "yyyy-MM-dd"))
            high_priority = len([d for d in all_deadlines if d.get('priority', '').lower() == 'high'])
            medium_priority = len([d for d in all_deadlines if d.get('priority', '').lower() == 'medium'])
            low_priority = len([d for d in all_deadlines if d.get('priority', '').lower() == 'low'])

            # Completion Rate
            completion_rate = (completed / max(total, 1)) * 100
            self.completion_label.setText(f"Completion Rate: {completion_rate:.1f}%")
            self.completion_bar.setValue(int(completion_rate))

            # Overdue Tasks
            overdue_percentage = (overdue / max(total, 1)) * 100
            self.overdue_label.setText(f"Overdue Tasks: {overdue}")
            self.overdue_bar.setValue(int(overdue_percentage))

            # Priority Distribution
            self.priority_pie.set_data(high_priority, medium_priority, low_priority)

            # Average Completion Time (assuming deadlines have a 'created_at' field)
            completed_deadlines = [d for d in personal_deadlines if d.get('status', '').lower() == 'completed']
            if completed_deadlines and all('created_at' in d for d in completed_deadlines):
                total_days = 0
                for d in completed_deadlines:
                    created = QDate.fromString(d['created_at'], "yyyy-MM-dd")
                    due = QDate.fromString(d['due_date'], "yyyy-MM-dd")
                    if created.isValid() and due.isValid():
                        total_days += created.daysTo(due)
                avg_days = total_days / len(completed_deadlines)
                self.avg_time_label.setText(f"Avg. Completion Time: {avg_days:.1f} days")
            else:
                self.avg_time_label.setText("Avg. Completion Time: N/A")
        except Exception as e:
            print(f"Error updating analytics display: {str(e)}")

    @lru_cache(maxsize=1)
    def fetch_api_data(self, endpoint, params=None):
        try:
            response = self.session.get(
                f'http://localhost:5000/api/{endpoint}',
                params=params,
                timeout=self.request_timeout
            )
            return response.json() if response.status_code == 200 else []
        except requests.RequestException as e:
            print(f"API fetch error for {endpoint}: {str(e)}")
            return []

    def load_dashboard_data_async(self):
        if self.is_loading:
            return
        self.is_loading = True
        self.loading_label.setGeometry(self.centralWidget().rect())
        self.loading_label.setVisible(True)

        def fetch_data():
            current_time = time.time()
            if current_time - self.data_cache['last_updated'] > self.cache_timeout:
                personal_deadlines = self.fetch_api_data('personal-deadlines')
                govt_deadlines = self.fetch_api_data('government-deadlines/public').get('deadlines', [])
                self.data_cache.update({
                    'personal_deadlines': personal_deadlines,
                    'govt_deadlines': govt_deadlines,
                    'last_updated': current_time,
                    'govt_last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            QTimer.singleShot(0, self.update_ui_with_data)

        threading.Thread(target=fetch_data, daemon=True).start()

    def update_ui_with_data(self):
        try:
            personal_deadlines = self.data_cache['personal_deadlines']
            govt_deadlines = self.data_cache['govt_deadlines']
            self.update_deadlines_display(personal_deadlines, govt_deadlines)
            self.update_profile_display()
            self.update_stats_display()
            self.update_calendar_dates()
            self.update_analytics_display()
            self.update_govt_last_updated_label()
        except Exception as e:
            print(f"Error updating UI: {str(e)}")
        finally:
            self.is_loading = False
            self.loading_label.setVisible(False)

    def update_govt_last_updated_label(self):
        timestamp = self.data_cache.get('govt_last_updated', 'N/A')
        self.govt_last_updated_label.setText(f"Last Updated: {timestamp}")

    def refresh_data(self):
        self.data_cache['last_updated'] = 0
        self.load_dashboard_data_async()

    def refresh_government_updates(self):
        self.data_cache['last_updated'] = 0
        self.load_dashboard_data_async()
        QMessageBox.information(self, "Government Updates", "Government deadlines refreshed successfully!")

    def check_government_updates(self):
        self.refresh_government_updates()
        self.show_deadlines()

    def update_profile_display(self):
        self.welcome_label.setText(f"Welcome, {self.user_data.get('name', 'User')}")
        self.email_label.setText(self.user_data.get('email', ''))

    def toggle_govt_deadline_subscription(self, deadline_id, state):
        try:
            user_email = self.user_data.get('email', '')
            if not user_email:
                QMessageBox.warning(self, "Error", "User email not found")
                return
            
            response = self.session.post(
                f'http://localhost:5000/api/government-deadlines/{deadline_id}/subscribe',
                json={'email': user_email, 'subscribed': bool(state)},
                timeout=5
            )
            
            if response.status_code == 200:
                QMessageBox.information(self, "Success", "Subscribed" if state else "Unsubscribed")
                self.refresh_data()
            else:
                error_msg = response.json().get('message', 'Failed to update subscription')
                QMessageBox.warning(self, "Error", error_msg)
                
        except requests.RequestException as e:
            QMessageBox.warning(self, "Network Error", f"Failed to connect: {str(e)}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Subscription failed: {str(e)}")

    def create_highlight_format(self, color):
        format = QTextCharFormat()
        format.setBackground(QColor(color))
        format.setForeground(QColor("white"))
        return format

    def add_deadline_to_govt_table(self, row, deadline):
        deadline_id = str(deadline.get('_id', deadline.get('id', '')))
        self.govt_table.setItem(row, 0, QTableWidgetItem(deadline.get('title', '')))
        self.govt_table.setItem(row, 1, QTableWidgetItem(deadline.get('department', '')))
        self.govt_table.setItem(row, 2, QTableWidgetItem(deadline.get('due_date', '')))
        self.govt_table.setItem(row, 3, QTableWidgetItem(deadline.get('priority', '')))
        self.govt_table.setItem(row, 4, QTableWidgetItem(deadline.get('description', '')))
        
        subscribe_widget = QWidget()
        subscribe_layout = QHBoxLayout(subscribe_widget)
        subscribe_layout.setContentsMargins(5, 0, 5, 0)
        subscribe_layout.setSpacing(8)
        
        subscribe_cb = QCheckBox("Subscribe")
        user_email = self.user_data.get('email', '')
        subscribers = deadline.get('subscribers', [])
        subscribe_cb.setChecked(user_email in subscribers)
        subscribe_cb.stateChanged.connect(lambda state: self.toggle_govt_deadline_subscription(deadline_id, state))
        subscribe_layout.addWidget(subscribe_cb)
        subscribe_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.govt_table.setCellWidget(row, 5, subscribe_widget)
        
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(5, 0, 5, 0)
        actions_layout.setSpacing(8)
        
        view_btn = QPushButton("View")
        view_btn.setObjectName("actionBtn")
        view_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        view_btn.clicked.connect(lambda: self.view_govt_deadline_details(deadline))
        actions_layout.addWidget(view_btn)
        actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.govt_table.setCellWidget(row, 6, actions_widget)

    def view_govt_deadline_details(self, deadline):
        details = (
            f"Title: {deadline.get('title', 'N/A')}\n"
            f"Department: {deadline.get('department', 'N/A')}\n"
            f"Due Date: {deadline.get('due_date', 'N/A')}\n"
            f"Priority: {deadline.get('priority', 'N/A')}\n"
            f"Description: {deadline.get('description', 'N/A')}"
        )
        QMessageBox.information(self, "Government Deadline Details", details)

    def filter_deadlines(self, text):
        for row in range(self.deadlines_table.rowCount()):
            show = False
            for col in range(self.deadlines_table.columnCount() - 1):
                item = self.deadlines_table.item(row, col)
                if item and text.lower() in item.text().lower():
                    show = True
                    break
            self.deadlines_table.setRowHidden(row, not show)

    def add_deadline_to_personal_table(self, row, deadline):
        deadline_id = str(deadline.get('_id', deadline.get('id', '')))
        self.deadlines_table.setItem(row, 0, QTableWidgetItem(deadline.get('title', '')))
        self.deadlines_table.setItem(row, 1, QTableWidgetItem(deadline.get('description', '')))
        self.deadlines_table.setItem(row, 2, QTableWidgetItem(deadline.get('due_date', '')))
        self.deadlines_table.setItem(row, 3, QTableWidgetItem(deadline.get('status', '')))
        self.deadlines_table.setItem(row, 4, QTableWidgetItem(deadline.get('priority', '')))
        
        actions_widget = QWidget()
        actions_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(5, 0, 5, 0)
        actions_layout.setSpacing(8)
        
        edit_btn = QPushButton("✏️ Edit")
        edit_btn.setObjectName("actionBtn")
        edit_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        edit_btn.clicked.connect(lambda: self.show_deadline_dialog(deadline))
        
        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.setObjectName("actionBtn")
        delete_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        delete_btn.clicked.connect(lambda: self.delete_deadline(deadline_id))
        
        actions_layout.addWidget(edit_btn)
        actions_layout.addWidget(delete_btn)
        actions_layout.addStretch()
        actions_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.deadlines_table.setCellWidget(row, 5, actions_widget)

    def update_calendar_dates(self):
        self.calendar.setDateTextFormat(QDate(), QTextCharFormat())
        try:
            personal_deadlines = self.data_cache['personal_deadlines']
            for deadline in personal_deadlines:
                due_date_str = deadline.get('due_date', '')
                if due_date_str:
                    due_date = QDate.fromString(due_date_str, "yyyy-MM-dd")
                    if due_date.isValid():
                        self.calendar.setDateTextFormat(due_date, self.highlight_formats['deadline'])
                        reminder_dates = [
                            (due_date.addDays(-30), 'day30'),
                            (due_date.addDays(-15), 'day15'),
                            (due_date.addDays(-1), 'day1')
                        ]
                        for reminder_date, format_key in reminder_dates:
                            if reminder_date.isValid():
                                self.calendar.setDateTextFormat(reminder_date, self.highlight_formats[format_key])
        except Exception as e:
            print(f"Error updating calendar dates: {str(e)}")

    def show_dashboard(self):
        self.content_area.setCurrentIndex(0)
        for btn in self.nav_buttons:
            btn.setChecked(btn.text() == "🏠 Dashboard")
        self.update_stats_display()

    def show_deadlines(self):
        self.content_area.setCurrentIndex(1)
        for btn in self.nav_buttons:
            btn.setChecked(btn.text() == "📅 Deadlines")
        self.load_dashboard_data_async()

    def show_calendar(self):
        self.content_area.setCurrentIndex(2)
        for btn in self.nav_buttons:
            btn.setChecked(btn.text() == "📆 Calendar")
        self.update_calendar_dates()

    def show_analytics(self):
        self.content_area.setCurrentIndex(3)
        for btn in self.nav_buttons:
            btn.setChecked(btn.text() == "📊 Analytics")
        self.update_analytics_display()

    def show_chatbot(self):
        self.content_area.setCurrentIndex(4)
        for btn in self.nav_buttons:
            btn.setChecked(btn.text() == "🤖 Chatbot")

    def show_settings(self):
        self.content_area.setCurrentIndex(5)
        for btn in self.nav_buttons:
            btn.setChecked(btn.text() == "⚙️ Settings")
        self.update_user_info_table()

    def handle_logout(self):
        reply = QMessageBox.question(
            self, "Confirm Logout",
            "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.user_data = {}
            self.close()

    def update_stats_display(self):
        try:
            personal_deadlines = self.data_cache['personal_deadlines']
            govt_deadlines = self.data_cache['govt_deadlines']
            user_email = self.user_data.get('email', '')
            subscribed_deadlines = [d for d in govt_deadlines if user_email in d.get('subscribers', [])]

            total_tasks = len(personal_deadlines) + len(subscribed_deadlines)
            in_progress = len([d for d in personal_deadlines if d.get('status', '').lower() == 'in_progress'])
            completed = len([d for d in personal_deadlines if d.get('status', '').lower() == 'completed'])
            urgent = sum(1 for d in personal_deadlines + subscribed_deadlines
                        if QDate.fromString(d.get('due_date', ''), "yyyy-MM-dd").isValid() 
                        and 0 <= QDate.currentDate().daysTo(QDate.fromString(d.get('due_date', ''), "yyyy-MM-dd")) <= 1)

            stats_data = [
                (total_tasks, 100),
                (in_progress, (in_progress / max(total_tasks, 1)) * 100),
                (completed, (completed / max(total_tasks, 1)) * 100),
                (urgent, (urgent / max(total_tasks, 1)) * 100)
            ]

            for i, (value, percentage) in enumerate(stats_data):
                if i < len(self.stat_cards):
                    value_label, progress = self.stat_cards[i]
                    value_label.setText(str(value))
                    progress.setValue(int(percentage))

        except Exception as e:
            print(f"Error updating stats: {str(e)}")

    def update_deadlines_display(self, personal_deadlines, govt_deadlines):
        try:
            self.deadlines_table.setUpdatesEnabled(False)
            self.govt_table.setUpdatesEnabled(False)
            self.subscribed_table.setUpdatesEnabled(False)
            
            self.deadlines_table.setRowCount(len(personal_deadlines))
            self.govt_table.setRowCount(len(govt_deadlines))
            
            for row, deadline in enumerate(personal_deadlines):
                self.add_deadline_to_personal_table(row, deadline)
            
            for row, deadline in enumerate(govt_deadlines):
                self.add_deadline_to_govt_table(row, deadline)
            
            user_email = self.user_data.get('email', '')
            subscribed_deadlines = [d for d in govt_deadlines if user_email in d.get('subscribers', [])]
            self.subscribed_table.setRowCount(len(subscribed_deadlines))
            for row, deadline in enumerate(subscribed_deadlines):
                self.add_deadline_to_subscribed_table(row, deadline)
            
        except Exception as e:
            print(f"Error updating deadlines: {str(e)}")
        finally:
            self.deadlines_table.setUpdatesEnabled(True)
            self.govt_table.setUpdatesEnabled(True)
            self.subscribed_table.setUpdatesEnabled(True)

    def show_deadline_dialog(self, deadline=None):
        try:
            dialog = DeadlineDialog(self, deadline_data=deadline, token=self.user_data.get('token'))
            if dialog.exec():
                deadline_data = dialog.get_data()
                if not all([deadline_data['title'], deadline_data['due_date']]):
                    QMessageBox.warning(self, "Error", "Title and Due Date are required!")
                    return
                
                if deadline:
                    deadline_id = str(deadline.get('_id', deadline.get('id', '')))
                    response = self.session.put(
                        f'http://localhost:5000/api/personal-deadlines/{deadline_id}',
                        json=deadline_data,
                        headers={'Authorization': f'Bearer {self.user_data.get("token", "")}'},
                        timeout=self.request_timeout
                    )
                else:
                    response = self.session.post(
                        'http://localhost:5000/api/personal-deadlines',
                        json=deadline_data,
                        headers={'Authorization': f'Bearer {self.user_data.get("token", "")}'},
                        timeout=self.request_timeout
                    )
                
                if response.status_code in (200, 201):
                    QMessageBox.information(self, "Success", "Deadline saved successfully!")
                    self.refresh_data()
                else:
                    error_msg = response.json().get('message', 'Failed to save deadline')
                    QMessageBox.warning(self, "Error", error_msg)
        except requests.RequestException as e:
            QMessageBox.warning(self, "Network Error", f"Failed to connect: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save deadline: {str(e)}")

    def delete_deadline(self, deadline_id):
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this deadline?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                response = self.session.delete(
                    f'http://localhost:5000/api/personal-deadlines/{deadline_id}',
                    headers={'Authorization': f'Bearer {self.user_data.get("token", "")}'}
                )
                if response.status_code == 200:
                    QMessageBox.information(self, "Success", "Deadline deleted successfully")
                    self.refresh_data()
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete deadline")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to delete deadline: {str(e)}")

    def add_deadline_to_subscribed_table(self, row, deadline):
        deadline_id = str(deadline.get('_id', deadline.get('id', '')))
        self.subscribed_table.setItem(row, 0, QTableWidgetItem(deadline.get('title', '')))
        self.subscribed_table.setItem(row, 1, QTableWidgetItem(deadline.get('department', '')))
        self.subscribed_table.setItem(row, 2, QTableWidgetItem(deadline.get('due_date', '')))
        self.subscribed_table.setItem(row, 3, QTableWidgetItem(deadline.get('priority', '')))
        self.subscribed_table.setItem(row, 4, QTableWidgetItem(deadline.get('description', '')))
        
        actions_widget = QWidget()
        actions_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(5, 0, 5, 0)
        actions_layout.setSpacing(8)
        
        unsubscribe_btn = QPushButton("Unsubscribe")
        unsubscribe_btn.setObjectName("actionBtn")
        unsubscribe_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        unsubscribe_btn.clicked.connect(lambda: self.toggle_govt_deadline_subscription(deadline_id, False))
        
        actions_layout.addWidget(unsubscribe_btn)
        actions_layout.addStretch()
        actions_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.subscribed_table.setCellWidget(row, 5, actions_widget)

    def update_date_deadlines(self, selected_date):
        try:
            self.date_deadlines.clear()
            personal_deadlines = self.data_cache['personal_deadlines']
            govt_deadlines = self.data_cache['govt_deadlines']
            user_email = self.user_data.get('email', '')
            subscribed_deadlines = [d for d in govt_deadlines if user_email in d.get('subscribers', [])]
            all_deadlines = personal_deadlines + subscribed_deadlines
            
            selected_date_str = selected_date.toString("yyyy-MM-dd")
            for deadline in all_deadlines:
                due_date = deadline.get('due_date', '')
                if due_date == selected_date_str:
                    item = QListWidgetItem(f"📅 {deadline.get('title', 'N/A')} - Due Today!")
                    item.setForeground(QColor("#ef4444"))
                    self.date_deadlines.addItem(item)
                else:
                    due_date_q = QDate.fromString(due_date, "yyyy-MM-dd")
                    if due_date_q.isValid():
                        days_until = selected_date.daysTo(due_date_q)
                        if days_until == 30:
                            item = QListWidgetItem(f"📆 {deadline.get('title', 'N/A')} - Due in 30 days")
                            item.setForeground(QColor("#10b981"))
                            self.date_deadlines.addItem(item)
                        elif days_until == 15:
                            item = QListWidgetItem(f"⚠️ {deadline.get('title', 'N/A')} - Due in 15 days")
                            item.setForeground(QColor("#f59e0b"))
                            self.date_deadlines.addItem(item)
                        elif days_until == 1:
                            item = QListWidgetItem(f"🚨 {deadline.get('title', 'N/A')} - Due tomorrow!")
                            item.setForeground(QColor("#ef4444"))
                            self.date_deadlines.addItem(item)
            
            if self.date_deadlines.count() == 0:
                self.date_deadlines.addItem("No deadlines or reminders for this date")
        except Exception as e:
            print(f"Error updating date deadlines: {str(e)}")

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        self.theme_btn.setText("☀️ Toggle Light Mode" if self.dark_mode else "🌙 Toggle Dark Mode")
        for page in range(self.content_area.count()):
            widget = self.content_area.widget(page)
            for label in widget.findChildren(QLabel):
                if label.objectName() != "pageHeader" and "color" in label.styleSheet():
                    label.setStyleSheet("color: #1e3a8a;" if not self.dark_mode else "color: #f1f5f9;")
            widget.update()
        self.centralWidget().update()

    def handle_predefined_question(self, selected_text):
        if not selected_text or selected_text.lower() not in self.chatbot_responses:
            return

        user_item = QListWidgetItem(f"👤 {selected_text}")
        user_item.setFont(QFont("Segoe UI", 12))
        user_item.setForeground(QColor("#1e40af" if not self.dark_mode else "#f1f5f9"))
        self.chat_history.addItem(user_item)

        response = ""
        if selected_text.lower() == "show my deadlines":
            personal_deadlines = self.data_cache['personal_deadlines']
            user_email = self.user_data.get('email', '')
            subscribed_deadlines = [d for d in self.data_cache['govt_deadlines'] if user_email in d.get('subscribers', [])]
            all_deadlines = personal_deadlines + subscribed_deadlines
            if all_deadlines:
                response = "🤖 Your deadlines:\n" + "\n".join([f"- {d.get('title', 'N/A')} (Due: {d.get('due_date', 'N/A')})" for d in all_deadlines])
            else:
                response = "🤖 You have no deadlines."
        elif selected_text.lower() == "subscribe to a deadline":
            govt_deadlines = self.data_cache['govt_deadlines']
            if govt_deadlines:
                response = "🤖 Available government deadlines:\n" + "\n".join([f"- {d.get('title', 'N/A')} (ID: {d.get('_id', d.get('id', ''))})" for d in govt_deadlines])
                response += "\nPlease type 'subscribe <deadline_id>' to subscribe (e.g., 'subscribe 123')."
            else:
                response = "🤖 No government deadlines available."
        elif selected_text.lower() == "unsubscribe from a deadline":
            user_email = self.user_data.get('email', '')
            subscribed_deadlines = [d for d in self.data_cache['govt_deadlines'] if user_email in d.get('subscribers', [])]
            if subscribed_deadlines:
                response = "🤖 Your subscribed deadlines:\n" + "\n".join([f"- {d.get('title', 'N/A')} (ID: {d.get('_id', d.get('id', ''))})" for d in subscribed_deadlines])
                response += "\nPlease type 'unsubscribe <deadline_id>' to unsubscribe (e.g., 'unsubscribe 123')."
            else:
                response = "🤖 You are not subscribed to any deadlines."
        else:
            response = self.chatbot_responses[selected_text.lower()]

        response_item = QListWidgetItem(f"🤖 {response}")
        response_item.setFont(QFont("Segoe UI", 12))
        response_item.setForeground(QColor("#10b981" if not self.dark_mode else "#10b981"))
        self.chat_history.addItem(response_item)
        self.chat_history.scrollToBottom()

    def handle_custom_question(self):
        query = self.chat_input.text().strip().lower()
        if not query:
            return

        user_item = QListWidgetItem(f"👤 {query}")
        user_item.setFont(QFont("Segoe UI", 12))
        user_item.setForeground(QColor("#1e40af" if not self.dark_mode else "#f1f5f9"))
        self.chat_history.addItem(user_item)

        response = self.chatbot_responses.get(query)
        if response:
            response_item = QListWidgetItem(f"🤖 {response}")
        elif query.startswith("subscribe "):
            deadline_id = query.replace("subscribe ", "").strip()
            govt_deadlines = self.data_cache['govt_deadlines']
            deadline = next((d for d in govt_deadlines if str(d.get('_id', d.get('id', ''))) == deadline_id), None)
            if deadline:
                self.toggle_govt_deadline_subscription(deadline_id, True)
                response = f"🤖 Successfully subscribed to '{deadline.get('title', 'N/A')}'."
            else:
                response = "🤖 Invalid deadline ID. Please check the ID from the 'Subscribe to a deadline' list."
        elif query.startswith("unsubscribe "):
            deadline_id = query.replace("unsubscribe ", "").strip()
            user_email = self.user_data.get('email', '')
            subscribed_deadlines = [d for d in self.data_cache['govt_deadlines'] if user_email in d.get('subscribers', [])]
            deadline = next((d for d in subscribed_deadlines if str(d.get('_id', d.get('id', ''))) == deadline_id), None)
            if deadline:
                self.toggle_govt_deadline_subscription(deadline_id, False)
                response = f"🤖 Successfully unsubscribed from '{deadline.get('title', 'N/A')}'."
            else:
                response = "🤖 Invalid deadline ID or not subscribed. Check the 'Unsubscribe from a deadline' list."
        elif query.startswith("add deadline "):
            try:
                parts = query.replace("add deadline ", "").split(",")
                if len(parts) >= 3:
                    title = parts[0].strip()
                    due_date = parts[1].strip()
                    priority = parts[2].strip().capitalize() if len(parts) > 2 else "Medium"
                    if not all([title, due_date]):
                        response = "🤖 Title and Due Date are required. Format: 'add deadline title, yyyy-mm-dd, [priority]'"
                    else:
                        deadline_data = {
                            'title': title,
                            'due_date': due_date,
                            'priority': priority,
                            'status': 'Pending',
                            'description': parts[3].strip() if len(parts) > 3 else ''
                        }
                        dialog = DeadlineDialog(self, deadline_data=deadline_data, token=self.user_data.get('token'))
                        if dialog.exec():
                            new_deadline = dialog.get_data()
                            response = self.session.post(
                                'http://localhost:5000/api/personal-deadlines',
                                json=new_deadline,
                                headers={'Authorization': f'Bearer {self.user_data.get("token", "")}'},
                                timeout=self.request_timeout
                            )
                            if response.status_code in (200, 201):
                                self.refresh_data()
                                response = f"🤖 Deadline '{new_deadline['title']}' added successfully!"
                            else:
                                response = f"🤖 Failed to add deadline: {response.json().get('message', 'Unknown error')}"
                        else:
                            response = "🤖 Deadline addition cancelled."
                else:
                    response = "🤖 Invalid format. Use: 'add deadline title, yyyy-mm-dd, [priority], [description]'"
            except Exception as e:
                response = f"🤖 Error adding deadline: {str(e)}"
        else:
            response = f"🤖 Sorry, I don’t have an answer for that yet. Try one of the predefined questions or use commands like 'subscribe <id>', 'unsubscribe <id>', or 'add deadline title, yyyy-mm-dd, [priority]'!"

        response_item = QListWidgetItem(f"🤖 {response}")
        response_item.setFont(QFont("Segoe UI", 12))
        response_item.setForeground(QColor("#10b981" if not self.dark_mode else "#10b981"))
        self.chat_history.addItem(response_item)

        self.chat_history.scrollToBottom()
        self.chat_input.clear()

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = DashboardWindow({"name": "Test User", "email": "test@example.com", "token": "dummy_token"})
    window.show()
    sys.exit(app.exec())