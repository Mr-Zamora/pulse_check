# Interactive Demo Specification: Pulse Check Teacher/Student Dual View

## Overview

**Purpose:** Create a standalone HTML demo file that simulates both teacher and student experiences without touching the database.

**File Location:** `ui_test/teacher_demo.html`

**Key Feature:** Toggle between Teacher View and Student View to demonstrate full application workflow.

---

## 1. View Toggle System

### Top-Right Corner Toggle

```html
<div class="view-toggle">
    <button class="toggle-btn active" onclick="switchView('teacher')">
        👨‍🏫 Teacher View
    </button>
    <button class="toggle-btn" onclick="switchView('student')">
        👨‍🎓 Student View
    </button>
</div>
```

### CSS for Toggle

```css
.view-toggle {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 1000;
    background: white;
    padding: 8px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.toggle-btn {
    padding: 10px 20px;
    border: 2px solid #CBD5E1;
    background: white;
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
    border-radius: 6px;
    transition: all 0.3s;
}

.toggle-btn.active {
    background: #3B82F6;
    color: white;
    border-color: #3B82F6;
}

.toggle-btn:hover:not(.active) {
    background: #F1F5F9;
}
```

---

## 2. Mock Data Structure

### Simulated Room State

```javascript
const mockRoomState = {
    state: 'LOCKED',  // WAITING, ACTIVE, LOCKED
    current_q: 'q_auto_05',
    show_responses: true,
    instruction_time: 120,
    quiz_time: 120,
    time_remaining: 0
};
```

### Simulated Questions (from questions.csv)

```javascript
const mockQuestions = [
    {
        question_id: 'q_auto_05',
        type: 'MCQ',
        prompt: 'Question 5: What is the most effective approach to ensuring that automation benefits society as a whole, rather than just a select few?',
        options: 'A: Letting market forces determine the distribution of automation benefits|B: Relying on voluntary corporate responsibility to address social impacts|C: Implementing policies that promote equitable access to education, retraining, and social safety nets|D: Restricting automation to prevent job displacement',
        correct_answer: 'C',
        video_url: 'https://youtu.be/v6fNh1AxZ-M'
    },
    {
        question_id: 'q_auto_06',
        type: 'MCQ',
        prompt: 'Question 6: A real estate company wants to predict house prices. Which type of machine learning should they use?',
        options: 'A: Classification|B: Clustering|C: Regression|D: Reinforcement Learning',
        correct_answer: 'C',
        video_url: 'https://youtu.be/LDdrLWiJJxc'
    },
    {
        question_id: 'q_auto_11',
        type: 'MCQ',
        prompt: 'Question 11: Which of the following is an example of unsupervised learning?',
        options: 'A: Predicting stock prices|B: Grouping customers by purchasing behavior|C: Classifying emails as spam or not spam|D: Teaching a robot to walk',
        correct_answer: 'B',
        video_url: 'https://youtu.be/GyeQd_iOikY'
    }
];
```

### Simulated Students (20+)

