from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLabel, QFrame, QTableWidget,
                            QTableWidgetItem, QHeaderView, QLineEdit,
                            QComboBox, QMessageBox, QStackedWidget, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QTimer, QDateTime
from PyQt6.QtGui import QFont, QColor
import requests
from ..components.government_deadline_dialog import GovernmentDeadlineDialog  # Fixed import path

class FancyButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(40)

class FancyFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("fancyFrame")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)

class AdminPanel(QMainWindow):
    def __init__(self, admin_token):
        super().__init__()
        self.admin_token = admin_token
        self.setWindowTitle("AlertMe Admin Panel")
        self.setMinimumSize(1400, 800)
        
        # Apply modern styling with dark mode support
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #1a237e, stop:1 #0d47a1);
            }
            #fancyFrame {
                background-color: rgba(255, 255, 255, 0.95);
                color: #1a237e;
                border-radius: 15px;
                margin: 10px;
                padding: 15px;
            }
            QLabel {
                color: #1a237e;
                font-family: 'Segoe UI', Arial;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #3949ab, stop:1 #1e88e5);
                color: white;
                border: none;
                padding: 8px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #5c6bc0, stop:1 #42a5f5);
            }
            QTableWidget {
                background-color: rgba(255, 255, 255, 0.95);
                color: #1a237e;
                border-radius: 10px;
                padding: 10px;
                font-size: 14px;
                gridline-color: #bbdefb;
            }
            QTableWidget::item {
                padding: 8px;
                margin: 2px;
                border-radius: 5px;
                color: #1a237e;
            }
            QTableWidget::item:hover {
                background-color: #e3f2fd;
            }
            QTableWidget::item:selected {
                background-color: #bbdefb;
                color: #1a237e;
            }
            QLineEdit, QComboBox {
                padding: 8px;
                border: 2px solid #bbdefb;
                border-radius: 8px;
                background-color: white;
                color: #1a237e;
                font-size: 14px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #2196f3;
            }
            QComboBox::drop-down {
                border: none;
                border-radius: 4px;
                background: #2196f3;
                width: 24px;
            }
            QComboBox::down-arrow {
                image: none;
                border-width: 6px;
                border-top-width: 0;
                border-style: solid;
                border-color: white transparent;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: #1a237e;
                selection-background-color: #bbdefb;
                selection-color: #1a237e;
            }
            QHeaderView::section {
                background-color: #1976d2;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #2196f3;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QMessageBox {
                background-color: white;
                color: #1a237e;
            }
            QMessageBox QPushButton {
                min-width: 80px;
            }
        """)
        
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left Panel
        left_frame = FancyFrame()
        left_layout = QVBoxLayout(left_frame)
        
        # Admin Info
        admin_info = QLabel("<h2>Admin Panel</h2>")
        admin_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label = QLabel()
        self.time_label.setFont(QFont('Segoe UI', 16, QFont.Weight.Bold))
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_time()
        
        timer = QTimer(self)
        timer.timeout.connect(self.update_time)
        timer.start(1000)
        
        # Navigation Buttons
        nav_buttons = [
            ("👥 Users", lambda: self.show_tab("users")),
            ("📅 Government Deadlines", lambda: self.show_tab("deadlines")),
            ("📊 Analytics", lambda: self.show_tab("analytics")),
            ("⚙️ Settings", lambda: self.show_tab("settings"))
        ]
        
        for text, action in nav_buttons:
            btn = FancyButton(text)
            btn.clicked.connect(action)
            left_layout.addWidget(btn)
        
        left_layout.addStretch()
        
        # Add Logout Button
        logout_btn = FancyButton("🚪 Logout")
        logout_btn.clicked.connect(self.logout)
        logout_btn.setStyleSheet("""
            QPushButton {
                background: #dc3545;
                color: white;
            }
            QPushButton:hover {
                background: #c82333;
            }
        """)
        left_layout.addWidget(logout_btn)
        
        # System Status
        status_frame = FancyFrame()
        status_layout = QVBoxLayout(status_frame)
        status_layout.addWidget(QLabel("<h3>System Status</h3>"))
        
        stats = [
            ("Active Users", "0", "👥"),
            ("Pending Tasks", "0", "⏱️"),
            ("Total Deadlines", "0", "📅")
        ]
        
        for label, value, icon in stats:
            stat_label = QLabel(f"{icon} {label}: {value}")
            status_layout.addWidget(stat_label)
        
        left_layout.addWidget(admin_info)
        left_layout.addWidget(self.time_label)
        left_layout.addWidget(status_frame)
        
        # Right Content Area
        right_frame = FancyFrame()
        right_layout = QVBoxLayout(right_frame)
        
        # Stack for different views
        self.stack = QStackedWidget()
        self.stack.addWidget(self.create_users_view())          # index 0
        self.stack.addWidget(self.create_deadlines_view())      # index 1
        self.stack.addWidget(self.create_analytics_view())      # index 2
        self.stack.addWidget(self.create_settings_view())       # index 3
        right_layout.addWidget(self.stack)
        
        # Add panels to main layout
        main_layout.addWidget(left_frame, 1)
        main_layout.addWidget(right_frame, 4)

    def update_time(self):
        current_time = QDateTime.currentDateTime()
        self.time_label.setText(current_time.toString('yyyy-MM-dd\nhh:mm:ss'))

    def create_users_view(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # Controls
        controls = QHBoxLayout()
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search users...")
        self.search_box.textChanged.connect(self.filter_users)
        controls.addWidget(self.search_box)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Active", "Inactive"])
        self.status_filter.currentTextChanged.connect(self.filter_users)
        controls.addWidget(self.status_filter)
        
        layout.addLayout(controls)
        
        # Users table
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(6)  # Added one column for delete action
        self.users_table.setHorizontalHeaderLabels([
            "ID", "Name", "Email", "Status", "Actions", "Delete"
        ])
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.users_table)
        
        # Load users initially
        self.load_users()
        
        return page

    # Add these new methods
    def load_users(self):
        try:
            response = requests.get(
                'http://localhost:5000/auth/api/admin/users',
                headers={'Authorization': f'Bearer {self.admin_token}'}
            )
            
            if response.status_code == 200:
                users = response.json()
                self.users_table.setRowCount(len(users))
                
                for row, user in enumerate(users):
                    # Add user details
                    self.users_table.setItem(row, 0, QTableWidgetItem(str(user.get('id', ''))))
                    self.users_table.setItem(row, 1, QTableWidgetItem(user.get('name', '')))
                    self.users_table.setItem(row, 2, QTableWidgetItem(user.get('email', '')))
                    self.users_table.setItem(row, 3, QTableWidgetItem(user.get('status', '')))
                    
                    # Add action buttons
                    actions_widget = QWidget()
                    actions_layout = QHBoxLayout(actions_widget)
                    actions_layout.setContentsMargins(5, 0, 5, 0)
                    
                    view_btn = QPushButton("View")
                    view_btn.clicked.connect(lambda checked, u=user: self.view_user_details(u))
                    actions_layout.addWidget(view_btn)
                    
                    self.users_table.setCellWidget(row, 4, actions_widget)
                    
                    # Add delete button
                    delete_widget = QWidget()
                    delete_layout = QHBoxLayout(delete_widget)
                    delete_layout.setContentsMargins(5, 0, 5, 0)
                    
                    delete_btn = QPushButton("Delete")
                    delete_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #dc3545;
                            color: white;
                            border: none;
                            padding: 5px 10px;
                            border-radius: 3px;
                        }
                        QPushButton:hover {
                            background-color: #c82333;
                        }
                    """)
                    delete_btn.clicked.connect(lambda checked, u=user: self.delete_user(u))
                    delete_layout.addWidget(delete_btn)
                    
                    self.users_table.setCellWidget(row, 5, delete_widget)
                    
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load users: {str(e)}")

    def delete_user(self, user):
        try:
            # Get the user ID, checking both '_id' and 'id' fields
            user_id = user.get('_id') or user.get('id')
            if not user_id:
                QMessageBox.warning(self, "Error", "Invalid user ID")
                return

            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Are you sure you want to delete user {user.get('name')}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                response = requests.delete(
                    f'http://localhost:5000/api/admin/users/{user_id}',
                    headers={'Authorization': f'Bearer {self.admin_token}'}
                )
                
                if response.status_code == 200:
                    self.load_users()
                    QMessageBox.information(self, "Success", "User deleted successfully")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to delete user: {response.text}")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def view_user_details(self, user):
        details = (
            f"User Details:\n\n"
            f"ID: {user.get('id', 'N/A')}\n"
            f"Name: {user.get('name', 'N/A')}\n"
            f"Email: {user.get('email', 'N/A')}\n"
            f"Status: {user.get('status', 'N/A')}\n"
            f"Created At: {user.get('created_at', 'N/A')}"
        )
        QMessageBox.information(self, "User Details", details)

    def create_deadlines_view(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # Controls
        controls = QHBoxLayout()
        add_btn = QPushButton("Add Government Deadline")
        add_btn.clicked.connect(self.add_govt_deadline)
        controls.addWidget(add_btn)
        
        self.deadline_search = QLineEdit()
        self.deadline_search.setPlaceholderText("Search deadlines...")
        self.deadline_search.textChanged.connect(self.filter_deadlines)
        controls.addWidget(self.deadline_search)
        
        layout.addLayout(controls)
        
        # Deadlines table
        self.deadlines_table = QTableWidget()
        self.deadlines_table.setColumnCount(7)
        self.deadlines_table.setHorizontalHeaderLabels([
            "ID", "Title", "Department", "Due Date", "Priority", "Subscribers", "Actions"
        ])
        self.deadlines_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.deadlines_table)
        
        return page

    def show_tab(self, tab_name):
        if tab_name == "users":
            self.stack.setCurrentIndex(0)
            self.load_users()
        elif tab_name == "deadlines":
            self.stack.setCurrentIndex(1)
            self.load_govt_deadlines()
        elif tab_name == "analytics":
            self.stack.setCurrentIndex(2)
            self.load_analytics()
        elif tab_name == "settings":
            self.stack.setCurrentIndex(3)
            self.load_admin_details()

    def create_analytics_view(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # Analytics Header
        header = QLabel("📊 Analytics Dashboard")
        header.setFont(QFont('Segoe UI', 20, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # Summary Cards
        summary_layout = QHBoxLayout()
        
        # Create summary cards
        self.summary_cards = {}
        for title in ["Total Users", "Active Users", "Total Deadlines"]:
            card = FancyFrame()
            card_layout = QVBoxLayout(card)
            
            title_label = QLabel(title)
            title_label.setFont(QFont('Segoe UI', 12, QFont.Weight.Bold))
            value_label = QLabel("0")
            value_label.setFont(QFont('Segoe UI', 24, QFont.Weight.Bold))
            
            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)
            
            self.summary_cards[title] = value_label
            summary_layout.addWidget(card)
        
        layout.addLayout(summary_layout)
        
        # Deadlines Statistics
        deadline_frame = FancyFrame()
        deadline_layout = QVBoxLayout(deadline_frame)
        
        deadline_header = QLabel("Deadline Statistics")
        deadline_header.setFont(QFont('Segoe UI', 14, QFont.Weight.Bold))
        deadline_layout.addWidget(deadline_header)
        
        self.deadline_stats_table = QTableWidget()
        self.deadline_stats_table.setColumnCount(4)
        self.deadline_stats_table.setHorizontalHeaderLabels([
            "Deadline Title", "Total Subscribers", "Active Users", "Completion Rate"
        ])
        self.deadline_stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        deadline_layout.addWidget(self.deadline_stats_table)
        
        layout.addWidget(deadline_frame)
        
        # User Activity Statistics
        user_frame = FancyFrame()
        user_layout = QVBoxLayout(user_frame)
        
        user_header = QLabel("User Activity")
        user_header.setFont(QFont('Segoe UI', 14, QFont.Weight.Bold))
        user_layout.addWidget(user_header)
        
        self.user_stats_table = QTableWidget()
        self.user_stats_table.setColumnCount(4)
        self.user_stats_table.setHorizontalHeaderLabels([
            "User", "Subscribed Deadlines", "Active Deadlines", "Completion Rate"
        ])
        self.user_stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        user_layout.addWidget(self.user_stats_table)
        
        layout.addWidget(user_frame)
        
        # Refresh Button
        refresh_btn = QPushButton("🔄 Refresh Analytics")
        refresh_btn.clicked.connect(self.load_analytics)
        layout.addWidget(refresh_btn)
        
        return page

    def load_analytics(self):
        try:
            response = requests.get(
                'http://localhost:5000/admin/api/analytics',
                headers={'Authorization': f'Bearer {self.admin_token}'}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.update_analytics_view(data)
            else:
                QMessageBox.warning(self, "Error", "Failed to load analytics data")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def update_analytics_view(self, data):
        # Update summary cards
        summary = data.get('summary', {})
        self.summary_cards["Total Users"].setText(str(summary.get('total_users', 0)))
        self.summary_cards["Active Users"].setText(str(summary.get('active_users', 0)))
        self.summary_cards["Total Deadlines"].setText(str(summary.get('total_deadlines', 0)))
        
        # Update deadline statistics table
        deadlines = data.get('deadlines', [])
        self.deadline_stats_table.setRowCount(len(deadlines))
        for row, deadline in enumerate(deadlines):
            self.deadline_stats_table.setItem(row, 0, QTableWidgetItem(deadline['title']))
            self.deadline_stats_table.setItem(row, 1, QTableWidgetItem(str(deadline['total_subscribers'])))
            self.deadline_stats_table.setItem(row, 2, QTableWidgetItem(str(deadline['active_users'])))
            self.deadline_stats_table.setItem(row, 3, QTableWidgetItem(f"{deadline['completion_rate']}%"))
        
        # Update user statistics table
        users = data.get('users', [])
        self.user_stats_table.setRowCount(len(users))
        for row, user in enumerate(users):
            self.user_stats_table.setItem(row, 0, QTableWidgetItem(user['name']))
            self.user_stats_table.setItem(row, 1, QTableWidgetItem(str(user['subscribed_deadlines'])))
            self.user_stats_table.setItem(row, 2, QTableWidgetItem(str(user['active_deadlines'])))
            self.user_stats_table.setItem(row, 3, QTableWidgetItem(f"{user['completion_rate']}%"))

    def create_settings_view(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # Settings Header
        header = QLabel("⚙️ Settings")
        header.setFont(QFont('Segoe UI', 20, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # Admin Details Section
        admin_frame = FancyFrame()
        admin_layout = QVBoxLayout(admin_frame)
        
        admin_header = QLabel("Admin Information")
        admin_header.setFont(QFont('Segoe UI', 14, QFont.Weight.Bold))
        admin_layout.addWidget(admin_header)
        
        self.admin_info_table = QTableWidget()
        self.admin_info_table.setColumnCount(2)
        self.admin_info_table.setRowCount(4)
        self.admin_info_table.setHorizontalHeaderLabels(["Field", "Value"])
        self.admin_info_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.admin_info_table.verticalHeader().setVisible(False)
        admin_layout.addWidget(self.admin_info_table)
        
        layout.addWidget(admin_frame)
        
        # Theme Settings Section
        theme_frame = FancyFrame()
        theme_layout = QVBoxLayout(theme_frame)
        
        theme_header = QLabel("Theme Settings")
        theme_header.setFont(QFont('Segoe UI', 14, QFont.Weight.Bold))
        theme_layout.addWidget(theme_header)
        
        # Dark Mode Toggle
        dark_mode_widget = QWidget()
        dark_mode_layout = QHBoxLayout(dark_mode_widget)
        dark_mode_label = QLabel("Dark Mode")
        dark_mode_label.setFont(QFont('Segoe UI', 12))
        
        self.dark_mode_toggle = QPushButton()
        self.dark_mode_toggle.setCheckable(True)
        self.dark_mode_toggle.setFixedSize(60, 30)
        self.dark_mode_toggle.clicked.connect(self.toggle_dark_mode)
        self.dark_mode_toggle.setStyleSheet("""
            QPushButton {
                border: 2px solid #bbdefb;
                border-radius: 15px;
                background: #f8f9fa;
            }
            QPushButton:checked {
                background: #2196f3;
            }
        """)
        
        dark_mode_layout.addWidget(dark_mode_label)
        dark_mode_layout.addWidget(self.dark_mode_toggle)
        dark_mode_layout.addStretch()
        theme_layout.addWidget(dark_mode_widget)
        
        layout.addWidget(theme_frame)
        layout.addStretch()
        
        return page

    def load_admin_details(self):
        try:
            response = requests.get(
                'http://localhost:5000/admin/api/profile',
                headers={'Authorization': f'Bearer {self.admin_token}'}
            )
            
            if response.status_code == 200:
                admin_data = response.json()
                self.update_admin_info(admin_data)
            else:
                QMessageBox.warning(self, "Error", "Failed to load admin details")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def update_admin_info(self, admin_data):
        info_fields = [
            ("Name", admin_data.get('name', 'N/A')),
            ("Email", admin_data.get('email', 'N/A')),
            ("Role", "Administrator"),
            ("Last Login", admin_data.get('last_login', 'N/A'))
        ]
        
        for row, (field, value) in enumerate(info_fields):
            self.admin_info_table.setItem(row, 0, QTableWidgetItem(field))
            self.admin_info_table.setItem(row, 1, QTableWidgetItem(str(value)))

    def toggle_dark_mode(self, checked):
        if checked:
            self.apply_dark_theme()
        else:
            self.apply_light_theme()

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background: #1a1a1a;
            }
            #fancyFrame {
                background-color: #2d2d2d;
                color: #ffffff;
                border-radius: 15px;
                margin: 10px;
                padding: 15px;
            }
            QLabel {
                color: #ffffff;
            }
            QTableWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                gridline-color: #3d3d3d;
            }
            QTableWidget::item {
                color: #ffffff;
            }
            QTableWidget::item:hover {
                background-color: #3d3d3d;
            }
            QHeaderView::section {
                background-color: #1e88e5;
                color: white;
            }
            QLineEdit, QComboBox {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 2px solid #1e88e5;
            }
        """)

    def apply_light_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #1a237e, stop:1 #0d47a1);
            }
            #fancyFrame {
                background-color: rgba(255, 255, 255, 0.95);
                color: #1a237e;
                border-radius: 15px;
                margin: 10px;
                padding: 15px;
            }
            QLabel {
                color: #1a237e;
            }
            QTableWidget {
                background-color: rgba(255, 255, 255, 0.95);
                color: #1a237e;
                gridline-color: #bbdefb;
            }
            QTableWidget::item {
                color: #1a237e;
            }
            QTableWidget::item:hover {
                background-color: #e3f2fd;
            }
            QHeaderView::section {
                background-color: #1976d2;
                color: white;
            }
            QLineEdit, QComboBox {
                background-color: white;
                color: #1a237e;
                border: 2px solid #1e88e5;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #3949ab, stop:1 #1e88e5);
                color: white;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #5c6bc0, stop:1 #42a5f5);
            }
        """)

    def load_users(self):
        try:
            response = requests.get(
                'http://localhost:5000/admin/api/users',
                headers={'Authorization': f'Bearer {self.admin_token}'}
            )
            
            if response.status_code == 200:
                users = response.json()['users']
                self.populate_users_table(users)
            else:
                QMessageBox.warning(self, "Error", "Failed to load users")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def populate_users_table(self, users):
        self.users_table.setRowCount(len(users))
        
        for row, user in enumerate(users):
            self.users_table.setItem(row, 0, QTableWidgetItem(str(user['_id'])))
            self.users_table.setItem(row, 1, QTableWidgetItem(user['name']))
            self.users_table.setItem(row, 2, QTableWidgetItem(user['email']))
            self.users_table.setItem(row, 3, QTableWidgetItem("Active"))  # Default status
            
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda _, u=user: self.edit_user(u))
            
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda _, u=user: self.delete_user(u))
            
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            
            self.users_table.setCellWidget(row, 4, actions_widget)

    def load_govt_deadlines(self):
        try:
            print("Fetching government deadlines...")  # Debug print
            response = requests.get(
                'http://localhost:5000/admin/api/government-deadlines',
                headers={'Authorization': f'Bearer {self.admin_token}'}
            )
            
            print(f"Response status: {response.status_code}")  # Debug print
            print(f"Response content: {response.text}")  # Debug print
            
            if response.status_code == 200:
                data = response.json()
                deadlines = data.get('deadlines', [])
                print(f"Received {len(deadlines)} deadlines")  # Debug print
                if not deadlines:
                    print("No deadlines found in response")  # Debug print
                self.populate_deadlines_table(deadlines)
            else:
                error_msg = f"Failed to load government deadlines: {response.text}"
                print(error_msg)  # Debug print
                QMessageBox.warning(self, "Error", error_msg)
        except Exception as e:
            error_msg = f"An error occurred: {str(e)}"
            print(error_msg)  # Debug print
            QMessageBox.critical(self, "Error", error_msg)

    def populate_deadlines_table(self, deadlines):
        try:
            print(f"Populating table with {len(deadlines)} deadlines")  # Debug print
            self.deadlines_table.setRowCount(len(deadlines))
            
            for row, deadline in enumerate(deadlines):
                print(f"Processing deadline: {deadline}")  # Debug print
                
                # Safely get values with defaults
                deadline_id = str(deadline.get('id', ''))
                title = str(deadline.get('title', ''))
                department = str(deadline.get('department', ''))
                due_date = str(deadline.get('due_date', ''))
                priority = str(deadline.get('priority', ''))
                subscribers = str(deadline.get('subscribers', []))
                
                self.deadlines_table.setItem(row, 0, QTableWidgetItem(deadline_id))
                self.deadlines_table.setItem(row, 1, QTableWidgetItem(title))
                self.deadlines_table.setItem(row, 2, QTableWidgetItem(department))
                self.deadlines_table.setItem(row, 3, QTableWidgetItem(due_date))
                self.deadlines_table.setItem(row, 4, QTableWidgetItem(priority))
                self.deadlines_table.setItem(row, 5, QTableWidgetItem(subscribers))
                
                # Create actions buttons
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(0, 0, 0, 0)
                
                edit_btn = QPushButton("Edit")
                edit_btn.clicked.connect(lambda _, d=deadline: self.edit_govt_deadline(d))
                
                delete_btn = QPushButton("Delete")
                delete_btn.clicked.connect(lambda _, d=deadline: self.delete_govt_deadline(d))
                
                actions_layout.addWidget(edit_btn)
                actions_layout.addWidget(delete_btn)
                self.deadlines_table.setCellWidget(row, 6, actions_widget)
                
        except Exception as e:
            print(f"Error in populate_deadlines_table: {str(e)}")  # Debug print
            raise

    def add_govt_deadline(self):
        dialog = GovernmentDeadlineDialog(self)
        if dialog.exec():
            try:
                deadline_data = dialog.get_deadline_data()
                print("Sending data:", deadline_data)  # Debug print
                
                response = requests.post(
                    'http://localhost:5000/admin/api/government-deadlines',  # Updated endpoint
                    headers={
                        'Authorization': f'Bearer {self.admin_token}',
                        'Content-Type': 'application/json'
                    },
                    json=deadline_data
                )
                
                print(f"Response: {response.text}")  # Debug print
                
                if response.status_code == 201:
                    self.load_govt_deadlines()
                    QMessageBox.information(self, "Success", "Government deadline added successfully")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to add deadline: {response.text}")
            except Exception as e:
                print(f"Exception: {str(e)}")  # Debug print
                QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def edit_govt_deadline(self, deadline):
        dialog = GovernmentDeadlineDialog(self, deadline)
        if dialog.exec():
            try:
                updated_data = dialog.get_deadline_data()
                response = requests.put(
                    f'http://localhost:5000/admin/api/government-deadlines/{deadline["id"]}',
                    headers={
                        'Authorization': f'Bearer {self.admin_token}',
                        'Content-Type': 'application/json'
                    },
                    json=updated_data
                )
                
                if response.status_code == 200:
                    self.load_govt_deadlines()
                    QMessageBox.information(self, "Success", "Government deadline updated successfully")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to update deadline: {response.text}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def delete_govt_deadline(self, deadline):
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete deadline '{deadline['title']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                response = requests.delete(
                    f'http://localhost:5000/admin/api/government-deadlines/{deadline["id"]}',  # Updated endpoint
                    headers={'Authorization': f'Bearer {self.admin_token}'}
                )
                
                if response.status_code == 200:
                    self.load_govt_deadlines()
                    QMessageBox.information(self, "Success", "Deadline deleted successfully")
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete deadline")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def filter_deadlines(self):
        search_text = self.deadline_search.text().lower()
        
        for row in range(self.deadlines_table.rowCount()):
            title = self.deadlines_table.item(row, 1).text().lower()
            department = self.deadlines_table.item(row, 2).text().lower()
            
            match = search_text in title or search_text in department
            self.deadlines_table.setRowHidden(row, not match)

    def filter_users(self):
        search_text = self.search_box.text().lower()
        status_filter = self.status_filter.currentText()
        
        for row in range(self.users_table.rowCount()):
            name = self.users_table.item(row, 1).text().lower()
            email = self.users_table.item(row, 2).text().lower()
            status = self.users_table.item(row, 3).text()
            
            name_match = search_text in name or search_text in email
            status_match = status_filter == "All" or status == status_filter
            
            self.users_table.setRowHidden(row, not (name_match and status_match))

    def edit_user(self, user):
        # Implement user editing functionality
        pass

    def delete_user(self, user):
        try:
            # Get the user ID, checking both '_id' and 'id' fields
            user_id = user.get('_id') or user.get('id')
            if not user_id:
                QMessageBox.warning(self, "Error", "Invalid user ID")
                return

            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Are you sure you want to delete user {user.get('name')}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                response = requests.delete(
                    f'http://localhost:5000/api/admin/users/{user_id}',
                    headers={'Authorization': f'Bearer {self.admin_token}'}
                )
                
                if response.status_code == 200:
                    self.load_users()
                    QMessageBox.information(self, "Success", "User deleted successfully")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to delete user: {response.text}")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    # Add this method at the end of the class
    def logout(self):
        reply = QMessageBox.question(
            self, "Confirm Logout",
            "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            from .login_window import LoginWindow
            self.login_window = LoginWindow()
            self.login_window.show()
            self.close()

