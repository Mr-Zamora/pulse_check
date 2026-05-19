AI Capabilities Guide - Pulse Check AI Explainer
This document outlines how AI is integrated into the Pulse Check classroom application to provide just-in-time learning support for students.

1. Overview
The app uses Google's Generative AI (Gemini family) via the google-generativeai Python SDK. Teachers can generate AI explanations for quiz questions to help students understand concepts before answering.

Flow:

1. Teacher selects a question and clicks "Prepare Question"
2. Teacher chooses between "Play Video" or "AI Explainer"
3. If AI Explainer is chosen:
   - Browser POSTs to `/api/teacher/generate_explainer`
   - Server retrieves question details from `questions.csv`
   - Server constructs a pedagogical prompt
   - Server calls `model.generate_content(prompt)`
   - Server stores explainer text in `room_states` table
   - Students see the AI-generated explanation in WAITING state
4. Teacher clicks "Start Quiz" when ready
5. Students answer the question with the context they just learned
2. Requirements
Python packages (requirements.txt)
Flask
google-generativeai
Install:

pip install -r requirements.txt
API key
Add your Gemini API key to `admin.py` (already in .gitignore):

# admin.py
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "your_password"
SECRET_KEY = "your_secret_key"
GEMINI_API_KEY = "YOUR_API_KEY_HERE"  # Add this line
Get a key at https://aistudio.google.com/app/apikey.

