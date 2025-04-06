from PyQt6.QtWidgets import QPushButton, QFrame, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

class FancyButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            FancyButton {
                background-color: #f8fafc;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                padding: 8px 16px;
                color: #1e293b;
                font-weight: bold;
            }
            FancyButton:hover {
                background-color: #f1f5f9;
                border-color: #94a3b8;
            }
            FancyButton:pressed {
                background-color: #e2e8f0;
            }
            FancyButton:checked {
                background-color: #3b82f6;
                border-color: #2563eb;
                color: white;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(2, 2)
        self.setGraphicsEffect(shadow)

class FancyFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            FancyFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 25))
        shadow.setOffset(3, 3)
        self.setGraphicsEffect(shadow)