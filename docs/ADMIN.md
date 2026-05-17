# Admin Page Implementation Guide

This document outlines the implementation plan for the admin dashboard with critical and easy-to-implement features.

---

## **Priority Features**

### **1. Delete All Rooms** ⭐ HIGHEST PRIORITY
**Purpose**: Clear all room state data for a fresh start

**Backend (app.py)**:
```python
@app.route('/api/admin/delete_all_rooms', methods=['POST'])
def delete_all_rooms():
    try:
        db = get_db()
        db.execute("DELETE FROM room_state")
        db.commit()
        db.close()
        return jsonify({"status": "success", "message": "All rooms deleted"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
```

**Frontend (admin.js)**:
```javascript
function deleteAllRooms() {
    if (!confirm('⚠️ Delete ALL rooms? This cannot be undone!')) return;
    
    fetch('/api/admin/delete_all_rooms', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                showToast('All rooms deleted', 'success');
                loadRoomList();
            }
        });
}
```

---

### **2. Delete All Responses**
**Purpose**: Clear all student response history

**Backend (app.py)**:
```python
@app.route('/api/admin/delete_all_responses', methods=['POST'])
def delete_all_responses():
    try:
        # Recreate empty responses.csv
        with csv_lock:
            with open(RESPONSES_CSV, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['timestamp', 'room_id', 'student_name', 'question_id', 'answer', 'is_correct'])
                writer.writeheader()
        return jsonify({"status": "success", "message": "All responses deleted"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
```

**Frontend (admin.js)**:
```javascript
function deleteAllResponses() {
    if (!confirm('⚠️ Delete ALL responses? This cannot be undone!')) return;
    
    fetch('/api/admin/delete_all_responses', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                showToast('All responses deleted', 'success');
            }
        });
}
```

---

### **3. Clear Disconnected Students**
**Purpose**: Remove students marked as kicked/disconnected (last_seen = -1)

**Backend (app.py)**:
```python
@app.route('/api/admin/clear_disconnected', methods=['POST'])
def clear_disconnected():
    try:
        db = get_db()
        cursor = db.execute("DELETE FROM student_last_seen WHERE last_seen = -1")
        count = cursor.rowcount
        db.commit()
        db.close()
        return jsonify({"status": "success", "message": f"Removed {count} disconnected students"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
```

**Frontend (admin.js)**:
```javascript
function clearDisconnected() {
    if (!confirm('Clear all disconnected students?')) return;
    
    fetch('/api/admin/clear_disconnected', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                showToast(data.message, 'success');
            }
        });
}
```

---

### **4. View All Rooms**
**Purpose**: Monitor all active rooms and their states

**Backend (app.py)**:
```python
@app.route('/api/admin/rooms', methods=['GET'])
def get_all_rooms():
    try:
        db = get_db()
        rooms = db.execute("""
            SELECT room_id, room_state, current_question_id, time_remaining_seconds, show_responses
            FROM room_state
        """).fetchall()
        
        room_list = []
        for r in rooms:
            # Count students in this room
            student_count = db.execute(
                "SELECT COUNT(*) as cnt FROM student_last_seen WHERE room_id = ? AND last_seen != -1",
                (r['room_id'],)
            ).fetchone()['cnt']
            
            room_list.append({
                'room_id': r['room_id'],
                'state': r['room_state'],
                'question_id': r['current_question_id'],
                'time_remaining': r['time_remaining_seconds'],
                'show_responses': r['show_responses'],
                'student_count': student_count
            })
        
        db.close()
        return jsonify({"status": "success", "rooms": room_list})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
```

**Frontend (admin.js)**:
```javascript
function loadRoomList() {
    fetch('/api/admin/rooms')
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                renderRoomTable(data.rooms);
            }
        });
}

function renderRoomTable(rooms) {
    let html = '<table><thead><tr><th>Room ID</th><th>State</th><th>Question</th><th>Students</th><th>Time</th></tr></thead><tbody>';
    
    rooms.forEach(room => {
        html += `<tr>
            <td>${room.room_id}</td>
            <td>${room.state}</td>
            <td>${room.question_id || 'None'}</td>
            <td>${room.student_count}</td>
            <td>${room.time_remaining}s</td>
        </tr>`;
    });
    
    html += '</tbody></table>';
    document.getElementById('room-list').innerHTML = html;
}
```

---

### **5. Database Backup**
**Purpose**: Download backup of database and CSV files

**Backend (app.py)**:
```python
import zipfile
from io import BytesIO
from flask import send_file

@app.route('/api/admin/backup', methods=['GET'])
def backup_database():
    try:
        # Create in-memory zip file
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(DATABASE_PATH, 'classroom_pulse.db')
            zf.write(RESPONSES_CSV, 'responses.csv')
            zf.write(QUESTIONS_CSV, 'questions.csv')
        
        memory_file.seek(0)
        
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'pulse_check_backup_{timestamp}.zip'
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
```

**Frontend (admin.js)**:
```javascript
function downloadBackup() {
    window.location.href = '/api/admin/backup';
    showToast('Downloading backup...', 'info');
}
```

---

## **Admin Page Structure**

