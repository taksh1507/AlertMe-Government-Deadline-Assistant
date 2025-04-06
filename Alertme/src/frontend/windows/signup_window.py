from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QLineEdit, QPushButton, QLabel, QFrame, QMessageBox,
                            QStackedWidget, QCheckBox)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont
from twilio.rest import Client
import requests
import random
import os
from dotenv import load_dotenv
import re

load_dotenv()

class SignupWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AlertMe - Sign Up")
        self.showMaximized()
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #1a237e, stop:0.5 #0d47a1, stop:1 #1976d2);
            }
        """)
        self.twilio_client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )
        self.verification_code = None
        self.user_data = None
        
        self.init_ui()
        self.setup_animations()

    def setup_animations(self):
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(1000)
        self.fade_animation.setStartValue(0)
        self.fade_animation.setEndValue(1)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_animation.start()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        self.stacked_widget = QStackedWidget()
        main_layout = QHBoxLayout(central_widget)
        main_layout.addWidget(self.stacked_widget)
        
        self.create_signup_page()
        self.create_verification_page()

    def create_signup_page(self):
        signup_page = QWidget()
        signup_page.setStyleSheet("background: transparent;")
        main_layout = QHBoxLayout(signup_page)
        
        # Left Side
        left_widget = QWidget()
        left_widget.setStyleSheet("""
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        """)
        left_layout = QVBoxLayout(left_widget)
        
        logo_label = QLabel("🔔")
        logo_label.setStyleSheet("""
            font-size: 80px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 50%;
            margin: 20px;
            color: white;
        """)
        
        welcome_text = QLabel("Join AlertMe")
        welcome_text.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        welcome_text.setStyleSheet("""
            color: white;
            padding: 15px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
        """)
        
        description = QLabel("Create your account to start\nmanaging deadlines efficiently")
        description.setFont(QFont("Segoe UI", 14))
        description.setStyleSheet("""
            color: #e3f2fd;
            padding: 15px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
        """)
        
        left_layout.addStretch()
        left_layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(welcome_text, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(description, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addStretch()
        
        main_layout.addWidget(left_widget, 4)
        
        # Right Side
        signup_card = QFrame()
        signup_card.setObjectName("signupCard")
        signup_card.setStyleSheet("""
            #signupCard {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 25px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                padding: 30px;
            }
            QLineEdit {
                padding: 12px;
                border: 2px solid #bbdefb;
                border-radius: 12px;
                font-size: 14px;
                min-width: 300px;
                margin: 8px;
                background: rgba(255, 255, 255, 0.2);
                color: white;
            }
            QLineEdit:focus {
                border: 2px solid #42a5f5;
                background: rgba(255, 255, 255, 0.25);
            }
            QLineEdit::placeholder {
                color: rgba(255, 255, 255, 0.7);
                font-style: italic;
            }
            QPushButton#signupBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #2196f3, stop:1 #42a5f5);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 12px;
                font-size: 15px;
                font-weight: bold;
                min-width: 300px;
                margin: 8px;
            }
            QPushButton#signupBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #1976d2, stop:1 #2196f3);
            }
            QPushButton#backBtn {
                background: transparent;
                color: white;
                border: 2px solid #42a5f5;
                border-radius: 12px;
                padding: 12px;
                font-size: 15px;
                min-width: 300px;
                margin: 8px;
            }
            QPushButton#backBtn:hover {
                background: rgba(66, 165, 245, 0.15);
                border-color: #64b5f6;
            }
            QLabel#error {
                color: #ef5350;
                font-size: 12px;
                margin: 6px;
                background: rgba(239, 83, 80, 0.1);
                padding: 6px;
                border-radius: 6px;
            }
        """)
        signup_layout = QVBoxLayout(signup_card)
        
        title = QLabel("Create Your Account")
        title.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        title.setStyleSheet("color: white; margin-bottom: 18px;")
        
        subtitle = QLabel("Fill in your details below")
        subtitle.setFont(QFont("Segoe UI", 14))
        subtitle.setStyleSheet("color: #bbdefb; margin-bottom: 22px;")
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Full Name")
        self.name_input.textChanged.connect(self.clear_error)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")
        self.email_input.textChanged.connect(self.clear_error)
        
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Phone Number (with country code)")
        self.phone_input.textChanged.connect(self.clear_error)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.textChanged.connect(self.clear_error)
        
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("Confirm Password")
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.textChanged.connect(self.clear_error)
        
        show_password = QCheckBox("Show Password")
        show_password.setStyleSheet("""
            color: white;
            font-size: 12px;
            padding: 6px;
            spacing: 6px;
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 6px;
                border: 2px solid #bbdefb;
                background: rgba(255, 255, 255, 0.1);
            }
            QCheckBox::indicator:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #2196f3, stop:1 #42a5f5);
                border: none;
            }
            QCheckBox::indicator:hover {
                border-color: #64b5f6;
            }
        """)
        show_password.stateChanged.connect(lambda state: [
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal if state else QLineEdit.EchoMode.Password),
            self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Normal if state else QLineEdit.EchoMode.Password)
        ])
        
        self.error_label = QLabel()
        self.error_label.setObjectName("error")
        self.error_label.hide()
        
        signup_button = QPushButton("Create Account")
        signup_button.setObjectName("signupBtn")
        signup_button.clicked.connect(self.handle_signup)
        signup_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        back_button = QPushButton("Back to Login")
        back_button.setObjectName("backBtn")
        back_button.clicked.connect(self.back_to_login)
        back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        signup_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        signup_layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignCenter)
        signup_layout.addWidget(self.name_input)
        signup_layout.addWidget(self.email_input)
        signup_layout.addWidget(self.phone_input)
        signup_layout.addWidget(self.password_input)
        signup_layout.addWidget(self.confirm_password_input)
        signup_layout.addWidget(show_password, alignment=Qt.AlignmentFlag.AlignLeft)
        signup_layout.addWidget(self.error_label, alignment=Qt.AlignmentFlag.AlignCenter)
        signup_layout.addWidget(signup_button)
        signup_layout.addWidget(back_button)
        
        main_layout.addWidget(signup_card, 6)
        self.stacked_widget.addWidget(signup_page)

    def create_verification_page(self):
        verification_page = QWidget()
        verification_page.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(verification_page)
        
        title = QLabel("Verify Your Phone")
        title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        title.setStyleSheet("color: white; margin-bottom: 15px;")
        
        subtitle = QLabel("Enter the verification code sent to your phone")
        subtitle.setFont(QFont("Segoe UI", 12))
        subtitle.setStyleSheet("""
            color: #e3f2fd;
            margin-bottom: 20px;
            padding: 8px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
        """)
        
        self.otp_input = QLineEdit()
        self.otp_input.setPlaceholderText("Enter 6-digit code")
        self.otp_input.setMaxLength(6)
        self.otp_input.setStyleSheet("""
            padding: 12px;
            border: 2px solid #bbdefb;
            border-radius: 12px;
            font-size: 14px;
            min-width: 300px;
            margin: 8px;
            background: rgba(255, 255, 255, 0.2);
            color: white;
        """)
        
        verify_button = QPushButton("Verify")
        verify_button.setObjectName("signupBtn")
        verify_button.clicked.connect(self.verify_otp)
        verify_button.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                      stop:0 #2196f3, stop:1 #42a5f5);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 12px;
            font-size: 15px;
            font-weight: bold;
            min-width: 300px;
            margin: 8px;
        """)
        verify_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        resend_button = QPushButton("Resend Code")
        resend_button.setObjectName("backBtn")
        resend_button.clicked.connect(self.send_verification_code)
        resend_button.setStyleSheet("""
            background: transparent;
            color: white;
            border: 2px solid #42a5f5;
            border-radius: 12px;
            padding: 12px;
            font-size: 15px;
            min-width: 300px;
            margin: 8px;
        """)
        resend_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.verify_error_label = QLabel()
        self.verify_error_label.setObjectName("error")
        self.verify_error_label.hide()
        
        layout.addStretch()
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.otp_input)
        layout.addWidget(self.verify_error_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(verify_button)
        layout.addWidget(resend_button)
        layout.addStretch()
        
        self.stacked_widget.addWidget(verification_page)

    def handle_signup(self):
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        phone = self.phone_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        if not all([name, email, phone, password, confirm_password]):
            self.show_error("Please fill in all fields")
            return
        
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            self.show_error("Please enter a valid email address")
            return
        
        if not phone.startswith('+'):
            self.show_error("Phone number must start with country code (e.g., +1)")
            return
        
        if len(password) < 6:
            self.show_error("Password must be at least 6 characters long")
            return
        
        if password != confirm_password:
            self.show_error("Passwords do not match")
            return
        
        self.user_data = {'name': name, 'email': email, 'phone': phone, 'password': password}
        self.send_verification_code()

    def send_verification_code(self):
        try:
            self.verification_code = str(random.randint(100000, 999999))
            self.twilio_client.messages.create(
                body=f"Your AlertMe verification code is: {self.verification_code}",
                from_=os.getenv('TWILIO_PHONE_NUMBER'),
                to=self.user_data['phone']
            )
            self.stacked_widget.setCurrentIndex(1)
        except Exception as e:
            self.show_error(f"Failed to send verification code: {str(e)}")

    def verify_otp(self):
        entered_code = self.otp_input.text().strip()
        if entered_code == self.verification_code:
            try:
                response = requests.post(
                    'http://localhost:5000/signup',
                    json=self.user_data,
                    headers={'Content-Type': 'application/json'}
                )
                if response.status_code == 201:
                    QMessageBox.information(self, "Success", "Account created successfully!")
                    self.back_to_login()
                else:
                    self.show_error(response.json().get('message', 'Could not create account'))
                    self.stacked_widget.setCurrentIndex(0)
            except requests.exceptions.ConnectionError:
                self.show_error("Could not connect to server")
                self.stacked_widget.setCurrentIndex(0)
        else:
            self.verify_error_label.setText("Invalid verification code")
            self.verify_error_label.show()

    def show_error(self, message):
        self.error_label.setText(message)
        self.error_label.show()

    def clear_error(self):
        self.error_label.hide()
        self.verify_error_label.hide()

    def back_to_login(self):
        # Import LoginWindow only when needed to avoid circular import
        from .login_window import LoginWindow
        self.login_window = LoginWindow()
        self.login_window.show()
        self.close()
