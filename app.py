import csv
import os
import time
import uuid
import zipfile
from io import BytesIO
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from configuration import csv_lock, get_db, init_db, DISCONNECT_TIMEOUT

# Admin credentials - stored in admin.py (NOT committed to Git)
# Copy admin.py.example to admin.py and set your own credentials
try:
    from admin import ADMIN_USERNAME, ADMIN_PASSWORD, SECRET_KEY
    app = Flask(__name__)
    app.secret_key = SECRET_KEY
except ImportError as e:
    print(f"WARNING: admin.py not found! Copy admin.py.example to admin.py and set credentials. Error: {e}")
    app = Flask(__name__)
    app.secret_key = 'MY_SECRET_KEY_IS_A_LONG_RANDOM_STRING'
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "changeme"
except Exception as e:
    print(f"ERROR loading admin.py: {e}")
    app = Flask(__name__)
    app.secret_key = 'MY_SECRET_KEY_IS_A_LONG_RANDOM_STRING'
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "changeme"


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, 'database')
QUESTIONS_CSV = os.path.join(DB_DIR, 'questions.csv')
# --- In-memory cache for questions.csv (questions rarely change) ---
questions_cache = None


# ===========================================================================
# CSV Helpers (questions.csv only — responses now in SQLite)
# ===========================================================================

def get_all_questions():
    global questions_cache
    if questions_cache is not None:
        return list(questions_cache)

    if not os.path.exists(QUESTIONS_CSV):
        return []

    with csv_lock:
        with open(QUESTIONS_CSV, 'r', encoding='utf-8') as f:
            loaded = list(csv.DictReader(f))
        if questions_cache is None:  # second check: another thread may have filled it
            questions_cache = loaded
        return list(questions_cache)


def read_questions(room_id=None):
    qs = get_all_questions()
    if room_id is None:
        return qs
    return [q for q in qs if str(q.get('room_id')) == str(room_id)]


def read_responses(room_id=None, question_id=None):
    db = get_db()
    if room_id and question_id:
        rows = db.execute(
            "SELECT * FROM responses WHERE room_id = ? AND question_id = ?",
            (room_id, question_id)
        ).fetchall()
    elif room_id:
        rows = db.execute(
            "SELECT * FROM responses WHERE room_id = ?", (room_id,)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM responses").fetchall()
    return [dict(r) for r in rows]


def write_question(question_dict):
    global questions_cache
    fieldnames = ['question_id', 'room_id', 'type', 'prompt', 'options', 'correct_answer']
    with csv_lock:
        file_exists = os.path.exists(QUESTIONS_CSV)  # checked inside lock to avoid TOCTOU
        with open(QUESTIONS_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow({k: question_dict.get(k, '') for k in fieldnames})
        questions_cache = None  # invalidate cache


def write_response(response_dict):
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO responses "
        "(timestamp, room_id, student_name, question_id, answer, is_correct) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            response_dict.get('timestamp', ''),
            response_dict['room_id'],
            response_dict['student_name'],
            response_dict['question_id'],
            response_dict.get('answer', ''),
            response_dict.get('is_correct', '')
        )
    )
    db.commit()


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


def get_room_state(room_id):
    """Return room state as a plain dict, or None if room doesn't exist."""
    db = get_db()
    row = db.execute("SELECT * FROM room_states WHERE room_id = ?", (room_id,)).fetchone()
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


def touch_student(room_id, student_name):
    """Record or refresh a student's last_seen timestamp. Returns False if student was kicked."""
    db = get_db()
    # Check if student was kicked (last_seen = -1)
    existing = db.execute(
        "SELECT last_seen FROM student_last_seen WHERE room_id = ? AND student_name = ?",
        (room_id, student_name)
    ).fetchone()
    
    if existing and existing['last_seen'] == -1:
        return False  # Student was kicked
    
    db.execute("""
        INSERT INTO student_last_seen (room_id, student_name, last_seen)
        VALUES (?, ?, ?)
        ON CONFLICT(room_id, student_name) DO UPDATE SET last_seen = excluded.last_seen
    """, (room_id, student_name, time.time()))
    db.commit()
    return True


