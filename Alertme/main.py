"""
AlertMe - Government Deadline Assistant
Copyright (c) 2025 AlertMe. All rights reserved.

This software is for non-commercial use only.
Any commercial use, reproduction, or distribution without permission is strictly prohibited.
"""

import sys
from PyQt6.QtWidgets import QApplication
from src.frontend.windows.login_window import LoginWindow

def main():
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()