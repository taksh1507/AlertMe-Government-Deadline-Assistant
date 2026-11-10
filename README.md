# AlertMe — Government Deadline Assistant

[![GUI: PyQt6](https://img.shields.io/badge/GUI-PyQt6-4479A1?logo=python&logoColor=white)](Alertme/src/frontend)
[![Backend: Flask](https://img.shields.io/badge/backend-Flask-000000?logo=flask&logoColor=white)](Alertme/src/backend)
[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](Alertme/requirements.txt)
[![Database: MongoDB](https://img.shields.io/badge/database-MongoDB-4EA94B?logo=mongodb&logoColor=white)](Alertme/src/backend)
[![Auth: Firebase + JWT](https://img.shields.io/badge/auth-Firebase%20%7C%20JWT-FFCA28?logo=firebase&logoColor=white)](Alertme/src/backend)
[![Notifications: Twilio](https://img.shields.io/badge/notifications-Twilio-F22F46?logo=twilio&logoColor=white)](Alertme/src/backend/services)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**AlertMe is a desktop application that helps users track and manage government deadlines efficiently.** It provides notifications, deadline management, and a user-friendly interface for both regular users and administrators, with an admin panel for government deadline publishing.

> Copyright (c) 2025 AlertMe. All rights reserved. Non-commercial use only — see LICENSE.

## Features

- **User authentication system** — signup, login, JWT-based sessions
- **Personal deadline management** — create, track, organize deadlines by priority
- **Government deadline tracking** — admin-published official deadlines
- **SMS and email notifications** — deadline reminders via Twilio and SMTP
- **Interactive calendar view** — visualize upcoming deadlines
- **Admin panel** — government users publish and manage official deadlines
- **Real-time deadline updates** — live status changes across the app
- **Priority-based organization** — sort and filter deadlines by urgency

## Technology Stack

| Layer | Choice | Purpose |
| --- | --- | --- |
| Desktop GUI | PyQt6 | Cross-platform desktop windows and widgets |
| Backend API | Flask + Flask-CORS | REST API serving the desktop client |
| Database | MongoDB (pymongo) | Users, deadlines, notifications |
| Auth | Firebase Admin + PyJWT | Authentication and JWT sessions |
| Notifications | Twilio (SMS), SMTP (email) | Deadline reminders |
| Secrets | python-dotenv | Environment-based configuration |

## Project Structure

```text
AlertMe/
├── Alertme/                        # Application source
│   ├── main.py                     # PyQt6 entry point (LoginWindow)
│   ├── requirements.txt            # Pinned Python dependencies
│   ├── src/
│   │   ├── __init__.py
│   │   ├── app.py                  # Flask application factory
│   │   ├── backend/
│   │   │   ├── __init__.py
│   │   │   ├── routes/             # auth, admin, deadline route blueprints
│   │   │   │   ├── admin_routes.py
│   │   │   │   └── auth_routes.py
│   │   │   ├── services/           # deadline scanner, notification service
│   │   │   │   ├── deadline_scanner.py
│   │   │   │   └── notification_service.py
│   │   │   ├── models/             # deadline, personal_deadline, user models
│   │   │   │   ├── deadline.py
│   │   │   │   ├── personal_deadline.py
│   │   │   │   └── user.py
│   │   │   └── utils/              # auth utilities
│   │   │       └── auth_utils.py
│   │   ├── database/               # db_connector.py (MongoDB)
│   │   └── frontend/
│   │       ├── components/         # reusable Qt widgets/dialogs
│   │       │   ├── deadline_dialog.py
│   │       │   ├── fancy_widgets.py
│   │   │   └── government_deadline_dialog.py
│   │       └── windows/            # login window and other top-level windows
│   └── .env                        # tracked secrets file — see Security notes
├── CLOUD_SETUP.txt
├── DOCUMENTATION.txt
├── NOTIFICATION_SETUP.txt
├── SETUP.txt
├── .gitignore
├── LICENSE
└── README.md
```

## Setup

```bash
# Clone the repository
git clone https://github.com/taksh1507/AlertMe-Government-Deadline-Assistant.git
cd AlertMe-Government-Deadline-Assistant/Alertme

# Create a virtual environment and install dependencies
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
# Copy your credentials into Alertme/.env (see Security notes below)
# The app expects JWT_SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD, MongoDB URI,
# Twilio credentials, Firebase credentials, and OpenAI key as applicable.

# Run
python main.py
```

The desktop GUI requires a working display; there is no headless mode.

## Verification Status

Verified in this audit:

| Check | Result |
| --- | --- |
| Python syntax (`compileall` on `main.py` + `src/`) | PASS — all files parse cleanly |
| Dependency install (`pip install -r requirements.txt`) | environment-limited — see notes below |
| GUI runtime | not testable here — PyQt6 desktop app requires a display and PyQt6 wheels for this Python version |

Notes:
- `requirements.txt` pins `PyQt6==6.5.0`, `Flask==2.3.2`, `openai==0.27.8` and other older pins that have no Python 3.14 wheels. Install unpinned newer versions on modern Python; the dependency set targets older Python releases.
- No test suite or CI workflow exists in the repository; verification above is syntax-level, not automated.

## Fixes Applied (this audit)

1. **`src/backend/routes/auth_routes.py:61`** — missing comma in `jwt.encode({...}, os.getenv('JWT_SECRET_KEY'), algorithm='HS256')` caused a syntax error; the app could not even import.
2. **`src/backend/routes/auth_routes.py`** — `datetime.utcnow()` (removed in Python 3.12) replaced with `datetime.now(timezone.utc)` for forward compatibility.

## ⚠️ Security Notes

1. **`Alertme/.env` is tracked in git** (444 bytes) although `.env` appears in `.gitignore`. A tracked `.env` typically contains secrets (JWT secret, admin credentials, MongoDB URI, Twilio/Firebase/OpenAI keys). **Recommended:** remove it from tracking (`git rm --cached Alertme/.env`) and rotate any credentials it contains. Do not print or commit its contents.
2. `auth_routes.py` falls back to placeholder admin credentials (`your_admin_email` / `your_admin_password`) when env vars are unset — set real values in `.env` before any non-personal use.
3. Never commit real Twilio, Firebase, or OpenAI credentials.

## License

MIT License — see [LICENSE](LICENSE) for details.