def get_student_states(room_id):
    """Return dict of {student_name: {connection, state}} for a room."""
    db = get_db()
    rows = db.execute(
        "SELECT student_name, last_seen FROM student_last_seen WHERE room_id = ? AND last_seen != -1",
        (room_id,)
    ).fetchall()

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
    
    # Clear any kicked flag if student is rejoining
    db = get_db()
    db.execute("""
        UPDATE student_last_seen 
        SET last_seen = ? 
        WHERE room_id = ? AND student_name = ? AND last_seen = -1
    """, (time.time(), room_id, student_name))
    db.commit()
    
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

    # Only init room if it doesn't exist (reduces writes)
    state = get_room_state(room_id)
    if state is None:
        init_room(room_id)
        state = get_room_state(room_id)

    # Update student presence (prefer explicit query param over shared session cookie)
    student_name = None
    if role != 'teacher':
        explicit_name = request.args.get('student_name')
        if explicit_name:
            student_name = explicit_name
        elif 'student_name' in session and session.get('room_id') == room_id:
            student_name = session['student_name']

    if student_name:
        if not touch_student(room_id, student_name):
            # Student was kicked
            return jsonify({
                "status": "error",
                "error_type": "student_removed",
                "message": "You have been removed from this room by the teacher."
            }), 403

    # Calculate time remaining
    now = time.time()
    time_remaining = 0
    timer_type = None

    if state['state'] == 'WAITING' and state['instruction_start']:
        elapsed = now - state['instruction_start']
        time_remaining = max(0, state['instruction_duration'] - elapsed)
        timer_type = 'instruction'

        # Auto-transition to ACTIVE when instruction timer expires.
        # Use a conditional UPDATE so only one concurrent request wins;
        # subsequent polls land on the ACTIVE branch without a redundant write.
        if time_remaining == 0 and state['auto_start']:
            db = get_db()
            db.execute(
                "UPDATE room_states SET state='ACTIVE', quiz_start=?"
                " WHERE room_id=? AND state='WAITING'",
                (now, room_id)
            )
            db.commit()
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
                # Check if multi-select before removing correct_answer
                is_multi_select = ',' in q.get('correct_answer', '')
                question_data.pop('correct_answer', None)
                question_data['is_multi_select'] = is_multi_select
                break

    # Check if student has already submitted for this question (only for students)
    has_submitted = False
    if student_name and state['current_q']:
        responses = read_responses(room_id, state['current_q'])
        has_submitted = any(
            r['student_name'] == student_name and r.get('is_correct') != 'DELETED'
            for r in responses
        )

    return jsonify({
        "status": "success",
        "room_state": state['state'],
        "current_question_id": state['current_q'],
        "time_remaining_seconds": int(time_remaining),
        "timer_type": timer_type,
        "question_data": question_data,
        "show_responses": bool(state.get('show_responses', 0)),
        "has_submitted": has_submitted
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
            auto_start=1 if data.get('auto_start') else 0,
            show_responses=0  # Auto-disable show_responses for new question
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


@app.route('/api/teacher/delete_student', methods=['POST'])
def delete_student():
    try:
        data = request.get_json()
        room_id = data.get('room_id')
        student_name = data.get('student_name')
        
        if not room_id or not student_name:
            return jsonify({"status": "error", "message": "Missing room_id or student_name"}), 400
        
        print(f"Deleting student: room_id={room_id}, student_name={student_name}")
        
        # Mark student as kicked by setting last_seen to -1 (special value)
        db = get_db()
        cursor = db.execute("UPDATE student_last_seen SET last_seen = -1 WHERE room_id = ? AND student_name = ?", 
                   (room_id, student_name))
        rows_affected = cursor.rowcount
        db.commit()
        
        print(f"Rows affected: {rows_affected}")
        
        return jsonify({"status": "success", "rows_affected": rows_affected})
    except Exception as e:
        print(f"Error deleting student: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/teacher/delete_response', methods=['POST'])
def delete_response():
    try:
        data = request.get_json()
        room_id = data.get('room_id')
        question_id = data.get('question_id')
        normalized_answer = data.get('normalized_answer')

        if not room_id or not question_id or normalized_answer is None:
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        db = get_db()
        cursor = db.execute(
            "UPDATE responses SET is_correct = 'DELETED' "
            "WHERE room_id = ? AND question_id = ? AND LOWER(TRIM(answer)) = ?",
            (room_id, question_id, normalized_answer)
        )
        db.commit()

        return jsonify({"status": "success", "deleted_count": cursor.rowcount})
    except Exception as e:
        print(f"Error deleting response: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


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
            # SHORT answers can be resubmitted: atomically delete the prior answer.
            db = get_db()
            db.execute(
                "DELETE FROM responses WHERE room_id = ? AND student_name = ? AND question_id = ?",
                (room_id, student_name, q_id)
            )
            db.commit()
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
                    # Skip deleted responses
                    if r.get('is_correct') == 'DELETED':
                        continue
                    ans = r['answer']
                    # Handle multi-select: split by comma and count each option
                    if ',' in ans:
                        options = [opt.strip() for opt in ans.split(',')]
                        for opt in options:
                            stats[opt] = stats.get(opt, 0) + 1
                    else:
                        stats[ans] = stats.get(ans, 0) + 1
            elif target_q['type'] == 'SHORT':
                for r in responses:
                    # Skip deleted responses
                    if r.get('is_correct') == 'DELETED':
                        continue
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
                    student_states[name]["answer"] = r['answer']
                else:
                    student_states[name]["state"] = "short_submit"
                    student_states[name]["answer"] = r['answer']

    return jsonify({
        "status": "success",
        "question_type": target_q['type'] if target_q else None,
        "question_data": target_q,
        "stats": stats,
        "student_states": student_states,
        "total_submitted": len(responses)
    })


# ===========================================================================
# Admin Routes & API
# ===========================================================================

def admin_required(f):
    """Decorator to protect admin endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_authenticated'):
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_authenticated'] = True
            return redirect('/admin')
        else:
            return render_template('admin_login.html', error="Invalid credentials")
    
    if session.get('admin_authenticated'):
        return redirect('/admin')
    
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_authenticated', None)
    return redirect('/admin/login')


@app.route('/admin')
def admin():
    if not session.get('admin_authenticated'):
        return redirect('/admin/login')
    
    return render_template('admin.html')


@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    try:
        db = get_db()
        
        # Count rooms
        room_count = db.execute("SELECT COUNT(*) as cnt FROM room_states").fetchone()['cnt']
        
        # Count connected students (last_seen != -1)
        student_count = db.execute(
            "SELECT COUNT(*) as cnt FROM student_last_seen WHERE last_seen != -1"
        ).fetchone()['cnt']
        
        # Count questions
        questions = get_all_questions()
        question_count = len(questions)
        
        # Count responses
        response_count = db.execute(
            "SELECT COUNT(*) FROM responses WHERE is_correct != 'DELETED'"
        ).fetchone()[0]
        
        return jsonify({
            "status": "success",
            "stats": {
                "rooms": room_count,
                "students": student_count,
                "questions": question_count,
                "responses": response_count
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/admin/rooms', methods=['GET'])
@admin_required
def admin_get_rooms():
    try:
        db = get_db()
        # Single query: all room columns + student count via LEFT JOIN
        rooms = db.execute("""
            SELECT rs.room_id, rs.state, rs.current_q, rs.show_responses,
                   rs.instruction_start, rs.instruction_duration,
                   rs.quiz_start, rs.quiz_duration,
                   COUNT(sl.student_name) AS student_count
            FROM room_states rs
            LEFT JOIN student_last_seen sl
                ON sl.room_id = rs.room_id AND sl.last_seen != -1
            GROUP BY rs.room_id
        """).fetchall()

        now = time.time()
        room_list = []
        for r in rooms:
            time_remaining = 0
            if r['state'] == 'WAITING' and r['instruction_start']:
                elapsed = now - r['instruction_start']
                time_remaining = max(0, r['instruction_duration'] - int(elapsed))
            elif r['state'] == 'ACTIVE' and r['quiz_start']:
                elapsed = now - r['quiz_start']
                time_remaining = max(0, r['quiz_duration'] - int(elapsed))

            room_list.append({
                'room_id': r['room_id'],
                'state': r['state'],
                'question_id': r['current_q'],
                'time_remaining': time_remaining,
                'show_responses': r['show_responses'],
                'student_count': r['student_count']
            })

        return jsonify({"status": "success", "rooms": room_list})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/admin/delete_room', methods=['POST'])
@admin_required
def admin_delete_room():
    try:
        data = request.get_json()
        room_id = data.get('room_id')
        
        if not room_id:
            return jsonify({"status": "error", "message": "Missing room_id"}), 400
        
        db = get_db()
        db.execute("DELETE FROM room_states WHERE room_id = ?", (room_id,))
        db.execute("DELETE FROM student_last_seen WHERE room_id = ?", (room_id,))
        db.commit()
        return jsonify({"status": "success", "message": f"Room {room_id} deleted"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/admin/delete_all_rooms', methods=['POST'])
@admin_required
def admin_delete_all_rooms():
    try:
        db = get_db()
        db.execute("DELETE FROM room_states")
        db.execute("DELETE FROM student_last_seen")
        db.commit()
        return jsonify({"status": "success", "message": "All rooms deleted"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/admin/delete_all_responses', methods=['POST'])
@admin_required
def admin_delete_all_responses():
    try:
        db = get_db()
        db.execute("DELETE FROM responses")
        db.commit()
        return jsonify({"status": "success", "message": "All responses deleted"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/admin/clear_disconnected', methods=['POST'])
@admin_required
def admin_clear_disconnected():
    try:
        db = get_db()
        cursor = db.execute("DELETE FROM student_last_seen WHERE last_seen = -1")
        count = cursor.rowcount
        db.commit()
        return jsonify({"status": "success", "message": f"Removed {count} disconnected students"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/admin/backup', methods=['GET'])
@admin_required
def admin_backup():
    try:
        from configuration import DB_PATH
        
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(DB_PATH, 'classroom_pulse.db')  # contains all responses
            zf.write(QUESTIONS_CSV, 'questions.csv')
        
        memory_file.seek(0)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'pulse_check_backup_{timestamp}.zip'
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===========================================================================
# App Entry Point
# ===========================================================================

if __name__ == '__main__':
    os.makedirs(DB_DIR, exist_ok=True)
    init_db()
    app.run(debug=True, port=5000)
