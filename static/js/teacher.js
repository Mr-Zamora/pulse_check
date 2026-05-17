const POLL_INTERVAL = 2000;
let currentQuestions = [];
let currentRoomState = null;
let currentQuestionId = null;

// UI Elements
const qSelect = document.getElementById('q-select');
const instrTime = document.getElementById('instr-time');
const quizTime = document.getElementById('quiz-time');
const autoStart = document.getElementById('auto-start');
const rosterGrid = document.getElementById('roster-grid');
const distView = document.getElementById('distribution-view');

const ribbonTitle = document.getElementById('ribbon-q-title');
const ribbonTimerLabel = document.getElementById('ribbon-timer-label');
const ribbonTimer = document.getElementById('ribbon-timer');
const ribbonSub = document.getElementById('ribbon-submitted');
const ribbonTot = document.getElementById('ribbon-total');

// --- Utility: Toast Notifications ---
function showToast(message, type="info") {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    let icon = type === 'success' ? '✅' : (type === 'error' ? '❌' : 'ℹ️');
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease-out forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// --- Initialization ---
function init() {
    loadQuestions();
    updateTimeDisplays();
    pollServer();
}

function loadQuestions(selectId = null) {
    fetch(`/api/teacher/questions?room_id=${ROOM_ID}`)
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                currentQuestions = data.questions;
                qSelect.innerHTML = currentQuestions.map(q => 
                    `<option value="${q.question_id}">[${q.type}] ${q.prompt.substring(0, 50)}...</option>`
                ).join('');
                // Auto-select the newly added question if an ID was provided
                if (selectId) {
                    qSelect.value = selectId;
                }
            }
        });
}

function updateTimeDisplays() {
    const format = sec => {
        let m = Math.floor(sec / 60);
        let s = sec % 60;
        return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    };
    document.getElementById('instr-time-disp').textContent = format(instrTime.value);
    document.getElementById('quiz-time-disp').textContent = format(quizTime.value);
}

// --- Control API ---
function sendControl(action) {
    const payload = {
        action: action,
        room_id: ROOM_ID,
        q_id: qSelect.value,
        instruction_time: parseInt(instrTime.value),
        quiz_time: parseInt(quizTime.value),
        auto_start: autoStart.checked
    };
    
    fetch('/api/teacher/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            showToast(`Action '${action}' applied`, 'success');
            pollServer(); // force instant update
        } else {
            showToast("Error: " + data.message, "error");
        }
    })
    .catch(err => {
        console.error(err);
        showToast("Network error sending control.", "error");
    });
}

// --- Polling Engine ---
function pollServer() {
    fetch(`/api/room/status?room_id=${ROOM_ID}&role=teacher`)
        .then(r => r.json())
        .then(roomData => {
            if (roomData.status !== 'success') return;
            
            currentRoomState = roomData.room_state;
            currentQuestionId = roomData.current_question_id;
            
            updateRibbonState(roomData);
            fetchResponses();
            
            // Clear any connection error styling if it was present
            ribbonTitle.style.borderLeft = '';
        })
        .catch(err => {
            console.error("Polling error:", err);
            ribbonTitle.textContent = "⚠ Disconnected - Reconnecting...";
            ribbonTitle.style.color = "#EF4444";
            ribbonTitle.style.borderLeft = "4px solid #EF4444";
        })
        .finally(() => {
            setTimeout(pollServer, POLL_INTERVAL);
        });
}

function fetchResponses() {
    fetch(`/api/teacher/responses?room_id=${ROOM_ID}&question_id=${currentQuestionId}`)
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                renderRoster(data.student_states);
                renderDistribution(data);
                
                ribbonSub.textContent = data.total_submitted;
                ribbonTot.textContent = Object.keys(data.student_states).length;
            }
        });
}

