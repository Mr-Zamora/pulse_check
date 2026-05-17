# Technical Specification: Micro-Chunking Classroom Feedback Web Application

## 1. Project Overview & Objectives

The purpose of this application is to facilitate a high-frequency, rapid-feedback pedagogical framework ("Micro-Chunking"). The system breaks instruction into strict 2-minute cycles: **2 minutes of direct instruction/reading → 1–2 minutes of execution/quiz → 1 minute of immediate feedback/pivoting**. 

The application must be extremely lightweight, low-latency, highly scannable for the instructor, and dead-simple for students. It bypasses heavy relational databases in favor of CSV files and memory states to ensure zero configuration overhead and instant data portability.

### Core Stack

- **Backend:** Python 3.x with Flask
- **Frontend:** Vanilla JavaScript (ES6+), HTML5, CSS3 (Material-inspired typography and semantic states)
- **Templating Engine:** Jinja2
- **State Persistence:** SQLite (via Python `sqlite3` stdlib) for room state and student presence — process-safe, survives server restarts, zero external dependencies
- **Data Persistence:** CSV files for question definitions and student response ledger — append-only, human-readable, portable

---

## 2. Directory & Architecture Blueprint

```text
classroom_pulse/
│
├── app.py                      # Core application controller, routes, state engine
├── configuration.py            # Global locks, app configurations
│
├── database/
│   ├── classroom_pulse.db      # SQLite: room_states + student_last_seen tables
│   ├── questions.csv           # Master list of quiz questions/prompts
│   └── responses.csv           # Append-only ledger of student inputs
│
├── static/
│   ├── css/
│   │   └── style.css           # Typography, grid layouts, and semantic state colors
│   └── js/
│       ├── student.js          # Polling engine, DOM switcher, form submission
│       └── teacher.js          # Real-time analytics compiler, UI update loops, controls
│
└── templates/
    ├── base.html               # Master HTML5 skeleton (links CSS, sets viewport)
    ├── index.html              # Landing portal (Room ID and Name entry)
    ├── student.html            # Dynamic student display layout
    └── teacher.html            # High-scannability command center
```

---

## 3. Data Storage & Schema Design

The application uses a split storage strategy:
- **SQLite** (`classroom_pulse.db`) stores volatile session state — room configuration, timer data, and student connection presence. This data must survive server restarts and be safe across WSGI worker processes.
- **CSV files** store durable records — the question bank and student response ledger. These are append-only, human-readable, and portable for export.

All CSV write operations use Python's `threading.Lock()` to prevent race conditions. SQLite handles its own write locking via WAL mode.

### 3.1 SQLite: `room_states` table

One row per active room. Upserted on every teacher control action.

| Column | Type | Description |
|--------|------|-------------|
| `room_id` | TEXT PRIMARY KEY | Unique room identifier |
| `state` | TEXT | Current state: `WAITING`, `ACTIVE`, or `LOCKED` |
| `current_q` | TEXT | Active question ID (nullable) |
| `instruction_start` | REAL | Unix timestamp when instruction timer started |
| `instruction_duration` | INTEGER | Seconds allocated for instruction phase |
| `quiz_start` | REAL | Unix timestamp when quiz timer started |
| `quiz_duration` | INTEGER | Seconds allocated for quiz phase |
| `auto_start` | INTEGER | Boolean flag (0/1) for auto-transition |

### 3.2 SQLite: `student_last_seen` table

One row per student per room. Updated on every poll. Used to determine connection status.

| Column | Type | Description |
|--------|------|-------------|
| `room_id` | TEXT | Room the student is in |
| `student_name` | TEXT | Student display name |
| `last_seen` | REAL | Unix timestamp of last poll |

Primary key is `(room_id, student_name)`.

### 3.3 `questions.csv`

Contains the structural definitions of the micro-quizzes. Pre-configured before class or appended on-the-fly.

