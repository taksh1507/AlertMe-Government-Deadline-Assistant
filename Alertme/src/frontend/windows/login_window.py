from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QLineEdit, QPushButton, QLabel, QFrame, QMessageBox,
                            QStackedWidget, QCheckBox)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QPixmap, QFont, QPalette, QColor
# Remove this line to avoid circular import
# from .signup_window import SignupWindow
import requests
from twilio.rest import Client
import os
from dotenv import load_dotenv
import re
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .admin_panel import AdminPanel

load_dotenv()

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AlertMe")
        self.showMaximized()  # Replace setFixedSize with showMaximized
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
        self.ADMIN_EMAIL = "admin@alertme.com"
        self.ADMIN_PASSWORD = "admin123"
        
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
        
        self.create_login_page()
        self.create_verification_page()

    def create_login_page(self):
        page = QWidget()
        page.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)
        main_layout = QHBoxLayout(page)
        
        # Enhanced Left Side
        left_widget = QWidget()
        left_widget.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        left_layout = QVBoxLayout(left_widget)
        
        logo_label = QLabel("🔔")
        logo_label.setStyleSheet("""
            font-size: 96px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 50%;
            margin: 20px;
        """)
        
        welcome_text = QLabel("Welcome to AlertMe")
        welcome_text.setObjectName("title")
        welcome_text.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        welcome_text.setStyleSheet("""
            color: white;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
        """)
        
        description = QLabel("OFFICALLY ON TRACK")
        description.setObjectName("subtitle")
        description.setFont(QFont("Segoe UI", 16))
        description.setStyleSheet("""
            color: #e3f2fd;
            text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.1);
            padding: 10px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
        """)
        
        left_layout.addStretch()
        left_layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(welcome_text, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(description, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addStretch()
        
        main_layout.addWidget(left_widget, 4)
        
        # Enhanced Right Side
        login_card = QFrame()
        login_card.setObjectName("loginCard")
        login_card.setStyleSheet("""
            #loginCard {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 25px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                padding: 40px;
                backdrop-filter: blur(10px);
                box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
            }
            QLineEdit {
                padding: 14px;
                border: 2px solid #bbdefb;
                border-radius: 12px;
                font-size: 15px;
                min-width: 320px;
                margin: 10px;
                background: rgba(255, 255, 255, 0.2);
                color: white;
                transition: all 0.3s ease;
            }
            QLineEdit:focus {
                border: 2px solid #42a5f5;
                background: rgba(255, 255, 255, 0.25);
                box-shadow: 0 0 10px rgba(66, 165, 245, 0.5);
            }
            QLineEdit::placeholder {
                color: rgba(255, 255, 255, 0.7);
                font-style: italic;
            }
            QPushButton#loginBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #2196f3, stop:1 #42a5f5);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 14px;
                font-size: 16px;
                font-weight: bold;
                min-width: 320px;
                margin: 10px;
                box-shadow: 0 4px 15px rgba(33, 150, 243, 0.4);
                transition: all 0.3s ease;
            }
            QPushButton#loginBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #1976d2, stop:1 #2196f3);
                box-shadow: 0 6px 20px rgba(33, 150, 243, 0.6);
                transform: translateY(-2px);
            }
            QPushButton#signupBtn {
                background: transparent;
                color: white;
                border: 2px solid #42a5f5;
                border-radius: 12px;
                padding: 14px;
                font-size: 16px;
                min-width: 320px;
                margin: 10px;
                transition: all 0.3s ease;
            }
            QPushButton#signupBtn:hover {
                background: rgba(66, 165, 245, 0.15);
                border-color: #64b5f6;
                box-shadow: 0 4px 15px rgba(66, 165, 245, 0.3);
            }
            QLabel#error {
                color: #ef5350;
                font-size: 14px;
                margin: 8px;
                background: rgba(239, 83, 80, 0.1);
                padding: 8px;
                border-radius: 6px;
            }
        """)
        login_layout = QVBoxLayout(login_card)
        
        title = QLabel("Sign In")
        title.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        # Replace text-shadow with border effects
        title.setStyleSheet("""
            color: white;
            margin: 10px 0 30px 0;
            padding: 10px;
            background-color: rgba(255, 255, 255, 0.05);
        """)
        
        # Replace box-shadow and transition with Qt-compatible properties
        login_card.setStyleSheet("""
            #loginCard {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 25px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                padding: 40px;
            }
            QLineEdit {
                padding: 14px;
                border: 2px solid #bbdefb;
                border-radius: 12px;
                font-size: 15px;
                min-width: 320px;
                margin: 10px;
                background: rgba(255, 255, 255, 0.2);
                color: white;
            }
            QLineEdit:focus {
                border: 2px solid #42a5f5;
                background: rgba(255, 255, 255, 0.25);
            }
            QPushButton#loginBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #2196f3, stop:1 #42a5f5);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 14px;
                font-size: 16px;
                font-weight: bold;
                min-width: 320px;
                margin: 10px;
            }
            QPushButton#loginBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #1976d2, stop:1 #2196f3);
            }
            QPushButton#signupBtn {
                background: transparent;
                color: white;
                border: 2px solid #42a5f5;
                border-radius: 12px;
                padding: 14px;
                font-size: 16px;
                min-width: 320px;
                margin: 10px;
            }
            QPushButton#signupBtn:hover {
                background: rgba(66, 165, 245, 0.15);
                border-color: #64b5f6;
            }
        """)
        subtitle = QLabel("Your Government Deadline Assistant")
        subtitle.setFont(QFont("Segoe UI", 14))
        subtitle.setStyleSheet("""
            color: #bbdefb;
            margin-bottom: 30px;
        """)
        
        self.identifier_input = QLineEdit()
        self.identifier_input.setPlaceholderText("Email or Phone Number")
        self.identifier_input.textChanged.connect(self.clear_error)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.textChanged.connect(self.clear_error)
        
        show_password = QCheckBox("Show Password")
        show_password.setStyleSheet("""
            QCheckBox {
                color: white;
                font-size: 14px;
                padding: 8px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 6px;
                border: 2px solid #bbdefb;
                background: rgba(255, 255, 255, 0.1);
                transition: all 0.2s ease;
            }
            QCheckBox::indicator:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #2196f3, stop:1 #42a5f5);
                border: none;
            }
            QCheckBox::indicator:hover {
                border-color: #64b5f6;
                box-shadow: 0 0 8px rgba(66, 165, 245, 0.3);
            }
        """)
        show_password.stateChanged.connect(lambda state: self.password_input.setEchoMode(
            QLineEdit.EchoMode.Normal if state else QLineEdit.EchoMode.Password
        ))
        
        self.error_label = QLabel()
        self.error_label.setObjectName("error")
        self.error_label.hide()
        
        login_button = QPushButton("Sign In")
        login_button.setObjectName("loginBtn")
        login_button.clicked.connect(self.handle_login)
        login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        signup_button = QPushButton("Create New Account")
        signup_button.setObjectName("signupBtn")
        signup_button.clicked.connect(self.open_signup)
        signup_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        login_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        login_layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignCenter)
        login_layout.addWidget(self.identifier_input)
        login_layout.addWidget(self.password_input)
        login_layout.addWidget(show_password, alignment=Qt.AlignmentFlag.AlignLeft)
        login_layout.addWidget(self.error_label, alignment=Qt.AlignmentFlag.AlignCenter)
        login_layout.addWidget(login_button)
        login_layout.addWidget(signup_button)
        
        main_layout.addWidget(login_card, 6)

        self.stacked_widget.addWidget(page)

    def create_verification_page(self):
        page = QWidget()
        page.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)
        layout = QVBoxLayout(page)
        
        title = QLabel("Verify Your Identity")
        title.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        title.setStyleSheet("""
            color: white;
            margin-bottom: 20px;
            background-color: rgba(255, 255, 255, 0.05);
            padding: 10px;
            border-radius: 8px;
        """)
        
        self.verification_subtitle = QLabel()
        self.verification_subtitle.setFont(QFont("Segoe UI", 14))
        self.verification_subtitle.setStyleSheet("""
            color: #e3f2fd;
            margin-bottom: 30px;
            padding: 10px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
        """)
        
        self.otp_input = QLineEdit()
        self.otp_input.setPlaceholderText("Enter 6-digit OTP")
        self.otp_input.setMaxLength(6)
        self.otp_input.setStyleSheet("""
            padding: 14px;
            border: 2px solid #bbdefb;
            border-radius: 12px;
            font-size: 15px;
            min-width: 320px;
            margin: 10px;
            background: rgba(255, 255, 255, 0.2);
            color: white;
        """)
        
        verify_button = QPushButton("Verify")
        verify_button.setObjectName("loginBtn")
        verify_button.clicked.connect(self.verify_otp)
        verify_button.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                      stop:0 #2196f3, stop:1 #42a5f5);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 14px;
            font-size: 16px;
            font-weight: bold;
            min-width: 320px;
            margin: 10px;
        """)
        verify_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        resend_button = QPushButton("Resend OTP")
        resend_button.setObjectName("signupBtn")
        resend_button.clicked.connect(self.send_verification_code)
        resend_button.setStyleSheet("""
            background: transparent;
            color: white;
            border: 2px solid #42a5f5;
            border-radius: 12px;
            padding: 14px;
            font-size: 16px;
            min-width: 320px;
            margin: 10px;
        """)
        resend_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        back_button = QPushButton("Back")
        back_button.setObjectName("signupBtn")
        back_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout.addStretch()
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.verification_subtitle, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.otp_input)
        layout.addWidget(verify_button)
        layout.addWidget(resend_button)
        layout.addWidget(back_button)
        layout.addStretch()
        
        self.stacked_widget.addWidget(page)

    # All other methods remain unchanged
    def handle_login(self):
        identifier = self.identifier_input.text().strip()
        password = self.password_input.text()
        
        if not identifier or not password:
            self.show_error("Please fill in all fields")
            return
        
        if identifier == self.ADMIN_EMAIL and password == self.ADMIN_PASSWORD:
            try:
                response = requests.post(
                    f'{self.api_base_url}/auth/api/admin/login',
                    json={
                        'email': identifier,
                        'password': password
                    },
                    headers={'Content-Type': 'application/json'}
                )
                
                try:
                    response_data = response.json()
                except ValueError:
                    self.show_error(f"Server error: {response.text}")
                    return
                
                if response.status_code == 200:
                    self.admin_panel = AdminPanel(response_data.get('token'))
                    self.admin_panel.show()
                    self.close()
                else:
                    error_msg = response_data.get('message', 'Admin authentication failed')
                    self.show_error(error_msg)
                return
            except requests.exceptions.ConnectionError:
                self.show_error("Could not connect to server")
                return
            except Exception as e:
                self.show_error(f"Authentication error: {str(e)}")
                return
        
        try:
            response = requests.post(
                'http://localhost:5000/login',
                json={
                    'identifier': identifier,
                    'password': password
                }
            )
            
            if response.status_code == 200:
                response_data = response.json()
                self.user_data = {
                    **response_data['user'],
                    'token': response_data['token']
                }
                self.send_verification_code()
                self.stacked_widget.setCurrentIndex(1)
            else:
                self.show_error("Invalid credentials")
        except requests.exceptions.ConnectionError:
            self.show_error("Could not connect to server")

    def send_verification_code(self):
        self.verification_code = str(random.randint(100000, 999999))
        identifier = self.identifier_input.text().strip()
        
        if '@' in identifier:
            self.verification_subtitle.setText(f"Enter the verification code sent to {identifier}")
            self.send_email_otp(identifier)
        else:
            self.verification_subtitle.setText(f"Enter the verification code sent to {identifier}")
            self.send_sms_otp(identifier)

    def send_email_otp(self, email):
        try:
            smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_username = os.getenv('SMTP_EMAIL')
            smtp_password = os.getenv('SMTP_PASSWORD')
            
            if not smtp_username or not smtp_password:
                raise ValueError("Email credentials not configured")
            
            msg = MIMEMultipart()
            msg['From'] = f"AlertMe <{smtp_username}>"
            msg['To'] = email
            msg['Subject'] = "AlertMe - Your Verification Code"
            
            body = f"""
            Hello,
            
            Your verification code for AlertMe is: {self.verification_code}
            
            This code will expire in 10 minutes.
            
            If you didn't request this code, please ignore this email.
            
            Best regards,
            AlertMe Team
            """
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
                print(f"OTP sent successfully to {email}")
                
        except ValueError as ve:
            print(f"Configuration error: {str(ve)}")
            self.show_error("Email service not configured properly")
            self.stacked_widget.setCurrentIndex(0)
        except Exception as e:
            print(f"Email error: {str(e)}")
            self.show_error("Failed to send email verification code")
            self.stacked_widget.setCurrentIndex(0)

    def send_sms_otp(self, phone):
        try:
            self.twilio_client.messages.create(
                body=f"Your AlertMe verification code is: {self.verification_code}",
                from_=os.getenv('TWILIO_PHONE_NUMBER'),
                to=phone
            )
        except Exception as e:
            print(f"SMS error: {str(e)}")
            self.show_error("Failed to send SMS verification code")
            self.stacked_widget.setCurrentIndex(0)

    def verify_otp(self):
        entered_code = self.otp_input.text().strip()
        if entered_code == self.verification_code:
            from .dashboard_window import DashboardWindow
            self.dashboard = DashboardWindow(self.user_data)
            self.dashboard.show()
            self.close()
        else:
            self.show_error("Invalid verification code")

    def show_error(self, message):
        self.error_label.setText(message)
        self.error_label.show()
    
    def clear_error(self):
        self.error_label.hide()
    
    def open_signup(self):
        # Import SignupWindow only when needed
        from .signup_window import SignupWindow
        self.signup_window = SignupWindow()
        self.signup_window.show()
        self.close()