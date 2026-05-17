# Implementation Plan: Micro-Chunking Classroom Feedback Application

## Overview

This plan breaks down the implementation into distinct phases, starting with **UI prototypes for approval** before backend development. Each phase has clear deliverables and dependencies.

---

## Phase 0: UI Prototype & Design Approval ⭐ **START HERE**

**Objective:** Create flat HTML files with inline CSS for visual approval before any backend work.

**Deliverables:**

### 0.1 Landing Page (`prototype_index.html`)
- Simple centered form with two inputs:
  - Student Name (text input)
  - Room ID (text input)
  - Submit button → "Join Room"
- Clean, minimal design
- Responsive layout (works on mobile/tablet/desktop)

### 0.2 Student Interface (`prototype_student.html`)
- Header banner showing:
  - Student name
  - Room ID
  - Connection status indicator (green dot)
- Main viewport with three state mockups:
  - **WAITING state:** "Eyes on Teacher" placeholder card
  - **ACTIVE state (MCQ):** Sample multiple choice question with 4 options
  - **ACTIVE state (SHORT):** Sample short answer question with text input
  - **LOCKED state:** "Time's Up - Awaiting Feedback" message
- All states visible on same page for review (separated by horizontal rules)

### 0.3 Teacher Dashboard (`prototype_teacher.html`)
- **Component A - Top Summary Ribbon:**
  - Current question display (left)
  - Countdown timer (center) - shows "01:23" format
  - Submission counter (right) - "14 / 18 Submitted"
  
- **Component B - Distribution View (Left Partition):**
  - MCQ bar chart mockup (4 options with percentage bars)
  - Short answer grouped responses mockup (3-4 sample answers with counts)
  
- **Component C - Student Roster Grid (Right Partition):**
  - 12-16 sample student cards showing different states:
    - Connected & correct (green)
    - Connected & incorrect (red)
    - Thinking/in-progress (orange)
    - Disconnected (gray dashed)
  - Anonymize checkbox at top
  
- **Component D - Question Control Panel (Bottom):**
  - Question library dropdown (with 3-4 sample questions)
  - Action buttons: Prepare Question, Start Quiz Now, Lock Submissions, Reset Room
  - Collapsible "Create New Question" form showing:
    - Type selector (MCQ/SHORT radio buttons)
    - MCQ form fields (prompt + 4 options + correct answer selector)
    - SHORT form fields (prompt + expected answer)

**Success Criteria:**
- All UI components visible and styled
- Color scheme matches SPEC.md (`#1E293B`, `#10B981`, `#EF4444`, `#F59E0B`, etc.)
- Typography is clean and readable
- Layout is responsive and scannable
- **USER APPROVAL REQUIRED** before proceeding to Phase 1

**Estimated Time:** 2-3 hours

---

## Phase 1: Project Structure & Backend Foundation

**Objective:** Set up the Flask application skeleton and data layer.

**Dependencies:** Phase 0 approved

**Deliverables:**

### 1.1 Directory Structure
```
classroom_pulse/
├── app.py
├── configuration.py
├── database/
│   ├── classroom_pulse.db   (auto-created on first run)
│   ├── questions.csv (with sample data)
│   └── responses.csv (empty, headers only)
├── static/
│   ├── css/
│   │   └── style.css (extracted from prototypes)
│   └── js/
│       ├── student.js (empty stub)
│       └── teacher.js (empty stub)
└── templates/
    ├── base.html
    ├── index.html
    ├── student.html
    └── teacher.html
```

### 1.2 Configuration Module (`configuration.py`)
- Threading locks:
  - `csv_lock = threading.Lock()` — protects CSV file writes
- SQLite database path constant (`DB_PATH`)
- SQLite `init_db()` function — creates `room_states` and `student_last_seen` tables if they don't exist, enables WAL mode
- Constants:
  - `POLL_INTERVAL = 2000` (ms)
  - `DISCONNECT_TIMEOUT = 30` (seconds)
  - `DEFAULT_QUESTION_TIME = 120` (seconds)

> **Note:** `room_states` and `student_last_seen` are no longer Python in-memory dicts. All room state reads and writes go through SQLite, making the app safe for multi-worker WSGI deployments (e.g. PythonAnywhere).

### 1.3 CSV Helper Functions (`app.py` or separate `data_layer.py`)
- `read_questions(room_id)` → Returns list of question dicts
- `read_responses(room_id, question_id)` → Returns list of response dicts
- `write_question(question_dict)` → Appends to questions.csv with lock
- `write_response(response_dict)` → Appends to responses.csv with lock
- `normalize_answer(text)` → Lowercase, strip whitespace