| Column Name | Type | Description | Example Value |
| --- | --- | --- | --- |
| `question_id` | String (Unique) | Primary key identifier for the prompt | `q_syntax_01` |
| `room_id` | String | Links question to a specific active room | `1234` |
| `type` | String | Dictates UI rendering (`MCQ` or `SHORT`) | `MCQ` |
| `prompt` | String | The question or code snippet context | `Which line correctly invokes an inline loop?` |
| `options` | String (JSON Array) | Pipe-delimited string or serialized JSON array | `A: [x for x in y]|B: for x in y: append(x)` |
| `correct_answer` | String | The strict evaluation metric for grading | `A` |

### 3.2 `responses.csv`

An append-only historical log tracking every active node submission.

| Column Name | Type | Description | Example Value |
| --- | --- | --- | --- |
| `timestamp` | String (ISO) | Exact time of arrival at the server | `2026-05-17T10:15:32.102Z` |
| `room_id` | String | Scope identifier for the active room | `1234` |
| `student_name` | String | Sanitized student display name | `Nina M.` |
| `question_id` | String | Target question foreign identifier | `q_syntax_01` |
| `answer` | String | The exact raw payload submitted | `A` or `print(f"Val: {x}")` |
| `is_correct` | Boolean | Binary grade indicator determined on write | `True` |

---

## 4. System States & Synchronization Logic

The app manages a synchronization matrix across all active clients using **State Machine Synchronization via AJAX Long-Polling** (default robust baseline) to minimize setup complexity.

### 4.1 Room States

At any microsecond, a classroom session (`room_id`) exists in one of three global synchronization states:

1. **`WAITING`**: Students see a static "Eyes on Teacher / Listen to Slide" placeholder screen. Their input forms are locked/hidden.
2. **`ACTIVE`**: The quiz container unhides dynamically. The local Javascript timer initiates a 2-minute countdown. Submissions are active.
3. **`LOCKED`**: Submissions are rejected. The student screen displays a "Time's Up - Awaiting Feedback" view. The teacher reviews results.

### 4.2 State Sync Protocol (The Polling Sequence)

* Student browsers execute an asynchronous HTTP `GET` request to `/api/room/status?room_id=XXXX` every **2000 milliseconds**.
* The backend responds with a lightweight JSON payload:

```json
{
  "status": "success",
  "room_state": "ACTIVE",
  "current_question_id": "q_syntax_01",
  "time_remaining_seconds": 78
}
```

* If the browser detects a change from `WAITING` to `ACTIVE`, JavaScript strips the hidden attribute from the quiz component, inserts the options, and resets input structures without triggering a full page reload.

### 4.3 Implementation Clarifications

**Authentication & Room Management:**
- No authentication required - `/teacher` is publicly accessible for zero-config deployment
- Rooms auto-initialize when first accessed; no explicit creation endpoint needed
- Multiple concurrent rooms supported using `room_id` as partition key
- Global state structure in `configuration.py`:
```python
room_states = {
    "1234": {
        "state": "WAITING",
        "current_q": None,
        "instruction_start": None,
        "instruction_duration": 120,  # seconds
        "quiz_start": None,
        "quiz_duration": 120,  # seconds
        "auto_start": False
    },
    "5678": {
        "state": "ACTIVE",
        "current_q": "q1",
        "instruction_start": timestamp_1,
        "instruction_duration": 120,
        "quiz_start": timestamp_2,
        "quiz_duration": 120,
        "auto_start": True
    }
}
```

**Timer & State Transitions:**

All timers are **server-side** tracked using timestamps in `configuration.py`.

**Three-Phase Timing Model:**

1. **Instruction Phase (WAITING state):**
   - Optional visual countdown timer on teacher dashboard (default: 2 minutes)
   - Teacher can configure instruction duration per question (30s - 5min range)
   - Two start modes:
     - **Manual Start:** Teacher clicks "Start Quiz" button to transition to ACTIVE
     - **Auto-Start:** Timer expires → automatically transitions to ACTIVE state
   - Teacher selects mode via checkbox: "☐ Auto-start quiz when timer expires"
   - Students see: "Eyes on Teacher" placeholder (no timer visible to students)

2. **Execution Phase (ACTIVE state):**
   - Countdown timer (default: 2 minutes, configurable 30s - 5min)
   - Timer visible to both students and teacher
   - Teacher can manually lock early via "Lock Submissions" button
   - No auto-lock; teacher must manually transition to LOCKED

