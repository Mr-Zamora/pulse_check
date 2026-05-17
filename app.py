import csv
import os
import time
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from configuration import csv_lock, get_db, init_db, DISCONNECT_TIMEOUT

app = Flask(__name__)
app.secret_key = 'MY_SECRET_KEY_IS_A_LONG_RANDOM_STRING'


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, 'database')
QUESTIONS_CSV = os.path.join(DB_DIR, 'questions.csv')
RESPONSES_CSV = os.path.join(DB_DIR, 'responses.csv')

# --- In-memory questions cache (single process optimisation; safe with WAL SQLite) ---
questions_cache = None


# ===========================================================================
# CSV Helpers (questions.csv + responses.csv unchanged)
# ===========================================================================

def get_all_questions():
    global questions_cache
    if questions_cache is not None:
        return questions_cache
    questions = []
    if not os.path.exists(QUESTIONS_CSV):
        return questions
    with csv_lock:
        with open(QUESTIONS_CSV, 'r', encoding='utf-8') as f:
            questions = list(csv.DictReader(f))
    questions_cache = questions
    return questions


def read_questions(room_id=None):
    qs = get_all_questions()
    if room_id is None:
        return qs
    return [q for q in qs if str(q.get('room_id')) == str(room_id)]


def read_responses(room_id=None, question_id=None):
    responses = []
    if not os.path.exists(RESPONSES_CSV):
        return responses
    with csv_lock:
        with open(RESPONSES_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                match_room = (room_id is None) or (str(row.get('room_id')) == str(room_id))
                match_q = (question_id is None) or (str(row.get('question_id')) == str(question_id))
                if match_room and match_q:
                    responses.append(row)
    return responses


def write_question(question_dict):
    global questions_cache
    file_exists = os.path.exists(QUESTIONS_CSV)
    fieldnames = ['question_id', 'room_id', 'type', 'prompt', 'options', 'correct_answer']
    with csv_lock:
        with open(QUESTIONS_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow({k: question_dict.get(k, '') for k in fieldnames})
    questions_cache = None  # invalidate cache


def write_response(response_dict):
    file_exists = os.path.exists(RESPONSES_CSV)
    fieldnames = ['timestamp', 'room_id', 'student_name', 'question_id', 'answer', 'is_correct']
    with csv_lock:
        with open(RESPONSES_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow({k: response_dict.get(k, '') for k in fieldnames})


def normalize_answer(text):
    if text is None:
        return ""
    return str(text).strip().lower()


# ===========================================================================
# SQLite Room State Helpers
# ===========================================================================

def init_room(room_id):
    """Ensure a row exists in room_states for this room_id."""
    db = get_db()
    db.execute("""
        INSERT OR IGNORE INTO room_states (room_id) VALUES (?)
    """, (room_id,))
    db.commit()
    db.close()


def get_room_state(room_id):
    """Return room state as a plain dict, or None if room doesn't exist."""
    db = get_db()
    row = db.execute("SELECT * FROM room_states WHERE room_id = ?", (room_id,)).fetchone()
    db.close()
    if row is None:
        return None
    return dict(row)


def set_room_state(room_id, **kwargs):
    """Upsert fields on a room_states row."""
    if not kwargs:
        return
    cols = ', '.join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [room_id]
    db = get_db()
    db.execute(f"UPDATE room_states SET {cols} WHERE room_id = ?", vals)
    db.commit()
    db.close()


def touch_student(room_id, student_name):
    """Record or refresh a student's last_seen timestamp."""
    db = get_db()
    db.execute("""
        INSERT INTO student_last_seen (room_id, student_name, last_seen)
        VALUES (?, ?, ?)
        ON CONFLICT(room_id, student_name) DO UPDATE SET last_seen = excluded.last_seen
    """, (room_id, student_name, time.time()))
    db.commit()
    db.close()


def get_student_states(room_id):
    """Return dict of {student_name: {connection, state}} for a room."""
    db = get_db()
    rows = db.execute(
        "SELECT student_name, last_seen FROM student_last_seen WHERE room_id = ?",
        (room_id,)
    ).fetchall()
    db.close()

    now = time.time()
    states = {}
    for row in rows:
        status = "disconnected" if (now - row['last_seen']) > DISCONNECT_TIMEOUT else "connected"
        states[row['student_name']] = {"connection": status, "state": "thinking"}
    return states


# ===========================================================================
# Routes — Session & Authentication
# ===========================================================================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/join', methods=['POST'])
def join():
    student_name = request.form.get('student_name')
    room_id = request.form.get('room_id')
    if not student_name or not room_id:
        return redirect(url_for('index'))
    session['student_name'] = student_name
    session['room_id'] = room_id
    init_room(room_id)
    return redirect(url_for('room', room_id=room_id))


@app.route('/room/<room_id>')
def room(room_id):
    if 'student_name' not in session or session.get('room_id') != room_id:
        return redirect(url_for('index'))
    init_room(room_id)
    return render_template('student.html', student_name=session['student_name'], room_id=room_id)


@app.route('/teacher')
def teacher():
    room_id = request.args.get('room_id')
    return render_template('teacher.html', room_id=room_id)


# ===========================================================================
# Routes — Room State API
# ===========================================================================

@app.route('/api/room/status')
def room_status():
    room_id = request.args.get('room_id')
    role = request.args.get('role')

    if not room_id:
        return jsonify({"status": "error", "message": "Missing room_id"}), 400

    init_room(room_id)

    # Update student presence (prefer explicit query param over shared session cookie)
    student_name = None
    if role != 'teacher':
        explicit_name = request.args.get('student_name')
        if explicit_name:
            student_name = explicit_name
        elif 'student_name' in session and session.get('room_id') == room_id:
            student_name = session['student_name']

    if student_name:
        touch_student(room_id, student_name)

    state = get_room_state(room_id)

    # Calculate time remaining
    now = time.time()
    time_remaining = 0
    timer_type = None

    if state['state'] == 'WAITING' and state['instruction_start']:
        elapsed = now - state['instruction_start']
        time_remaining = max(0, state['instruction_duration'] - elapsed)
        timer_type = 'instruction'

        # Auto-transition to ACTIVE when instruction timer expires
        if time_remaining == 0 and state['auto_start']:
            set_room_state(room_id, state='ACTIVE', quiz_start=now)
            state = get_room_state(room_id)
            time_remaining = state['quiz_duration']
            timer_type = 'quiz'

    elif state['state'] == 'ACTIVE' and state['quiz_start']:
        elapsed = now - state['quiz_start']
        time_remaining = max(0, state['quiz_duration'] - elapsed)
        timer_type = 'quiz'

    # Fetch current question details (strip answer before sending to student)
    question_data = None
    if state['current_q']:
        questions = read_questions(room_id)
        for q in questions:
            if q['question_id'] == state['current_q']:
                question_data = q.copy()
                question_data.pop('correct_answer', None)
                break

    return jsonify({
        "status": "success",
        "room_state": state['state'],
        "current_question_id": state['current_q'],
        "time_remaining_seconds": int(time_remaining),
        "timer_type": timer_type,
        "question_data": question_data,
        "show_responses": bool(state.get('show_responses', 0))
    })


# ===========================================================================
# Routes — Teacher Control API
# ===========================================================================

@app.route('/api/teacher/control', methods=['POST'])
def teacher_control():
    data = request.get_json()
    action = data.get('action')
    room_id = data.get('room_id')

    if not room_id or not action:
        return jsonify({"status": "error", "message": "Missing room_id or action"}), 400

    init_room(room_id)
    now = time.time()

    if action == 'prepare':
        set_room_state(room_id,
            state='WAITING',
            current_q=data.get('q_id'),
            instruction_start=now,
            instruction_duration=int(data.get('instruction_time', 120)),
            quiz_duration=int(data.get('quiz_time', 120)),
            quiz_start=None,
            auto_start=1 if data.get('auto_start') else 0
        )
    elif action == 'start':
        set_room_state(room_id, state='ACTIVE', quiz_start=now)
    elif action == 'lock':
        set_room_state(room_id, state='LOCKED')
    elif action == 'reset':
        set_room_state(room_id,
            state='WAITING',
            current_q=None,
            instruction_start=None,
            quiz_start=None,
            show_responses=0
        )

    new_state = get_room_state(room_id)['state']
    return jsonify({"status": "success", "message": f"Action {action} processed", "new_state": new_state})


@app.route('/api/teacher/toggle_responses', methods=['POST'])
def toggle_responses():
    try:
        data = request.get_json()
        room_id = data.get('room_id')
        show = data.get('show', False)
        
        if not room_id:
            return jsonify({"status": "error", "message": "Missing room_id"}), 400
        
        init_room(room_id)
        set_room_state(room_id, show_responses=1 if show else 0)
        
        return jsonify({"status": "success", "show_responses": show})
    except Exception as e:
        print(f"Error in toggle_responses: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ===========================================================================
# Routes — Question Management API
# ===========================================================================

@app.route('/api/teacher/questions')
def get_questions():
    room_id = request.args.get('room_id')
    if not room_id:
        return jsonify({"status": "error", "message": "Missing room_id"}), 400
    return jsonify({"status": "success", "questions": read_questions(room_id)})


@app.route('/api/teacher/add_question', methods=['POST'])
def add_question():
    data = request.get_json()
    room_id = data.get('room_id')
    q_type = data.get('type')
    prompt = data.get('prompt')

    if not room_id or not q_type or not prompt:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    q_id = f"q_{str(uuid.uuid4())[:8]}"
    options_str = ""
    if q_type == "MCQ" and "options" in data:
        options_str = "|".join(data['options'])

    write_question({
        'question_id': q_id,
        'room_id': room_id,
        'type': q_type,
        'prompt': prompt,
        'options': options_str,
        'correct_answer': data.get('correct_answer', '')
    })
    return jsonify({"status": "success", "question_id": q_id})


# ===========================================================================
# Routes — Student Submission API
# ===========================================================================

@app.route('/api/submit', methods=['POST'])
def submit():
    data = request.get_json()
    q_id = data.get('q_id')
    ans = data.get('ans')
    room_id = data.get('room_id')
    student_name = data.get('student_name')

    if not all([q_id, ans, room_id, student_name]):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    init_room(room_id)
    state = get_room_state(room_id)['state']

    if state not in ("ACTIVE", "LOCKED"):
        return jsonify({"status": "error", "message": "Room is not accepting submissions"}), 400

    # Evaluate correctness
    questions = read_questions(room_id)
    target_q = next((q for q in questions if q['question_id'] == q_id), None)

    is_correct = False
    if target_q:
        if target_q['type'] == 'SHORT':
            is_correct = normalize_answer(ans) == normalize_answer(target_q['correct_answer'])
        else:
            is_correct = str(ans).strip() == str(target_q['correct_answer']).strip()

    write_response({
        'timestamp': datetime.utcnow().isoformat() + "Z",
        'room_id': room_id,
        'student_name': student_name,
        'question_id': q_id,
        'answer': ans,
        'is_correct': str(is_correct)
    })
    return jsonify({"status": "success", "is_correct": is_correct, "message": "Submission recorded"})


# ===========================================================================
# Routes — Teacher Analytics API
# ===========================================================================

@app.route('/api/teacher/responses')
def get_responses():
    room_id = request.args.get('room_id')
    q_id = request.args.get('question_id')

    if not room_id:
        return jsonify({"status": "error", "message": "Missing room_id"}), 400

    responses = []
    target_q = None
    stats = {}

    if q_id and q_id != 'null':
        responses = read_responses(room_id, q_id)
        questions = read_questions(room_id)
        target_q = next((q for q in questions if q['question_id'] == q_id), None)

        if target_q:
            if target_q['type'] == 'MCQ':
                for r in responses:
                    ans = r['answer']
                    stats[ans] = stats.get(ans, 0) + 1
            elif target_q['type'] == 'SHORT':
                for r in responses:
                    norm_ans = normalize_answer(r['answer'])
                    if norm_ans not in stats:
                        stats[norm_ans] = {"count": 0, "raw": r['answer']}
                    stats[norm_ans]["count"] += 1

    # Student states from SQLite
    student_states = get_student_states(room_id)

    if target_q:
        for r in responses:
            name = r['student_name']
            if name in student_states:
                if target_q['type'] == 'MCQ':
                    student_states[name]["state"] = "mcq_correct" if r['is_correct'] == 'True' else "mcq_incorrect"
                else:
                    student_states[name]["state"] = "short_submit"

    return jsonify({
        "status": "success",
        "question_type": target_q['type'] if target_q else None,
        "question_data": target_q,
        "stats": stats,
        "student_states": student_states,
        "total_submitted": len(responses)
    })


# ===========================================================================
# App Entry Point
# ===========================================================================

if __name__ == '__main__':
    os.makedirs(DB_DIR, exist_ok=True)
    init_db()
    app.run(debug=True, port=5000)