### 1.4 Sample Data
- Create `database/questions.csv` with 3-5 sample questions:
  - 2 MCQ questions (Python syntax examples)
  - 2 SHORT questions (code completion)
- Create `database/responses.csv` with headers only

**Success Criteria:**
- Flask app runs without errors
- CSV files can be read/written with thread safety
- Sample questions load correctly
- Directory structure matches SPEC.md

**Estimated Time:** 2-3 hours

---

## Phase 2: Core API Routes (Backend Only)

**Objective:** Implement all API endpoints without frontend integration.

**Dependencies:** Phase 1 complete

**Deliverables:**

### 2.1 Session & Authentication Routes
- `GET /` → Renders `index.html`
- `POST /join` → Validates input, sets Flask session, redirects to `/room/<room_id>`
- `GET /room/<room_id>` → Checks session, renders `student.html`
- `GET /teacher` → Renders `teacher.html`

### 2.2 Room State API
- `GET /api/room/status?room_id=XXXX`
  - Returns: `{status, room_state, current_question_id, time_remaining_seconds, question_data}`
  - Updates `student_last_seen` timestamp
  - Calculates time remaining from server-side start_time

### 2.3 Teacher Control API
- `POST /api/teacher/control`
  - Accepts: `{action: "prepare|start|lock|reset", q_id, room_id, instruction_time, quiz_time, auto_start}`
  - Actions:
    - `prepare`: Loads question, sets room to WAITING, starts instruction timer
    - `start`: Sets room to ACTIVE, records start_time, starts quiz timer
    - `lock`: Sets room to LOCKED
    - `reset`: Sets room to WAITING, clears current question
  - Returns: `{status, message, new_state}`

### 2.4 Question Management API
- `POST /api/teacher/add_question`
  - Accepts: `{room_id, type, prompt, options, correct_answer}`
  - Generates unique `question_id`
  - Writes to questions.csv
  - Returns: `{status, question_id}`

- `GET /api/teacher/questions?room_id=XXXX`
  - Returns list of all questions for room
  - Used to populate dropdown

### 2.5 Student Submission API
- `POST /api/submit`
  - Accepts: `{q_id, ans, room_id, student_name}`
  - Validates room state is ACTIVE
  - Evaluates correctness (normalized for SHORT)
  - Writes to responses.csv
  - Returns: `{status, is_correct, message}`

### 2.6 Teacher Analytics API
- `GET /api/teacher/responses?room_id=XXXX&question_id=YYYY`
  - Parses responses.csv
  - Aggregates statistics:
    - MCQ: Count per option, percentage correct
    - SHORT: Grouped normalized answers with counts
  - Includes student connection status
  - Returns: `{question_type, stats, student_states, total_submitted, total_students}`

**Testing:**
- Use Postman/curl to test all endpoints
- Verify CSV writes are thread-safe
- Confirm state transitions work correctly

**Success Criteria:**
- All API routes return correct JSON
- State management works across multiple rooms
- CSV data persists correctly
- No race conditions in concurrent writes

**Estimated Time:** 4-5 hours

---

## Phase 3: Student Frontend Integration

**Objective:** Connect student UI to backend with polling and form submission.

**Dependencies:** Phase 2 complete

**Deliverables:**

### 3.1 Convert Prototype to Jinja Template
- Extract CSS from `prototype_student.html` → `static/css/style.css`
- Convert to `templates/student.html` with Jinja variables:
  - `{{ student_name }}`
  - `{{ room_id }}`
- Create `templates/base.html` with common HTML structure

### 3.2 Student JavaScript (`static/js/student.js`)

**Polling Engine:**
```javascript
// Poll /api/room/status every 2 seconds
// Update UI based on room_state
// Handle state transitions: WAITING → ACTIVE → LOCKED
```

**State Handlers:**
- `showWaitingState()` → Display "Eyes on Teacher" card
- `showActiveState(questionData)` → Render question form (MCQ or SHORT)
- `showLockedState()` → Display "Time's Up" message
- `updateTimer(seconds)` → Display countdown

**Form Submission:**
- Capture form submit event
- POST to `/api/submit`
- Show success/error feedback
- Disable form after submission

**Connection Indicator:**
- Green dot when polling succeeds
- Yellow dot on network error
- Auto-retry on failure