3. **Feedback Phase (LOCKED state):**
   - No timer (teacher-controlled duration)
   - Teacher reviews analytics and provides feedback
   - Teacher clicks "Reset Room" to return to WAITING for next question

**State Transition Actions via `/api/teacher/control`:**
- `{"action": "prepare", "q_id": "q1", "instruction_time": 120, "quiz_time": 120, "auto_start": true}` → Loads question, sets WAITING, starts instruction timer
- `{"action": "start", "room_id": "1234"}` → Manual transition from WAITING to ACTIVE (starts quiz timer)
- `{"action": "lock", "room_id": "1234"}` → Transition from ACTIVE to LOCKED
- `{"action": "reset", "room_id": "1234"}` → Returns to WAITING (clears current question)

**Timer Calculations:**
- `/api/room/status` returns `time_remaining_seconds` calculated from server timestamp
- Instruction timer only visible on teacher dashboard
- Quiz timer visible on both student and teacher interfaces

**Question Management:**
- Questions pre-loaded in `questions.csv` before class or added on-the-fly
- `/api/teacher/control` activates existing questions from CSV
- Optional `/api/teacher/add_question` endpoint for spontaneous question creation

**Short Answer Grading:**
- Uses **normalized matching** (lowercase, whitespace-stripped) for `SHORT` type questions
- Both student answer and `correct_answer` normalized before comparison
- Teacher dashboard displays all unique normalized answers grouped with counts

**Student Connection Tracking:**
- Server maintains in-memory dict: `{student_name: last_poll_timestamp}`
- Updated on every `/api/room/status` request
- Student marked as disconnected if no poll received in last 10 seconds (5× poll interval)
- Connection status included in `/api/teacher/responses` payload

---

## 5. API Routing Matrix

| Route | Method | Content-Type | Payload | Server Action / Logic |
| --- | --- | --- | --- | --- |
| `/` | `GET` | `text/html` | None | Renders `index.html`. Base registration terminal. |
| `/join` | `POST` | `form-data` | `name`, `room_id` | Validates session, writes values into encrypted cookie Flask `session`, redirects to `/room/<room_id>`. |
| `/room/<room_id>` | `GET` | `text/html` | None | Authenticates session context. Renders `student.html` structural baseline. |
| `/teacher` | `GET` | `text/html` | None | Base control viewport rendering `teacher.html`. No authentication required. |
| `/api/room/status` | `GET` | `application/json` | `room_id` (query param) | Fetches room state dict for `room_id`. Updates student last-seen timestamp. Returns state, current question, time remaining. |
| `/api/teacher/control` | `POST` | `application/json` | `{"action": "prepare\|start\|lock\|reset", "q_id": "q1", "room_id": "1234", "instruction_time": 120, "quiz_time": 120, "auto_start": false}` | Mutates room state. Actions: `prepare` (load question, start instruction timer), `start` (begin quiz manually), `lock` (freeze submissions), `reset` (return to waiting). |
| `/api/teacher/add_question` | `POST` | `application/json` | `{"room_id": "1234", "type": "MCQ", "prompt": "...", "options": [...], "correct_answer": "A"}` | Acquires lock, appends new question to `questions.csv`, returns `question_id`. |
| `/api/submit` | `POST` | `application/json` | `{"q_id": "q1", "ans": "text", "room_id": "1234", "student_name": "..."}` | Evaluates correctness (normalized for SHORT type), acquires `threading.Lock()`, appends to `responses.csv`, returns status. |
| `/api/teacher/responses` | `GET` | `application/json` | `room_id`, `question_id` (query params) | Parses `responses.csv` filtered by room and question. Aggregates statistics, groups normalized answers. Includes student connection status. |

---

## 6. Layout & UI/UX Component Specifications

The interface relies on clean, high-contrast, structured interfaces. No flashy graphics, complex animations, or gamified mechanics.

### 6.1 The Student Interface (`student.html`)

