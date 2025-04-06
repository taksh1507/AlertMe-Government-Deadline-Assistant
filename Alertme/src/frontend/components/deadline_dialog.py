from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QTextEdit, QComboBox, QPushButton,
                            QDateEdit, QMessageBox)
from PyQt6.QtCore import QDate
from datetime import datetime
import requests

class DeadlineDialog(QDialog):
    def __init__(self, parent=None, deadline_data=None, token=None):
        super().__init__(parent)
        self.deadline_data = deadline_data
        self.token = token
        self.setWindowTitle("Add Deadline" if not deadline_data else "Edit Deadline")
        self.setMinimumWidth(400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Title
        title_label = QLabel("Title:")
        self.title_input = QLineEdit()
        if self.deadline_data:
            self.title_input.setText(self.deadline_data['title'])
        layout.addWidget(title_label)
        layout.addWidget(self.title_input)

        # Description
        desc_label = QLabel("Description:")
        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(100)
        if self.deadline_data:
            self.desc_input.setText(self.deadline_data.get('description', ''))
        layout.addWidget(desc_label)
        layout.addWidget(self.desc_input)

        # Due Date
        date_label = QLabel("Due Date:")
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setMinimumDate(QDate.currentDate())
        if self.deadline_data:
            self.date_input.setDate(QDate.fromString(self.deadline_data['due_date'], 'yyyy-MM-dd'))
        else:
            self.date_input.setDate(QDate.currentDate())
        layout.addWidget(date_label)
        layout.addWidget(self.date_input)

        # Priority
        priority_label = QLabel("Priority:")
        self.priority_input = QComboBox()
        self.priority_input.addItems(['Low', 'Medium', 'High'])
        if self.deadline_data:
            self.priority_input.setCurrentText(self.deadline_data['priority'].capitalize())
        layout.addWidget(priority_label)
        layout.addWidget(self.priority_input)

        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_deadline)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def save_deadline(self):
        try:
            if not self.title_input.text().strip():
                QMessageBox.warning(self, "Error", "Title is required!")
                return

            # Get user_id from the token payload
            token_parts = self.token.split('.')
            import base64
            import json
            payload = json.loads(base64.b64decode(token_parts[1] + '=' * (-len(token_parts[1]) % 4)).decode('utf-8'))
            user_id = payload.get('sub')  # 'sub' contains the user_id in JWT

            deadline_data = {
                'title': self.title_input.text().strip(),
                'description': self.desc_input.toPlainText().strip(),
                'due_date': self.date_input.date().toString('yyyy-MM-dd'),
                'priority': self.priority_input.currentText().lower(),
                'status': 'pending',
                'type': 'personal',
                'user_id': user_id  # Add user_id to the request
            }

            url = 'http://localhost:5000/api/personal-deadlines'
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }

            if self.deadline_data:  # Edit existing deadline
                deadline_id = self.deadline_data.get('_id', self.deadline_data.get('id'))
                response = requests.put(
                    f'{url}/{deadline_id}',
                    json=deadline_data,
                    headers=headers,
                    timeout=5
                )
            else:  # Create new deadline
                response = requests.post(
                    url,
                    json=deadline_data,
                    headers=headers,
                    timeout=5
                )

            if response.status_code in [200, 201]:
                self.accept()
            else:
                error_msg = response.json().get('message', 'Failed to save deadline')
                QMessageBox.warning(self, "Error", f"{error_msg}\nStatus: {response.status_code}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")