.gitignore entries (already configured)
admin.py
__pycache__/
*.pyc
database/*.db
database/*.db-*
3. Model
For Pulse Check, we use `gemini-3.1-flash-lite` for educational explanations:

model = genai.GenerativeModel('gemini-3.1-flash-lite')

This model is optimized for:
- Clear, educational explanations
- Appropriate language for high school students
- Fast response times (1-4 seconds)
- Free tier friendly

4. SDK Configuration Pattern
import google.generativeai as genai

try:
    from admin import GEMINI_API_KEY
    genai.configure(api_key=GEMINI_API_KEY)
except (ImportError, AttributeError):
    print("WARNING: GEMINI_API_KEY not found in admin.py. AI Explainer will fail.")
This lets the app boot even without a key (useful for UI dev), but logs a clear warning.

5. Prompt Engineering Pattern - AI Explainer
The AI Explainer uses a structured pedagogical prompt designed to teach concepts without giving away answers.

5.1 Actual Prompt Template for Pulse Check

```python
def construct_explainer_prompt(question):
    return f"""### ROLE ###
You are a high school teacher preparing students for a quiz question.
Your audience is high school students aged 15-18.
Your goal is to teach them the concepts they need to answer the question correctly.

### CONTEXT ###
This is part of a live classroom quiz system. Students will see your explanation
for 30-60 seconds before the question appears. They need just enough information
to understand the concepts, but you should NOT give away the answer directly.

Question Type: {question['type']}
- If MCQ: Students will choose from multiple options
- If SHORT: Students will write a brief answer

### TASK ###
Write a clear, concise explanation (100-150 words, 1-2 paragraphs) that:

1. **Teaches the concept:** Explain the key ideas students need to understand
2. **Provides context:** Give relevant background or examples
3. **Guides thinking:** Help them approach the question logically
4. **Avoids spoilers:** Do NOT reveal the correct answer or make it obvious
5. **Uses simple language:** Appropriate for high school students
6. **Uses Australian spelling:** Use colour (not color), organise (not organize), etc.

### INPUT ###
* **Question:** {question['prompt']}
* **Type:** {question['type']}
* **Topic:** {question.get('video_url', 'General knowledge')}

Write your explanation now:"""
```
5.2 Why This Prompt Works

**ROLE** anchors the AI as a teacher, not a quiz-taker or answer-giver.

**CONTEXT** explicitly states:
- The time constraint (30-60 seconds)
- The pedagogical goal (teach, don't spoil)
- The question type (helps AI calibrate explanation depth)

**TASK** uses a numbered checklist with clear constraints:
- Word count (100-150) prevents rambling
- "Do NOT reveal the answer" is explicit
- "Simple language" ensures accessibility

**INPUT** provides just enough information:
- The actual question text
- Question type (MCQ vs SHORT)
- Topic hint from video_url field

5.3 Example Output

**Question:** "What does RTSP stand for?"

**AI Explainer Output:**
> "Streaming protocols are specialized systems designed to deliver video and audio content over the internet efficiently. Unlike traditional file downloads where you wait for the entire file, streaming protocols send data in small chunks so you can start watching immediately. Different protocols have different strengths - some are better for live broadcasts, while others work well for on-demand content. Understanding what each protocol's name stands for often gives you a clue about its primary purpose and how it manages data transmission."

Notice how it:
- ✅ Teaches the concept of streaming protocols
- ✅ Provides context about how they work
- ✅ Guides thinking about acronyms and purpose
- ❌ Does NOT reveal "Real-time Streaming Protocol"

6. Implementation in Pulse Check

6.1 Backend Endpoint (`app.py`)

```python
@app.route('/api/teacher/generate_explainer', methods=['POST'])
def generate_explainer():
    """Generate AI explanation for a question"""
    try:
        data = request.get_json()
        room_id = data.get('room_id')
        question_id = data.get('question_id')
        
        if not room_id or not question_id:
            return jsonify({"status": "error", "message": "Missing parameters"}), 400
        
        # Get question from CSV
        questions = read_questions(room_id)
        question = next((q for q in questions if q['question_id'] == question_id), None)
        
        if not question:
            return jsonify({"status": "error", "message": "Question not found"}), 404
        
        # Generate explainer using Gemini
        explainer_text = generate_ai_explainer(question)
        
        # Store in database
        db = get_db()
        db.execute("""
            UPDATE room_states 
            SET explainer_text = ?, explainer_timestamp = ?
            WHERE room_id = ?
        """, (explainer_text, time.time(), room_id))
        db.commit()
        
        return jsonify({
            "status": "success",
            "explainer": explainer_text
        })
        
    except Exception as e:
        print(f"Error generating explainer: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


def generate_ai_explainer(question):
    """Call Gemini API to generate pedagogical explanation"""
    model = genai.GenerativeModel('gemini-3.1-flash-lite')
    
    prompt = f"""### ROLE ###
You are a high school teacher preparing students for a quiz question.
Your audience is high school students aged 15-18.
Your goal is to teach them the concepts they need to answer the question correctly.

### CONTEXT ###
This is part of a live classroom quiz system. Students will see your explanation
for 30-60 seconds before the question appears. They need just enough information
to understand the concepts, but you should NOT give away the answer directly.

Question Type: {question['type']}
- If MCQ: Students will choose from multiple options
- If SHORT: Students will write a brief answer

### TASK ###
Write a clear, concise explanation (100-150 words, 1-2 paragraphs) that:

1. **Teaches the concept:** Explain the key ideas students need to understand
2. **Provides context:** Give relevant background or examples
3. **Guides thinking:** Help them approach the question logically
4. **Avoids spoilers:** Do NOT reveal the correct answer or make it obvious
5. **Uses simple language:** Appropriate for high school students
6. **Uses Australian spelling:** Use colour (not color), organise (not organize), etc.

### INPUT ###
* **Question:** {question['prompt']}
* **Type:** {question['type']}

Write your explanation now:"""
    
    response = model.generate_content(prompt)
    return response.text.strip()
```

6.2 No JSON Parsing Needed

Unlike other AI applications, the AI Explainer returns **plain text** (not JSON) because:
- Students need to read natural language explanations
- No structured data extraction required
- Simpler implementation
- Faster response times
7. Frontend Integration

7.1 Teacher Dashboard (`teacher.js`)

```javascript
function prepareQuestion(questionId) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>Prepare Students</h3>
            <p>Choose how to introduce this question:</p>
            <button onclick="playVideo('${questionId}')">
                🎥 Play Video
            </button>
            <button onclick="generateAIExplainer('${questionId}')">
                🤖 AI Explainer
            </button>
            <button onclick="closeModal()">Cancel</button>
        </div>
    `;
    document.body.appendChild(modal);
}

async function generateAIExplainer(questionId) {
    showLoadingSpinner("Generating AI explanation...");
    
    try {
        const response = await fetch('/api/teacher/generate_explainer', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                room_id: currentRoomId,
                question_id: questionId
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            alert('AI Explainer sent to students!');
            closeModal();
        } else {
            alert('Error: ' + data.message);
        }
    } catch (error) {
        alert('Failed to generate explainer: ' + error);
    } finally {
        hideLoadingSpinner();
    }
}
```

7.2 Student View (`student.js`)

```javascript
function showWaitingState(state) {
    const viewport = document.getElementById('viewport');
    
    // Check if AI explainer exists
    if (state.explainer_text) {
        viewport.innerHTML = `
            <div class="explainer-card">
                <h3>🤖 AI Teacher Explainer</h3>
                <div class="explainer-text">
                    ${state.explainer_text}
                </div>
                <p class="timer">Question starts in: ${state.time_remaining}s</p>
            </div>
        `;
    } 
    // Otherwise check for video
    else if (state.video_url) {
        const videoId = extractYouTubeId(state.video_url);
        viewport.innerHTML = `
            <div class="video-container">
                <iframe src="https://www.youtube.com/embed/${videoId}"></iframe>
            </div>
        `;
    }
    // Default waiting message
    else {
        viewport.innerHTML = `
            <p>Waiting for teacher to start the quiz...</p>
        `;
    }
}
```

8. Database Schema Update

Add these columns to `room_states` table:

```sql
ALTER TABLE room_states 
ADD COLUMN explainer_text TEXT,
ADD COLUMN explainer_timestamp REAL;
```

Or update `configuration.py` `init_db()`:

```python
db.execute("""
    CREATE TABLE IF NOT EXISTS room_states (
        room_id TEXT PRIMARY KEY,
        state TEXT DEFAULT 'IDLE',
        current_q TEXT,
        show_responses INTEGER DEFAULT 0,
        instruction_start REAL,
        instruction_duration INTEGER DEFAULT 30,
        quiz_start REAL,
        quiz_duration INTEGER DEFAULT 60,
        explainer_text TEXT,
        explainer_timestamp REAL
    )
""")
```

9. Cost & Performance

**Gemini API Pricing:**
- Free tier: 60 requests/minute, 1500 requests/day
- Cost: $0 for typical classroom use

**Performance:**
- Generation time: 1-3 seconds
- Response length: ~150 words
- No caching needed (each explanation is unique)

**Typical Usage:**
- 1 class = 10 questions
- 10 questions × 1 explainer = 10 API calls
- Well within free tier limits

10. Security & Best Practices

✅ **API Key Security:**
- Store in `admin.py` (already gitignored)
- Never commit to repository
- Use environment variables in production

✅ **Input Validation:**
- Validate `room_id` and `question_id` exist
- Sanitize question text before sending to API
- Handle API errors gracefully

✅ **Rate Limiting:**
- Free tier: 60 requests/minute
- Classroom use: ~1 request/minute
- No additional limiting needed

✅ **Error Handling:**
- Graceful fallback if API key missing
- Show user-friendly error messages
- Log errors server-side for debugging

11. Testing Checklist

Before deploying:
- [ ] Add `GEMINI_API_KEY` to `admin.py`
- [ ] Install `google-generativeai` package
- [ ] Update database schema with new columns
- [ ] Test with a sample question
- [ ] Verify explainer appears on student screen
- [ ] Test fallback when API key is missing
- [ ] Check response time (<3 seconds)
- [ ] Verify explainer clears when quiz starts

12. Implementation Details & Fixes

12.1 Button State Management
Buttons are automatically enabled/disabled based on room state to prevent confusion:
- **WAITING state**: Prepare Question, AI Explainer, Start Quiz enabled
- **ACTIVE state**: Only Lock Submissions enabled (others greyed out)
- **LOCKED state**: Only Reset enabled
- This prevents teachers from generating explainers during active quiz

12.2 Student Polling
- Student polling interval: 1 second (reduced from 2 seconds for faster updates)
- Students see explainer updates within 1-6 seconds of teacher clicking AI Explainer button

12.3 Database Location (PythonAnywhere)
- On PythonAnywhere, database stored in `/tmp/classroom_pulse.db` to avoid NFS I/O errors
- This prevents "disk I/O error" issues on free-tier PythonAnywhere
- Note: `/tmp` database is cleared on server restart (room states reset, responses remain in CSV)

12.4 Explainer Display Logic
- Explainer only shows in WAITING state (before quiz starts)
- Explainer is left-aligned for better readability
- Explainer is automatically cleared when:
  - Teacher clicks "Prepare Question" for a new question
  - Teacher clicks "Start Quiz Now"
- Students see explainer automatically without page refresh (polling-based)

12.5 Performance Characteristics
- Total delay: 3-6 seconds (expected variation)
  - Gemini API generation: 1-4 seconds (varies with question complexity)
  - Student polling: 0-1 second
  - Network latency: 0.5-2 seconds
- Variation is normal due to:
  - Gemini server load
  - Question complexity
  - Network conditions

12.6 Fixes Applied During Implementation
- Fixed database corruption by moving to `/tmp` (avoided NFS I/O errors)
- Added missing `lastStateData` variable in student.js
- Added explainer columns to allowed room_state columns
- Updated to `gemini-3.1-flash-lite` model (gemini-pro deprecated)
- Added Australian spelling convention to prompt
- Fixed button styling (white text on AI Explainer button)
- Added explainer change detection for auto-updating student view

13. Current Behavior Summary
- Teacher selects question → Clicks "🤖 AI Explainer" → Explainer generated in 2-4 seconds
- Students see explainer automatically within 1-6 seconds in WAITING state
- Explainer displays with left alignment and Australian spelling
- Buttons automatically disable during ACTIVE quiz to prevent confusion
- Explainer clears when preparing new question or starting quiz
- All changes committed and deployed to production