* **Container Structure:** Divided into a steady Header Banner (Displaying Student Name, Room ID, and Connection Pulse indicator) and a single, central multi-state viewport container (`#view-port`).
* **Dynamic CSS Clamping:**
  * State `WAITING`: Displays a large, centered card styled with a soft off-white background, subtle dark text: *"Slide Instruction Active. Watch the presentation and engage with the instructor."*
  * State `ACTIVE`: The card transitions instantly via structural DOM swapping. Renders the prompt clearly using a monospaced font segment for code blocks. Multiple choice arrays use substantial touch targets (`min-height: 48px`).

### 6.2 The Teacher Dashboard (`teacher.html`)

#### Component A: The Top Summary Ribbon (The "Pulse")

* **Visuals:** Full horizontal span across the absolute top edge of the screen. Dark, charcoal-tinted header fill (`#1E293B`) with crisp, bold white elements.
* **Metrics Display:**
  * **Left:** Large text displaying current pointer position (e.g., `[Q2: Loop Control structures]`).
  * **Center:** Large digital countdown clock using custom typography rules (`font-size: 24pt; font-weight: bold;`).
    * **During WAITING (instruction phase):** Shows instruction timer with label "Instruction Time" (color: `#3B82F6` blue) - *Teacher only, not visible to students*
    * **During ACTIVE (quiz phase):** Shows quiz timer with label "Quiz Time" (color: `#F59E0B` amber) - *Visible to both teacher and students*
    * **During LOCKED:** Shows "Review Mode" text (color: `#10B981` green)
  * **Right:** Horizontal stacked data displaying total headcount velocity: `Submitted: 14 / 18` (only shown during ACTIVE/LOCKED states).

#### Component B: The Distribution View (The Left Partition)

* Splits into real-time visual parsers depending on the active question's payload metadata.
* **MCQ Rendering Matrix:** Uses simple CSS-width horizontal block bars to convey percentages instantly:

```html
<div class="bar-container" style="margin: 10px 0;">
  <span class="label">Option A (Correct):</span>
  <div class="bar-track" style="background: #E2E8F0; width: 100%; border-radius: 4px;">
    <div class="bar-fill" style="background: #10B981; width: 65%; height: 20px; border-radius: 4px;"></div>
  </div>
  <span class="pct-val">65% (11/17)</span>
</div>
```

* **Short Answer Structural Stream:** A vertical layout container that performs string normalization (lowercasing, whitespace stripping). Exact string matches group into parent container modules showing a counter tag next to the block. If multiple students make an identical error, it instantly bubbles up visually:

> `for i in range(x)`  --- **[4 Students] ⚠️ Missing Trailing Colon**

#### Component C: The Student Roster Grid (The Right Partition)

A dense flex-wrap or CSS block-grid compilation of miniature student diagnostic block cards. Cards use semantic color indicators based on incoming state data matrices:

```css
/* Card Core Properties */
.student-card {
  border-radius: 6px;
  padding: 12px;
  margin: 6px;
  width: 140px;
  border: 2px solid transparent;
  box-sizing: border-box;
}

/* Operational States */
.state-disconnected { background-color: #F1F5F9; border-style: dashed; border-color: #CBD5E1; color: #94A3B8; }
.state-thinking      { background-color: #FFFFFF; border-color: #F59E0B; animation: pulse 2s infinite; }
.state-mcq-correct   { background-color: #ECFDF5; border-color: #10B981; color: #065F46; }
.state-mcq-incorrect { background-color: #FEF2F2; border-color: #EF4444; color: #991B1B; }
.state-short-submit  { background-color: #EFF6FF; border-color: #3B82F6; color: #1E40AF; }
```

* **Roster Privacy Toggle:** The top of Component C contains a checkbox interactive input (`Anonymize Screen`). When checked, a CSS pseudo-class rules set hides student names (`.student-card .name { filter: blur(4px); }`) or swaps the text string with placeholder tokens (`Student 1`, `Student 2`), allowing the teacher to securely output the entire dashboard to the main classroom projector screen without compromising individual identities.

#### Component D: Question Control Panel (Bottom/Side Panel)

Located below the Summary Ribbon or in a collapsible side panel, this component allows teachers to manage questions.

