from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                            QLineEdit, QComboBox, QDateEdit, QTextEdit,
                            QPushButton)
from PyQt6.QtCore import QDate

class GovernmentDeadlineDialog(QDialog):
    def __init__(self, parent=None, deadline=None):
        super().__init__(parent)
        self.setWindowTitle("Government Deadline")
        self.setModal(True)
        self.deadline = deadline  # Store the original deadline
        
        layout = QVBoxLayout(self)
        
        # Title
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter title")
        layout.addWidget(QLabel("Title:"))
        layout.addWidget(self.title_input)
        
        # Department
        self.dept_input = QLineEdit()
        self.dept_input.setPlaceholderText("Enter department")
        layout.addWidget(QLabel("Department:"))
        layout.addWidget(self.dept_input)
        
        # Due Date
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("yyyy-MM-dd")  # Set consistent date format
        self.date_input.setDate(QDate.currentDate())
        layout.addWidget(QLabel("Due Date:"))
        layout.addWidget(self.date_input)
        
        # Priority
        self.priority_input = QComboBox()
        self.priority_input.addItems(["High", "Medium", "Low"])
        layout.addWidget(QLabel("Priority:"))
        layout.addWidget(self.priority_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter description")
        layout.addWidget(QLabel("Description:"))
        layout.addWidget(self.description_input)
        
        # Buttons
        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        
        save_btn.clicked.connect(self.validate_and_accept)
        cancel_btn.clicked.connect(self.reject)
        
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        # Fill data if editing
        if deadline:
            self.title_input.setText(deadline.get('title', ''))
            self.dept_input.setText(deadline.get('department', ''))
            self.description_input.setText(deadline.get('description', ''))
            self.priority_input.setCurrentText(deadline.get('priority', 'Medium'))
            
            if 'due_date' in deadline:
                try:
                    date = QDate.fromString(deadline['due_date'], "yyyy-MM-dd")
                    if date.isValid():
                        self.date_input.setDate(date)
                except Exception as e:
                    print(f"Error setting date: {str(e)}")

    def validate_and_accept(self):
        # Basic validation
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Title is required")
            return
        if not self.dept_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Department is required")
            return
        
        self.accept()

    def get_deadline_data(self):
        data = {
            'title': self.title_input.text().strip(),
            'department': self.dept_input.text().strip(),
            'due_date': self.date_input.date().toString("yyyy-MM-dd"),
            'priority': self.priority_input.currentText(),
            'description': self.description_input.toPlainText().strip()
        }
        
        # If editing, preserve the ID
        if self.deadline and 'id' in self.deadline:
            data['id'] = self.deadline['id']
            
        return data