```javascript
const mockStudents = [
    { name: 'Alice Chen', answer: 'C', is_correct: true, connected: true },
    { name: 'Bob Martinez', answer: 'A', is_correct: false, connected: true },
    { name: 'Carol Wang', answer: 'C', is_correct: true, connected: true },
    { name: 'David Kim', answer: 'B', is_correct: false, connected: true },
    { name: 'Emma Johnson', answer: 'C', is_correct: true, connected: false },
    { name: 'Frank Lee', answer: 'C', is_correct: true, connected: true },
    { name: 'Grace Patel', answer: 'A', is_correct: false, connected: true },
    { name: 'Henry Zhang', answer: 'C', is_correct: true, connected: true },
    { name: 'Iris Rodriguez', answer: 'D', is_correct: false, connected: true },
    { name: 'Jack Wilson', answer: 'C', is_correct: true, connected: true },
    { name: 'Kate Nguyen', answer: 'C', is_correct: true, connected: true },
    { name: 'Liam Brown', answer: 'B', is_correct: false, connected: true },
    { name: 'Maya Singh', answer: 'C', is_correct: true, connected: true },
    { name: 'Noah Davis', answer: 'C', is_correct: true, connected: true },
    { name: 'Olivia Taylor', answer: 'A', is_correct: false, connected: true },
    { name: 'Peter Anderson', answer: 'C', is_correct: true, connected: true },
    { name: 'Quinn Murphy', answer: 'C', is_correct: true, connected: true },
    { name: 'Rachel Cohen', answer: 'D', is_correct: false, connected: true },
    { name: 'Sam Thompson', answer: 'C', is_correct: true, connected: true },
    { name: 'Tara Williams', answer: 'C', is_correct: true, connected: true },
    { name: 'Uma Sharma', answer: 'B', is_correct: false, connected: true },
    { name: 'Victor Garcia', answer: 'C', is_correct: true, connected: true },
    { name: 'Wendy Liu', answer: 'A', is_correct: false, connected: true },
    { name: 'Xavier Jones', answer: 'C', is_correct: true, connected: false }
];
```

**Response Distribution for Q5:**
- **Option A:** 4 students (17%) ❌
- **Option B:** 3 students (13%) ❌
- **Option C:** 15 students (63%) ✓ Correct
- **Option D:** 2 students (8%) ❌

---

## 3. Teacher View Components

### Visible Elements

✅ **Top Summary Ribbon** (full width)
- Current question display (left)
- Timer display (center) - shows "02:00" or countdown
- Submission counter (right) - "24 / 24 Submitted"
- All-submitted indicator (green highlight when all submitted)

✅ **Control Panel** (left side)
- Question dropdown (populated from mockQuestions)
- "Prepare Question" button
- "Start Quiz Now" button
- "Lock Submissions" button
- "Show/Hide Responses" toggle
- Timer inputs (instruction time, quiz time)

✅ **Distribution View** (center)
- Full question display box with question text
- Response bar charts (MCQ) showing percentages
- Correct answer marked with ✓

✅ **Student Roster Grid** (right side)
- 24 student cards
- Color-coded by state:
  - Green border: Correct answer
  - Red border: Incorrect answer
  - Gray dashed: Disconnected
- Each card shows: Student name + answer
- "×" button to remove student (demo only)

✅ **Demo Controls** (bottom-right)
- Add Random Student
- Remove Random Student
- Simulate Submission
- Force State buttons
- Reset Demo

### Hidden Elements

❌ Student submission form
❌ Student waiting screen

---

## 4. Student View Components

### Visible Elements

✅ **Student Header Banner**
- Student name: "Demo Student"
- Room ID: "DEMO"
- Connection indicator (green dot)

✅ **Main Viewport** (state-dependent)

**WAITING State:**
- **With video URL:** Embedded YouTube video player (16:9 aspect ratio, auto-play enabled)
  - Uses actual YouTube URL from question data
  - Example: `https://youtu.be/v6fNh1AxZ-M` for Q5
  - Message below video: "The question will appear when the teacher starts the quiz"
- **Without video URL:** "👀 Eyes on Teacher" card

**ACTIVE State:**
- Question prompt
- MCQ options (radio buttons) with labels A, B, C, D
- Submit Answer button
- Timer countdown (if applicable)

**LOCKED State:**
- "⏱️ Time's Up - Awaiting Feedback" message
- Response distribution (if show_responses enabled)
  - Shows same bar chart as teacher view
  - Student can see what everyone answered

### Hidden Elements

❌ Teacher controls
❌ Student roster
❌ Question selection dropdown
❌ Demo controls

### Interactive Features (Student View)

