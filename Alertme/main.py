"""Launch the native AlertMe desktop application."""

import sys
from pathlib import Path
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication
from src.frontend.desktop import AlertMeWindow


def main():
    load_dotenv(Path(__file__).parent / ".env")
    application = QApplication(sys.argv)
    application.setApplicationName("AlertMe")
    window = AlertMeWindow()
    window.show()
    sys.exit(application.exec())


if __name__ == "__main__":
    main()
