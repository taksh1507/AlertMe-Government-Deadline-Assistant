STYLE = """
QWidget { font-family: "Inter", "DejaVu Sans", sans-serif; font-size: 13px; color: #35344b; }
QMainWindow, #workspace { background: #f7f7fb; }
#sidebar { background: #ffffff; border-right: 1px solid #e9e8f1; }
QLabel[tone="brand"] { font-size: 22px; font-weight: 700; color: #39334e; }
QLabel[tone="caption"] { font-size: 10px; color: #767187; }
QLabel[tone="heading"] { font-size: 28px; font-weight: 700; color: #302c46; }
QLabel[tone="subtitle"] { color: #706b80; font-size: 12px; }
QLabel[tone="eyebrow"] { color: #746795; font-size: 10px; font-weight: 600; }
#card { background: white; border: 1px solid #e7e5ef; border-radius: 12px; }
QLabel[tone="statValue"] { font-size: 30px; font-weight: 700; color: #514492; }
QLabel[tone="statCaption"] { font-size: 12px; color: #777084; }
QLabel[tone="sectionTitle"] { font-size: 15px; font-weight: 600; }
#heroPanel { background: #efebfa; border-radius: 16px; }
#authHero { background: #eeebf8; border-radius: 16px; }
QLabel[tone="authHeading"] { color: #45366e; font-size: 36px; font-weight: 700; }
QLabel[tone="notice"] { background: #eeebf8; color: #5d4d82; padding: 12px; border-radius: 8px; }
QLabel[tone="error"] { color: #ab3f4a; padding: 8px 0; }
QLabel[tone="success"] { color: #37714e; padding: 8px 0; }
QLineEdit, QTextEdit, QDateEdit, QComboBox { border: 1px solid #dcd9e8; border-radius: 7px; padding: 9px; background: white; color: #373147; selection-background-color: #ded4ff; }
QLineEdit:focus, QTextEdit:focus, QDateEdit:focus, QComboBox:focus { border: 1px solid #8270cc; }
QPushButton { padding: 9px 14px; border-radius: 7px; background: white; border: 1px solid #dedbe8; color: #544969; }
QPushButton:hover { background: #f1edf9; }
QPushButton:focus { border: 2px solid #8c7bc9; }
QPushButton:disabled { color: #9993a3; background: #efedf3; }
QPushButton[primary="true"] { background: #6355cd; color: white; border: 1px solid #6355cd; font-weight: 600; }
QPushButton[primary="true"]:hover { background: #5546b8; }
QPushButton[primary="true"]:disabled { background: #aca5d6; border: 1px solid #aca5d6; }
QPushButton#nav { text-align: left; border: 0; background: transparent; padding: 12px; color: #706981; }
QPushButton#nav:checked { background: #f0ecfb; color: #5946ad; font-weight: 600; }
QPushButton#danger { color: #a43f4a; }
QTableWidget { background: white; border: 0; gridline-color: #eeecf4; selection-background-color: #efebfa; selection-color: #39334e; alternate-background-color: #fcfbfd; }
QTableWidget::item { padding: 10px; border-bottom: 1px solid #eeecf4; }
QHeaderView::section { padding: 11px 9px; background: #faf9fc; color: #746b85; border: 0; border-bottom: 1px solid #e9e5f1; text-align: left; font-size: 11px; }
QScrollArea { border: 0; background: transparent; }
QScrollBar:vertical { background: transparent; width: 9px; margin: 0; }
QScrollBar::handle:vertical { background: #d3cde2; border-radius: 4px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QCheckBox { spacing: 8px; color: #5d546c; }
QCalendarWidget { background: white; border: 1px solid #e7e3ee; border-radius: 10px; }
QCalendarWidget QWidget#qt_calendar_navigationbar { background: #f1edf9; border-radius: 7px; }
QCalendarWidget QToolButton { color: #57477e; background: transparent; border: 0; padding: 8px; }
QCalendarWidget QAbstractItemView { background: white; color: #3e3652; selection-background-color: #6355cd; selection-color: white; outline: 0; }
QDialog { background: #faf9fc; }
QDialogButtonBox QPushButton { min-width: 90px; }
QProgressBar { border: 0; background: #eeeaf6; height: 7px; border-radius: 3px; text-align: center; }
QProgressBar::chunk { background: #a69acb; border-radius: 3px; }
QStatusBar { background: #f7f7fb; color: #766e85; font-size: 11px; }
QTabWidget::pane { border: 1px solid #e4dfec; background: white; border-radius: 8px; }
QTabBar::tab { padding: 10px 17px; background: #f1eef6; color: #6a5f7c; }
QTabBar::tab:selected { background: #e6e0f6; color: #544384; }
"""