### **HTML Template (templates/admin.html)**:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard - Pulse Check</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <div class="container">
        <h1>🔧 Admin Dashboard</h1>
        
        <section class="admin-section">
            <h2>Room Management</h2>
            <button class="btn-danger" onclick="deleteAllRooms()">Delete All Rooms</button>
            <button class="btn-primary" onclick="loadRoomList()">Refresh Room List</button>
            <div id="room-list"></div>
        </section>
        
        <section class="admin-section">
            <h2>Data Management</h2>
            <button class="btn-danger" onclick="deleteAllResponses()">Delete All Responses</button>
            <button class="btn-warning" onclick="clearDisconnected()">Clear Disconnected Students</button>
        </section>
        
        <section class="admin-section">
            <h2>Backup & Restore</h2>
            <button class="btn-primary" onclick="downloadBackup()">Download Backup</button>
        </section>
    </div>
    
    <div id="toast-container"></div>
    <script src="{{ url_for('static', filename='js/admin.js') }}"></script>
</body>
</html>
```

### **Route (app.py)**:
```python
@app.route('/admin')
def admin():
    return render_template('admin.html')
```

---

## **Security Implementation - Flask Session Login** ⭐ RECOMMENDED

### **Step 1: Add Admin Credentials to app.py**
```python
# At the top of app.py with other config
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "your_secure_password_here"  # Change this!

# Make sure you have a secret key for sessions
app.secret_key = 'your-secret-key-here'  # Change this to a random string!
```

### **Step 2: Create Login Route (app.py)**
```python
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
    
    # If already logged in, redirect to admin
    if session.get('admin_authenticated'):
        return redirect('/admin')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_authenticated', None)
    return redirect('/admin/login')

@app.route('/admin')
def admin():
    # Check if user is authenticated
    if not session.get('admin_authenticated'):
        return redirect('/admin/login')
    
    return render_template('admin.html')
```

### **Step 3: Protect Admin API Endpoints (app.py)**
```python
# Add this decorator function
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_authenticated'):
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

# Use it on all admin API endpoints
@app.route('/api/admin/delete_all_rooms', methods=['POST'])
@admin_required
def delete_all_rooms():
    try:
        db = get_db()
        db.execute("DELETE FROM room_state")
        db.commit()
        db.close()
        return jsonify({"status": "success", "message": "All rooms deleted"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Apply @admin_required to all other admin endpoints...
```

### **Step 4: Create Login Template (templates/admin_login.html)**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Login - Pulse Check</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <style>
        .login-container {
            max-width: 400px;
            margin: 100px auto;
            padding: 40px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .login-form input {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid #CBD5E1;
            border-radius: 6px;
            font-size: 16px;
        }
        .login-form button {
            width: 100%;
            padding: 12px;
            margin-top: 10px;
            background: #3B82F6;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            cursor: pointer;
        }
        .login-form button:hover {
            background: #2563EB;
        }
        .error-message {
            color: #EF4444;
            background: #FEE2E2;
            padding: 10px;
            border-radius: 6px;
            margin-bottom: 15px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1 style="text-align: center; margin-bottom: 30px;">🔐 Admin Login</h1>
        
        {% if error %}
        <div class="error-message">{{ error }}</div>
        {% endif %}
        
        <form method="POST" class="login-form">
            <input type="text" name="username" placeholder="Username" required autofocus>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        
        <p style="text-align: center; margin-top: 20px; color: #64748B;">
            <a href="/" style="color: #3B82F6;">← Back to Home</a>
        </p>
    </div>
</body>
</html>
```

### **Step 5: Add Logout Button to Admin Page (templates/admin.html)**
```html
<div class="container">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <h1>🔧 Admin Dashboard</h1>
        <a href="/admin/logout" class="btn-secondary">Logout</a>
    </div>
    
    <!-- Rest of admin page... -->
</div>
```

### **Step 6: Add Required Import (app.py)**
```python
from functools import wraps
```

---

## **Alternative: Environment Variables (More Secure)** 🔒

Instead of hardcoding credentials, use environment variables:

### **app.py**:
```python
import os

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'changeme')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
```

### **Set environment variables**:

**Windows (PowerShell)**:
```powershell
$env:ADMIN_USERNAME = "admin"
$env:ADMIN_PASSWORD = "your_secure_password"
$env:SECRET_KEY = "random_secret_key_here"
```

**Linux/Mac**:
```bash
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="your_secure_password"
export SECRET_KEY="random_secret_key_here"
```

**PythonAnywhere** (in Web tab → Environment variables):
```
ADMIN_USERNAME = admin
ADMIN_PASSWORD = your_secure_password
SECRET_KEY = random_secret_key_here
```

---

## **Session Security Best Practices**

### **1. Set Session Timeout**
```python
from datetime import timedelta

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.permanent = True  # Enable timeout
            session['admin_authenticated'] = True
            return redirect('/admin')
        # ...
```

### **2. Generate Secure Secret Key**
```python
import secrets
print(secrets.token_hex(32))  # Run this once to generate a key
```

### **3. Use HTTPS in Production**
```python
# For PythonAnywhere or production
app.config['SESSION_COOKIE_SECURE'] = True  # Only send cookie over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
```

---

## **Implementation Checklist**

- [ ] Create `templates/admin.html`
- [ ] Create `static/js/admin.js`
- [ ] Add admin routes to `app.py`
- [ ] Add API endpoints to `app.py`
- [ ] Add security (password or IP whitelist)
- [ ] Test all delete operations
- [ ] Test backup functionality
- [ ] Add CSS styling for admin page
- [ ] Document admin password/access method

---

## **Estimated Implementation Time**

- Backend API endpoints: 15 minutes
- Frontend HTML/JS: 15 minutes
- Security layer: 5 minutes
- Testing: 10 minutes

**Total: ~45 minutes**