**Question Selection Mode:**
* **Question Library Dropdown:** A `<select>` element populated from `questions.csv` filtered by current `room_id`
  * Each option displays: `[question_id] - [prompt preview (first 50 chars)]`
  * Selecting a question loads its details into a preview pane

* **Timer Configuration (shown when question selected):**
  * **Instruction Time:** Number input or slider (30s - 5min, default: 2min)
    * Label: "Teacher Explanation Duration"
    * Shows selected time in MM:SS format
  * **Quiz Time:** Number input or slider (30s - 5min, default: 2min)
    * Label: "Student Answer Duration"
    * Shows selected time in MM:SS format
  * **Auto-Start Checkbox:** `☐ Auto-start quiz when instruction timer expires`
    * Checked: Quiz automatically begins when instruction timer hits 0:00
    * Unchecked: Teacher must manually click "Start Quiz" button

* **Action Buttons (context-aware based on room state):**
  * **When WAITING (no active question):**
    * `Prepare Question` → Sends `{"action": "prepare", "q_id": "...", "instruction_time": X, "quiz_time": Y, "auto_start": bool}` to `/api/teacher/control`
    * Loads question, starts instruction timer on teacher dashboard
  * **When WAITING (instruction phase active):**
    * `Start Quiz Now` → Sends `{"action": "start", "room_id": "..."}` (manual override)
    * Button disabled if auto-start is enabled and timer > 0
  * **When ACTIVE (quiz running):**
    * `Lock Submissions` → Sends `{"action": "lock", "room_id": "..."}`
  * **When LOCKED (reviewing):**
    * `Reset Room` → Sends `{"action": "reset", "room_id": "..."}`

**Quick Question Creator (Collapsible Form):**
* **Toggle Button:** "➕ Create New Question" expands/collapses the form
* **Form Fields:**
  1. **Question Type Radio Buttons:**
     * `○ Multiple Choice (MCQ)`
     * `○ Short Answer (SHORT)`
  2. **Prompt Textarea:** Large text input for question/code snippet (supports multiline)
  3. **Conditional Fields (shown based on type selection):**
     * **If MCQ selected:**
       * Dynamic option inputs: "Option A", "Option B", "Option C", "Option D" (text inputs)
       * "➕ Add Option" button (up to 6 options)
       * Radio buttons to mark correct answer: `○ A  ○ B  ○ C  ○ D`
     * **If SHORT selected:**
       * Single text input: "Expected Answer (will be normalized)"
       * Helper text: *"Answer matching is case-insensitive and ignores extra whitespace"*
  4. **Submit Button:** "Add Question to Library"
     * Sends POST to `/api/teacher/add_question`
     * On success: Clears form, adds question to dropdown, shows success toast

**Visual Design:**
* Clean, form-focused layout with clear labels
* Type selector at top triggers instant UI swap between MCQ/SHORT field sets
* Validation: Prompt required, at least 2 options for MCQ, correct answer must be selected
* Uses same color scheme as rest of dashboard (`#1E293B` headers, `#10B981` success states)

---

## 7. Implementation Roadmap

### Step 1: Base Environment & Engine Configuration

Assemble the basic framework folder configurations. Write `app.py` establishing standard setup protocols, instantiate global variables tracking current live-room vectors, and code the CSV thread-locking IO function logic.

### Step 2: Routing Setup

Construct full API capabilities. Code individual routes ensuring student details accurately set session configurations. Confirm that reading and querying operational states outputs pristine data frameworks.

### Step 3: Frontend Layout Mechanics

Write Jinja code blocks within `base.html`, `index.html`, and structural sub-templates. Apply CSS grids ensuring elements align properly without using problematic display frameworks that degrade unpredictably across layout configurations.

### Step 4: Javascript Synchronization Engine

Construct client-side polling processes. Establish error handling routines so that sudden network issues cleanly trigger soft yellow visual warnings inside the application dashboard interfaces instead of halting client processes.

### Step 5: Analytical Dashboard Assembly

Write custom algorithms inside `teacher.js` processing inbound data matrices. Program individual rendering components ensuring text data properly converts into structural charts and semantic dashboard indicators during execution.