```javascript
// Simulated student can pick an answer
let demoStudentAnswer = null;

function selectStudentAnswer(option) {
    demoStudentAnswer = option;
    // Highlight selected option
    document.querySelectorAll('.mcq-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    event.target.closest('.mcq-option').classList.add('selected');
}

function submitStudentAnswer() {
    if (!demoStudentAnswer) {
        alert('Please select an answer');
        return;
    }
    
    // Add demo student to teacher roster with selected answer
    const currentQ = mockQuestions.find(q => q.question_id === mockRoomState.current_q);
    const isCorrect = demoStudentAnswer === currentQ.correct_answer;
    
    mockStudents.push({
        name: 'Demo Student',
        answer: demoStudentAnswer,
        is_correct: isCorrect,
        connected: true
    });
    
    // Show success message
    alert(`Answer "${demoStudentAnswer}" submitted!`);
    
    // Update teacher view if visible
    if (currentView === 'teacher') {
        updateTeacherUI();
    }
    
    // Disable form for MCQ
    document.getElementById('student-submit-btn').disabled = true;
    document.getElementById('student-submit-btn').textContent = '✅ Answer Submitted';
}
```

**Key Behavior:** When demo student picks option "A" in student view, it appears in teacher roster as a red card (incorrect) with "Demo Student - A" label.

---

## 5. View Switching Logic

```javascript
let currentView = 'teacher'; // or 'student'
let studentState = 'WAITING'; // WAITING, ACTIVE, LOCKED

function switchView(view) {
    currentView = view;
    
    // Update toggle buttons
    document.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    if (view === 'teacher') {
        showTeacherView();
    } else {
        showStudentView();
    }
}

function showTeacherView() {
    // Show teacher components
    document.getElementById('teacher-dashboard').style.display = 'block';
    document.getElementById('student-viewport').style.display = 'none';
    
    // Show demo controls
    document.querySelector('.demo-controls').style.display = 'block';
    
    // Update view label
    document.getElementById('view-label').textContent = 'Teacher Dashboard';
}

function showStudentView() {
    // Hide teacher components
    document.getElementById('teacher-dashboard').style.display = 'none';
    document.getElementById('student-viewport').style.display = 'block';
    
    // Hide demo controls
    document.querySelector('.demo-controls').style.display = 'none';
    
    // Update view label
    document.getElementById('view-label').textContent = 'Student Experience';
    
    // Render student state
    renderStudentState(studentState);
}
```

---

## 6. Student View State Rendering

### WAITING State (with YouTube Video)

```javascript
function renderStudentState(state) {
    const viewport = document.getElementById('student-content');
    const currentQ = mockQuestions.find(q => q.question_id === mockRoomState.current_q);
    
    if (state === 'WAITING') {
        if (currentQ && currentQ.video_url) {
            // Extract YouTube video ID
            const videoId = extractYouTubeId(currentQ.video_url);
            
            viewport.innerHTML = `
                <div class="state-card">
                    <h3 style="margin-bottom: 20px; color: #64748B;">State: WAITING</h3>
                    <div class="video-container" style="position: relative; padding-bottom: 56.25%; height: 0; margin-bottom: 20px;">
                        <iframe 
                            style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border-radius: 8px;"
                            src="https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0" 
                            frameborder="0" 
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                            allowfullscreen>
                        </iframe>
                    </div>
                    <p style="text-align: center; color: #64748B; font-size: 16px;">
                        The question will appear when the teacher starts the quiz
                    </p>
                </div>
            `;
        } else {
            viewport.innerHTML = `
                <div class="state-card" style="text-align: center; padding: 60px 40px;">
                    <h2 style="font-size: 48px; margin-bottom: 20px;">👀</h2>
                    <h3 style="color: #1E293B; margin-bottom: 16px;">Eyes on Teacher</h3>
                    <p style="color: #64748B; font-size: 16px;">
                        Listen to the presentation and engage with the instructor.
                    </p>
                </div>
            `;
        }
    } else if (state === 'ACTIVE') {
        renderActiveState(viewport, currentQ);
    } else if (state === 'LOCKED') {
        renderLockedState(viewport);
    }
}

function extractYouTubeId(url) {
    // Handle youtu.be/VIDEO_ID
    if (url.includes('youtu.be/')) {
        return url.split('youtu.be/')[1].split('?')[0];
    }
    // Handle youtube.com/watch?v=VIDEO_ID
    if (url.includes('watch?v=')) {
        return url.split('watch?v=')[1].split('&')[0];
    }
    // Handle youtube.com/embed/VIDEO_ID
    if (url.includes('embed/')) {
        return url.split('embed/')[1].split('?')[0];
    }
    return '';
}
```

