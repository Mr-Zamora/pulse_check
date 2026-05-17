# Classroom Pulse (Micro-Chunking Tool)

A lightweight, high-performance web application designed for active classroom engagement through "micro-chunking". It allows teachers to quickly distribute multiple-choice and short-answer questions, enforce strict instruction/quiz timers, and instantly visualize class comprehension.

## Features
- **Zero-Config Rooms:** Students just type their name and a Room ID to join. No accounts required.
- **Strict State Management:** Teachers control exactly when students can see questions and submit answers (`WAITING` -> `ACTIVE` -> `LOCKED`).
- **Real-Time Dashboards:** Instant visualization of student connection statuses, thinking states, and response distributions.
- **Privacy Mode:** One-click anonymization for projecting the dashboard to the class safely.
- **Thread-Safe CSV Backend:** No external database servers required. Uses atomic threading locks to safely write to CSV files in a concurrent classroom environment.

## Prerequisites
- Python 3.8+

## Setup & Running
1. Clone or download this repository.
2. Ensure you have Flask installed:
   ```bash
   pip install flask
   ```
3. Run the application:
   ```bash
   python app.py
   ```
4. The server will start on `http://localhost:5000`.

## User Guide
### Teacher
1. Navigate to `http://localhost:5000/teacher`.
2. Enter a unique Room ID (e.g., `1234`).
3. Click **"➕ Create New Question"** to build your first question.
4. Select the question from the dropdown and click **"Prepare Question"**. This starts the instruction timer and tells students to pay attention.
5. When ready, click **"Start Quiz Now"** to reveal the question to students and start the quiz timer.
6. Watch the real-time distribution bars and student roster update dynamically!

### Student
1. Navigate to `http://localhost:5000/`.
2. Enter your Name and the Room ID provided by the teacher.
3. Keep the tab open and follow the teacher's instructions! The UI will automatically transition based on the teacher's controls.

## Architecture
- **Backend:** Flask (Python)
- **Frontend:** Vanilla JS / Vanilla CSS / HTML5
- **Data Layer:** `questions.csv` and `responses.csv` (In-memory caching is implemented for high-performance concurrent reads).
- **Communication:** AJAX Long-Polling (`/api/room/status` and `/api/teacher/responses`).

## Development Notes
- The CSV database files are generated automatically in the `database/` folder upon first boot.
- If you need to clear the database, simply delete `responses.csv`.