### 3.3 Testing
- Test with multiple browser tabs (simulate multiple students)
- Verify state transitions work smoothly
- Confirm timer updates correctly
- Test both MCQ and SHORT question rendering

**Success Criteria:**
- Student sees real-time state changes
- Questions render correctly from backend data
- Form submissions save to CSV
- No page reloads required
- Works on mobile browsers

**Estimated Time:** 3-4 hours

---

## Phase 4: Teacher Frontend Integration

**Objective:** Connect teacher dashboard to backend with real-time updates.

**Dependencies:** Phase 3 complete

**Deliverables:**

### 4.1 Convert Prototype to Jinja Template
- Extract CSS from `prototype_teacher.html` → `static/css/style.css`
- Convert to `templates/teacher.html`
- Add room_id input/session handling

### 4.2 Teacher JavaScript (`static/js/teacher.js`)

**Initialization:**
- Load questions from `/api/teacher/questions`
- Populate dropdown
- Set up polling for `/api/teacher/responses`

**Control Panel Logic:**
- Question selection → Preview question details
- "Prepare Question" button → POST with action="prepare" (with timer config)
- "Start Quiz Now" button → POST to `/api/teacher/control` with action="start"
- "Lock Submissions" button → POST with action="lock"
- "Reset Room" button → POST with action="reset"
- Update UI state after each action

**Question Creator Form:**
- Type selector toggle (MCQ/SHORT) → Show/hide relevant fields
- Dynamic option addition (MCQ mode)
- Form validation
- Submit → POST to `/api/teacher/add_question`
- On success: Clear form, refresh dropdown, show toast

**Real-Time Analytics (Polling every 2 seconds):**
- Fetch `/api/teacher/responses`
- Update Component B (Distribution View):
  - MCQ: Render bar charts with percentages
  - SHORT: Group and display normalized answers
- Update Component C (Student Roster):
  - Create/update student cards
  - Apply state classes based on response data
  - Mark disconnected students (last_seen > 10s ago)
- Update Component A (Summary Ribbon):
  - Update timer countdown
  - Update submission counter

**Anonymization Toggle:**
- Checkbox listener
- Apply/remove CSS blur or text replacement

### 4.3 Testing
- Create questions via form
- Start questions and verify student screens update
- Submit responses as students
- Verify analytics update in real-time
- Test anonymization toggle
- Test with multiple concurrent rooms

**Success Criteria:**
- Teacher can create and launch questions
- Real-time analytics display correctly
- Student roster updates with connection status
- Bar charts render accurately
- Anonymization works
- No performance issues with 20+ students

**Estimated Time:** 5-6 hours

---

## Phase 5: Polish & Production Readiness

**Objective:** Refine UI/UX, add error handling, optimize performance.

**Dependencies:** Phase 4 complete

**Deliverables:**

### 5.1 Error Handling
- Network error recovery in polling
- Graceful degradation when server unavailable
- User-friendly error messages
- Form validation feedback

### 5.2 UI Polish
- Loading states and spinners
- Smooth transitions between states
- Toast notifications for actions
- Keyboard accessibility
- Mobile responsive refinements

### 5.3 Performance Optimization
- Debounce polling if needed
- Optimize CSV parsing for large datasets
- Add caching for question lists
- Minimize DOM manipulations

### 5.4 Documentation
- README.md with setup instructions
- Sample questions CSV template
- Deployment guide
- Teacher quick-start guide

### 5.5 Testing & QA
- Cross-browser testing (Chrome, Firefox, Safari, Edge)
- Mobile device testing (iOS, Android)
- Load testing with 30+ concurrent students
- Edge case testing (network failures, empty states, etc.)

**Success Criteria:**
- Application is stable and performant
- Error states are handled gracefully
- Documentation is complete
- Ready for classroom deployment

**Estimated Time:** 3-4 hours

---

## Total Estimated Time: 19-25 hours

## Next Steps

1. **Review this plan** - Confirm phased approach
2. **Start Phase 0** - Create UI prototypes for approval
3. **Iterate on design** - Refine based on feedback
4. **Proceed sequentially** - Complete each phase before moving to next

## Notes

- Each phase can be completed in 1-2 work sessions
- UI approval (Phase 0) is critical - all subsequent work depends on it
- Backend and frontend are separated to allow parallel work if needed
- CSV approach keeps deployment simple (no database setup required)
- Real-time updates via polling (no WebSocket complexity)

---

**Ready to start Phase 0 with UI prototypes?**