### ACTIVE State (MCQ Form)

```javascript
function renderActiveState(viewport, question) {
    if (question.type === 'MCQ') {
        const options = question.options.split('|');
        let optionsHTML = options.map(opt => {
            const optVal = opt.split(':')[0].trim();
            return `
                <label class="mcq-option" onclick="selectStudentAnswer('${optVal}')">
                    <input type="radio" name="demo-answer" value="${optVal}">
                    <span>${opt}</span>
                </label>
            `;
        }).join('');
        
        viewport.innerHTML = `
            <div class="question-container">
                <h3 style="margin-bottom: 20px; color: #64748B;">State: ACTIVE</h3>
                <div class="question-prompt" style="background: #F8FAFC; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <p style="font-size: 16px; line-height: 1.6; color: #1E293B;">${question.prompt}</p>
                </div>
                <div class="mcq-options">
                    ${optionsHTML}
                </div>
                <button id="student-submit-btn" class="btn-primary" onclick="submitStudentAnswer()" style="margin-top: 20px; width: 100%;">
                    Submit Answer
                </button>
            </div>
        `;
    }
}
```

### LOCKED State (with Response Distribution)

```javascript
function renderLockedState(viewport) {
    let html = `
        <div class="state-card" style="text-align: center; padding: 40px;">
            <h2 style="font-size: 36px; margin-bottom: 16px;">⏱️</h2>
            <h3 style="color: #1E293B; margin-bottom: 12px;">Time's Up</h3>
            <p style="color: #64748B; font-size: 16px;">
                Awaiting feedback from teacher...
            </p>
        </div>
    `;
    
    // Show responses if enabled
    if (mockRoomState.show_responses) {
        html += `
            <div style="margin-top: 30px; padding: 20px; background: #F8FAFC; border-radius: 8px;">
                <h3 style="margin-bottom: 20px; color: #1E293B;">Response Distribution</h3>
                ${renderStudentDistribution()}
            </div>
        `;
    }
    
    viewport.innerHTML = html;
}

function renderStudentDistribution() {
    const currentQ = mockQuestions.find(q => q.question_id === mockRoomState.current_q);
    const stats = calculateDistribution();
    const total = mockStudents.length;
    
    let html = '';
    const options = currentQ.options.split('|');
    
    options.forEach(opt => {
        const optVal = opt.split(':')[0].trim();
        const count = stats[optVal] || 0;
        const pct = total > 0 ? Math.round((count / total) * 100) : 0;
        const isCorrect = optVal === currentQ.correct_answer;
        const fillClass = isCorrect ? 'correct' : 'incorrect';
        const labelSuffix = isCorrect ? ' ✓' : '';
        
        html += `
            <div class="bar-container" style="margin: 10px 0;">
                <div class="bar-label" style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span>${opt}${labelSuffix}</span>
                    <span><strong>${pct}%</strong> (${count}/${total})</span>
                </div>
                <div class="bar-track" style="background: #E2E8F0; width: 100%; border-radius: 4px; height: 20px;">
                    <div class="bar-fill ${fillClass}" style="width: ${pct}%; height: 100%; border-radius: 4px; background: ${isCorrect ? '#10B981' : '#EF4444'};"></div>
                </div>
            </div>
        `;
    });
    
    return html;
}
```

---

## 7. Synchronized State Changes

### Prepare Question