// --- Rendering ---
function updateRibbonState(data) {
    if (!data.current_question_id) {
        ribbonTitle.textContent = "[No Question Active]";
        ribbonTimerLabel.textContent = "Timer";
        ribbonTimer.textContent = "--:--";
        ribbonTimer.style.color = "#64748B";
        return;
    }
    
    const q = currentQuestions.find(x => x.question_id === data.current_question_id);
    if (q) {
        ribbonTitle.textContent = `[${q.type}] ${q.prompt.substring(0, 30)}...`;
    }
    
    let sec = data.time_remaining_seconds;
    let m = Math.floor(sec / 60);
    let s = sec % 60;
    let timeStr = `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    
    if (data.room_state === "WAITING") {
        ribbonTimerLabel.textContent = "Instruction Time";
        ribbonTimer.textContent = timeStr;
        ribbonTimer.style.color = "#3B82F6"; // Blue
    } else if (data.room_state === "ACTIVE") {
        ribbonTimerLabel.textContent = "Quiz Time";
        ribbonTimer.textContent = timeStr;
        ribbonTimer.style.color = "#F59E0B"; // Amber
    } else if (data.room_state === "LOCKED") {
        ribbonTimerLabel.textContent = "Review Mode";
        ribbonTimer.textContent = "LOCKED";
        ribbonTimer.style.color = "#10B981"; // Green
    }
}

let isAnonymized = false;
function toggleAnonymize() {
    isAnonymized = document.getElementById('anonymize').checked;
    renderRoster(lastStudentStates); // trigger re-render
}

let lastStudentStates = {};
function renderRoster(states) {
    lastStudentStates = states;
    
    let html = '';
    let count = 0;
    
    for (const [name, info] of Object.entries(states)) {
        count++;
        let stateClass = '';
        let iconText = '';
        
        if (info.connection === 'disconnected') {
            stateClass = 'state-disconnected';
            iconText = '⚠ Disconnected';
        } else {
            if (info.state === 'thinking') {
                stateClass = 'state-thinking';
                iconText = '⏳ Thinking...';
            } else if (info.state === 'mcq_correct') {
                stateClass = 'state-mcq-correct';
                iconText = '✓ Correct';
            } else if (info.state === 'mcq_incorrect') {
                stateClass = 'state-mcq-incorrect';
                iconText = '✗ Incorrect';
            } else if (info.state === 'short_submit') {
                stateClass = 'state-short-submit';
                iconText = '📝 Submitted';
            }
        }
        
        let displayName = isAnonymized ? `Student ${count}` : name;
        let nameStyle = isAnonymized ? `style="filter: blur(4px);"` : "";
        
        html += `
            <div class="student-card ${stateClass}">
                <div class="name" ${nameStyle}>${displayName}</div>
                <div class="status">${iconText}</div>
            </div>
        `;
    }
    
    if (html === '') {
        html = '<p style="color: #94A3B8; text-align: center; grid-column: 1/-1; padding: 20px;">Waiting for students to join...</p>';
    }
    rosterGrid.innerHTML = html;
}

function renderDistribution(data) {
    if (!data.question_type) {
        distView.innerHTML = `<h3 style="color: #64748B; font-weight: normal; text-align: center; margin-top: 40px;">No Active Submissions</h3>`;
        return;
    }
    
    let html = `<h3>Response Distribution - ${data.question_type}</h3>`;
    
    if (data.question_type === 'MCQ') {
        const q = currentQuestions.find(x => x.question_id === currentQuestionId);
        if (!q) return;
        
        const options = q.options.split('|');
        const correctOpt = q.correct_answer.trim();
        const total = data.total_submitted;
        
        options.forEach(opt => {
            let optVal = opt.split(':')[0].trim();
            let count = data.stats[optVal] || 0;
            let pct = total > 0 ? Math.round((count / total) * 100) : 0;
            let isCorrect = (optVal === correctOpt);
            
            let fillClass = isCorrect ? 'correct' : 'incorrect';
            let labelSuffix = isCorrect ? ' (Correct)' : '';
            
            html += `
                <div class="bar-container">
                    <div class="bar-label">
                        <span>${opt}${labelSuffix}</span>
                        <span><strong>${pct}%</strong> (${count}/${total})</span>
                    </div>
                    <div class="bar-track">
                        <div class="bar-fill ${fillClass}" style="width: ${pct}%;"></div>
                    </div>
                </div>
            `;
        });
        
    } else if (data.question_type === 'SHORT') {
        const q = currentQuestions.find(x => x.question_id === currentQuestionId);
        let correctNorm = q ? q.correct_answer.toLowerCase().trim() : "";
        
        const entries = Object.entries(data.stats).sort((a,b) => b[1].count - a[1].count);
        
        if (entries.length === 0) {
             html += `<p style="color: #94A3B8; margin-top: 10px;">No submissions yet.</p>`;
        }
        
        entries.forEach(([norm, info]) => {
            let isCorrect = (norm === correctNorm);
            let borderStyle = isCorrect ? 'border-left-color: #10B981;' : 'border-left-color: #EF4444;';
            
            html += `
                <div class="short-answer-group" style="${borderStyle}">
                    <div><code>${info.raw}</code> <span class="count">[${info.count} Students]</span></div>
                </div>
            `;
        });
    }
    
    distView.innerHTML = html;
}

// --- Question Creator logic ---
function toggleCreator() {
    const form = document.getElementById('creator-form');
    form.style.display = form.style.display === 'none' ? 'grid' : 'none';
}

function toggleQType() {
    const type = document.querySelector('input[name="q-type"]:checked').value;
    if (type === 'MCQ') {
        document.getElementById('mcq-options-group').style.display = 'block';
        document.getElementById('short-answer-group').style.display = 'none';
    } else {
        document.getElementById('mcq-options-group').style.display = 'none';
        document.getElementById('short-answer-group').style.display = 'block';
    }
}

function addOption() {
    const container = document.getElementById('mcq-options-container');
    const count = container.children.length;
    if (count >= 6) return;
    
    const letters = ['A', 'B', 'C', 'D', 'E', 'F'];
    const letter = letters[count];
    
    const div = document.createElement('div');
    div.className = 'option-row';
    div.innerHTML = `
        <input type="text" class="opt-text" placeholder="Option ${letter}">
        <input type="radio" name="correct" value="${count}">
    `;
    container.appendChild(div);
}

function submitNewQuestion() {
    const type = document.querySelector('input[name="q-type"]:checked').value;
    const prompt = document.getElementById('new-q-prompt').value;
    
    if (!prompt.trim()) { showToast("Please enter a prompt.", "error"); return; }
    
    let payload = { room_id: ROOM_ID, type: type, prompt: prompt };
    
    if (type === 'MCQ') {
        const opts = document.querySelectorAll('.opt-text');
        const correctIdx = document.querySelector('input[name="correct"]:checked');
        
        let optionsList = [];
        let letters = ['A', 'B', 'C', 'D', 'E', 'F'];
        
        for (let i=0; i<opts.length; i++) {
            if (opts[i].value.trim()) {
                optionsList.push(`${letters[i]}: ${opts[i].value.trim()}`);
            }
        }
        
        if (optionsList.length < 2) { showToast("Please provide at least 2 options.", "error"); return; }
        
        payload.options = optionsList;
        payload.correct_answer = letters[correctIdx ? parseInt(correctIdx.value) : 0];
        
    } else {
        const shortAns = document.getElementById('new-q-short').value;
        if (!shortAns.trim()) { showToast("Please enter expected answer.", "error"); return; }
        payload.correct_answer = shortAns.trim();
    }
    
    fetch('/api/teacher/add_question', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            const newQId = data.question_id;
            document.getElementById('new-q-prompt').value = '';
            document.getElementById('new-q-short').value = '';
            toggleCreator();
            loadQuestions(newQId); // reload dropdown and auto-select the new question
            showToast("Question added! It's now selected in the dropdown.", "success");
        } else {
            showToast("Error: " + data.message, "error");
        }
    })
    .catch(err => {
        console.error(err);
        showToast("Network error creating question.", "error");
    });
}

init();
