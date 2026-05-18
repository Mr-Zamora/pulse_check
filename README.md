# Pulse Check

A lightweight, real-time classroom feedback tool built on the **Micro-Chunking** pedagogical framework. It breaks instruction into strict cycles — teach → quiz → discuss — and gives teachers instant visibility into student comprehension without any accounts, logins, or heavy infrastructure.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)
![SQLite](https://img.shields.io/badge/SQLite-stdlib-blue?logo=sqlite)
![License](https://img.shields.io/badge/License-MIT-green)

---

## What Is Micro-Chunking?

Micro-Chunking is a high-frequency active learning strategy:

1. **2 minutes** — Teacher delivers a short chunk of instruction
2. **1–2 minutes** — Students respond to a quick MCQ or Short Answer question
3. **1 minute** — Teacher reviews live results and pivots if needed

Pulse Check enforces this cycle with server-side timers, state-locked submissions, and a real-time teacher dashboard.

---

## Features

| Feature | Description |
|---|---|
| 🚪 **Zero-config rooms** | Students join by name + room code — no accounts required |
| 🔄 **Live state machine** | `WAITING → ACTIVE → LOCKED` transitions pushed to all students in real-time |
| ⏱️ **Dual timer system** | Separate instruction and quiz countdown timers |
| 📊 **Real-time analytics** | MCQ bar charts and grouped Short Answer distributions update as students submit |
| 🎓 **Roster tracking** | Student connection status (Connected / Disconnected / Submitted / Correct / Incorrect) |
| 🔒 **Auto-submit on lock** | Partial answers are captured when teacher locks — pedagogically sound for formative assessment |
| 🙈 **Privacy mode** | One-click anonymize for projecting the dashboard in class |
| 🗃️ **Portable data** | Questions and responses stored as plain CSV — easy to export or analyse in Excel |
| 🌐 **PythonAnywhere ready** | SQLite state layer is process-safe for WSGI multi-worker deployments |

---

## Tech Stack

- **Backend:** Python / Flask
- **State Persistence:** SQLite (`sqlite3` stdlib — zero install)
- **Data Records:** CSV files (questions + student responses)
- **Frontend:** Vanilla JS + Vanilla CSS + Jinja2 templates
- **Communication:** AJAX long-polling (2s interval)

---

## Project Structure

```
pulse_check/
├── app.py                   # All Flask routes and business logic
├── configuration.py         # SQLite setup, CSV lock, constants
├── requirements.txt
│
├── database/
│   ├── classroom_pulse.db   # Auto-created on first run (gitignored)
│   ├── questions.csv        # Question bank (committed as seed data)
│   └── responses.csv        # Student responses (gitignored — privacy)
│
├── static/
│   ├── css/style.css
│   └── js/
│       ├── student.js       # Polling engine, form submission, auto-submit on lock
│       └── teacher.js       # Dashboard analytics, controls, question creator
│
├── templates/
│   ├── base.html
│   ├── index.html           # Student landing / join page
│   ├── student.html         # Live student view
│   └── teacher.html         # Teacher command centre
│
└── docs/
    ├── PLAN.md              # Implementation plan
    ├── SPEC.md              # Technical specification
    └── APP_DOCS.md          # Detailed app documentation
```

---

## Quick Start (Local)

```bash
# 1. Clone the repo
git clone https://github.com/Mr-Zamora/pulse_check.git
cd pulse_check

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up admin credentials (IMPORTANT!)
# Copy the example file and edit with your own credentials
cp admin.py.example admin.py
# Edit admin.py and change ADMIN_USERNAME, ADMIN_PASSWORD, and SECRET_KEY

# 4. Run
python app.py
```

Visit `http://localhost:5000`

> The SQLite database and CSV files are created automatically on first run.

### ⚠️ Admin Credentials Setup

The admin dashboard requires credentials stored in `admin.py`:

1. Copy `admin.py.example` to `admin.py`
2. Edit `admin.py` and change:
   - `ADMIN_USERNAME` (default: "admin")
   - `ADMIN_PASSWORD` (default: "changeme")
   - `SECRET_KEY` (generate with `import secrets; print(secrets.token_hex(32))`)
3. **Never commit `admin.py` to Git** — it's in `.gitignore` for security

Access the admin dashboard at `http://localhost:5000/admin/login`

---

## Teacher Workflow

1. Go to `http://localhost:5000/teacher` and enter a Room ID (e.g. `1234`)
2. Click **➕ Create New Question** to build your question bank
3. For each micro-chunk:
   - Select the question → set timers → click **Prepare Question**
   - Teach your content while the instruction timer counts down
   - Click **Start Quiz Now** (or enable auto-start)
   - Watch the real-time roster and distribution update as students submit
   - Click **Lock Submissions** when time is up
   - Discuss the results with the class

## Student Workflow

1. Go to `http://localhost:5000/` on any device
2. Enter your name and the Room ID from your teacher
3. Follow the on-screen prompts — the interface updates automatically

---

## Performance

**Optimized for 20-30+ concurrent students** with:
- Thread-local database connection pooling
- In-memory response caching with modification tracking
- Database indexes on frequently queried columns
- 2-second polling interval (reduced server load by 50%)
- WAL mode SQLite for better concurrent access
- **Thread-safe operations** - No race conditions under concurrent load

See [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md) for detailed metrics and [`docs/RACE_CONDITIONS.md`](docs/RACE_CONDITIONS.md) for concurrency analysis.

---

## Deployment

### Production (Recommended)

For live classroom use with 10+ students:

**Windows:**
```bash
run_production.bat
```

**Linux/Mac:**
```bash
chmod +x run_production.sh
./run_production.sh
```

This runs the app with:
- **Waitress** (Windows) or **Gunicorn** (Linux/Mac) production server
- Multiple worker processes for concurrent handling
- Proper logging and timeout configuration

### PythonAnywhere (Free Tier)

1. Upload the project folder to your PythonAnywhere files
2. In the **Web** tab, set the WSGI file to point to `app.py`
3. Set up `admin.py` with secure credentials
4. Reload the web app

> The default PythonAnywhere free tier uses a single WSGI worker. For better performance with larger classes, consider a paid tier with multiple workers.

---

## Data & Privacy

- `questions.csv` — question bank, safe to commit (no student data)
- `responses.csv` — student answers, **gitignored by default** — store and handle per your institution's data policy
- `classroom_pulse.db` — runtime state only, **gitignored** — contains no personally identifiable information beyond student-chosen display names

---

## Licence

MIT