```javascript
function prepareQuestion(questionId) {
    // Update room state
    mockRoomState.state = 'WAITING';
    mockRoomState.current_q = questionId;
    mockRoomState.show_responses = false; // Auto-disable
    
    // Clear student responses
    mockStudents.length = 0;
    generateRandomStudents(0); // Start with 0 students
    
    // Update teacher view
    updateTeacherUI();
    
    // Update student state
    studentState = 'WAITING';
    if (currentView === 'student') {
        renderStudentState('WAITING');
    }
    
    console.log(`Prepared question: ${questionId}`);
}
```

### Start Quiz

```javascript
function startQuiz() {
    // Update room state
    mockRoomState.state = 'ACTIVE';
    mockRoomState.time_remaining = mockRoomState.quiz_time;
    
    // Update teacher view
    updateTeacherUI();
    
    // Update student state
    studentState = 'ACTIVE';
    if (currentView === 'student') {
        renderStudentState('ACTIVE');
    }
    
    // Start countdown timer
    startCountdown();
    
    console.log('Quiz started');
}
```

### Lock Submissions

```javascript
function lockSubmissions() {
    // Update room state
    mockRoomState.state = 'LOCKED';
    
    // Update teacher view
    updateTeacherUI();
    
    // Update student state
    studentState = 'LOCKED';
    if (currentView === 'student') {
        renderStudentState('LOCKED');
    }
    
    console.log('Submissions locked');
}
```

---

## 8. Demo Controls

```html
<div class="demo-controls" style="position: fixed; bottom: 20px; right: 20px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); max-width: 300px;">
    <h4 style="margin-bottom: 16px; color: #1E293B;">Demo Controls</h4>
    
    <!-- Student Management -->
    <div style="margin-bottom: 16px;">
        <button onclick="addRandomStudent()" style="width: 100%; margin-bottom: 8px;">
            ➕ Add Random Student
        </button>
        <button onclick="removeRandomStudent()" style="width: 100%; margin-bottom: 8px;">
            ➖ Remove Random Student
        </button>
        <button onclick="simulateSubmission()" style="width: 100%;">
            ⚡ Simulate Submission
        </button>
    </div>
    
    <!-- State Controls -->
    <div style="margin-bottom: 16px; padding-top: 16px; border-top: 1px solid #E2E8F0;">
        <p style="font-size: 12px; color: #64748B; margin-bottom: 8px;">Force State:</p>
        <button onclick="forceState('WAITING')" style="width: 100%; margin-bottom: 4px; font-size: 12px;">
            Set WAITING
        </button>
        <button onclick="forceState('ACTIVE')" style="width: 100%; margin-bottom: 4px; font-size: 12px;">
            Set ACTIVE
        </button>
        <button onclick="forceState('LOCKED')" style="width: 100%; font-size: 12px;">
            Set LOCKED
        </button>
    </div>
    
    <!-- Reset -->
    <button onclick="resetDemo()" style="width: 100%; background: #EF4444; color: white;">
        🔄 Reset Demo
    </button>
</div>
```

### Demo Control Functions

```javascript
function addRandomStudent() {
    const names = ['Zoe Parker', 'Alex Turner', 'Jordan Smith', 'Casey Lee', 'Morgan Davis'];
    const options = ['A', 'B', 'C', 'D'];
    const currentQ = mockQuestions.find(q => q.question_id === mockRoomState.current_q);
    
    const randomName = names[Math.floor(Math.random() * names.length)] + ' ' + Math.floor(Math.random() * 100);
    const randomAnswer = options[Math.floor(Math.random() * options.length)];
    const isCorrect = randomAnswer === currentQ.correct_answer;
    
    mockStudents.push({
        name: randomName,
        answer: randomAnswer,
        is_correct: isCorrect,
        connected: true
    });
    
    updateTeacherUI();
}

function removeRandomStudent() {
    if (mockStudents.length > 0) {
        const randomIndex = Math.floor(Math.random() * mockStudents.length);
        mockStudents.splice(randomIndex, 1);
        updateTeacherUI();
    }
}

function simulateSubmission() {
    // Simulate all students submitting
    generateRandomStudents(24);
    updateTeacherUI();
}

function forceState(state) {
    mockRoomState.state = state;
    studentState = state;
    updateTeacherUI();
    if (currentView === 'student') {
        renderStudentState(state);
    }
}

function resetDemo() {
    mockRoomState.state = 'WAITING';
    mockRoomState.current_q = 'q_auto_05';
    mockRoomState.show_responses = false;
    mockStudents.length = 0;
    studentState = 'WAITING';
    demoStudentAnswer = null;
    
    updateTeacherUI();
    if (currentView === 'student') {
        renderStudentState('WAITING');
    }
}
```

---

## 9. File Structure

```
ui_test/
└── teacher_demo.html  (~1000 lines)
    ├── <!DOCTYPE html>
    ├── <head>
    │   ├── <title>Pulse Check - Interactive Demo</title>
    │   └── <style>
    │       ├── /* Copy from static/css/style.css */
    │       ├── /* Teacher dashboard styles */
    │       ├── /* Student viewport styles */
    │       ├── /* Toggle button styles */
    │       ├── /* State-specific styles */
    │       └── /* Demo controls styles */
    │   </style>
    ├── <body>
    │   ├── <!-- View Toggle -->
    │   ├── <!-- Teacher Dashboard -->
    │   │   ├── <!-- Summary Ribbon -->
    │   │   ├── <!-- Control Panel -->
    │   │   ├── <!-- Distribution View -->
    │   │   └── <!-- Student Roster -->
    │   ├── <!-- Student Viewport -->
    │   │   ├── <!-- Student Header -->
    │   │   └── <!-- State-dependent content -->
    │   └── <!-- Demo Controls -->
    └── <script>
        ├── /* Mock data */
        ├── /* View switching */
        ├── /* State management */
        ├── /* Teacher controls */
        ├── /* Student interactions */
        ├── /* YouTube video handling */
        └── /* Demo utilities */
    </script>
```

---

## 10. Key Implementation Notes

### YouTube Video Integration

- **Extract video ID** from multiple URL formats (youtu.be, youtube.com/watch, youtube.com/embed)
- **Auto-play enabled** in WAITING state
- **16:9 aspect ratio** maintained with responsive container
- **Video stops** when transitioning to ACTIVE state (iframe removed from DOM)

### Student Answer Synchronization

- When demo student selects answer "A" in student view:
  1. Answer stored in `demoStudentAnswer` variable
  2. On submit, new student added to `mockStudents` array
  3. Student card appears in teacher roster with:
     - Name: "Demo Student"
     - Answer: "A"
     - Border color: Red (if incorrect) or Green (if correct)
  4. Response distribution updates to include demo student's answer
  5. Submission counter increments

### State Synchronization

- All teacher actions (Prepare, Start, Lock) update both:
  - `mockRoomState` (teacher state)
  - `studentState` (student state)
- View automatically re-renders when switching between teacher/student
- Demo controls only visible in teacher view

### No Database Interaction

- ✅ All data in JavaScript variables
- ✅ No fetch() calls
- ✅ No backend dependencies
- ✅ Fully self-contained HTML file
- ✅ Can be opened directly in browser (file://)

---

## 11. Estimated Metrics

**File Size:** ~1000-1200 lines
**Estimated Development Time:** 90-120 minutes
**Browser Compatibility:** Chrome, Firefox, Safari, Edge (modern browsers)
**Dependencies:** None (standalone HTML file)

---

## 12. Usage Instructions

1. Open `ui_test/teacher_demo.html` in web browser
2. Default view: Teacher Dashboard
3. Click "👨‍🎓 Student View" to see student experience
4. Use demo controls to:
   - Add/remove students
   - Change questions
   - Simulate state transitions
5. Switch between views to see synchronized updates
6. In student view, select an answer and submit to see it appear in teacher roster

---

**This demo is fully simulated and does not affect the production database.**
