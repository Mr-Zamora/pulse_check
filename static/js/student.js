const POLL_INTERVAL = 1000;
let currentState = null;
let currentQuestionId = null;
let hasSubmitted = false;
let timeRemaining = 0;
let showResponses = false;
let responseData = null;

const viewport = document.getElementById('view-port');
const connDot = document.getElementById('conn-dot');
const connText = document.getElementById('conn-text');

// --- Polling Engine ---
function pollServer() {
    fetch(`/api/room/status?room_id=${ROOM_ID}&student_name=${encodeURIComponent(STUDENT_NAME)}`)
        .then(response => {
            if (!response.ok) throw new Error("Network response was not ok");
            return response.json();
        })
        .then(data => {
            setConnectionStatus(true);
            handleStateUpdate(data);
        })
        .catch(error => {
            console.error("Polling error:", error);
            setConnectionStatus(false);
        })
        .finally(() => {
            setTimeout(pollServer, POLL_INTERVAL);
        });
}

function setConnectionStatus(isConnected) {
    if (isConnected) {
        connDot.style.background = '#10B981'; // Green
        connDot.style.animation = 'pulse 2s infinite';
        connText.textContent = 'Connected';
    } else {
        connDot.style.background = '#F59E0B'; // Yellow warning
        connDot.style.animation = 'none';
        connText.textContent = 'Reconnecting...';
    }
}

let hasQuestionData = false;

function handleStateUpdate(data) {
    if (data.status !== "success") return;
    
    // Update local timer state from server truth
    timeRemaining = data.time_remaining_seconds;
    updateTimerDisplay();

    const questionChanged = data.current_question_id !== currentQuestionId;
    if (questionChanged) {
        currentQuestionId = data.current_question_id;
        hasSubmitted = false;
        hasQuestionData = false;
        responseData = null;
    }

    // Track show_responses state
    const showResponsesChanged = data.show_responses !== showResponses;
    showResponses = data.show_responses;
    
    // Fetch response data if show_responses is enabled
    if (showResponses && currentQuestionId) {
        fetchResponseData();
    } else if (!showResponses) {
        responseData = null;
    }

    // Re-render if: state changed, question changed, show_responses changed,
    // OR we are ACTIVE but were stuck on "Loading Question..." (question data just arrived)
    const questionJustArrived = currentState === "ACTIVE" && !hasQuestionData && data.question_data !== null;
    const transitioningToLocked = currentState === "ACTIVE" && data.room_state === "LOCKED" && !hasSubmitted;

    if (data.room_state !== currentState || questionChanged || questionJustArrived || showResponsesChanged) {
        if (transitioningToLocked) {
            // Try to auto-submit before rendering the locked screen
            attemptAutoSubmit(data);
        } else {
            currentState = data.room_state;
            if (data.question_data) hasQuestionData = true;
            renderState(data);
        }
    }
}

function fetchResponseData() {
    fetch(`/api/teacher/responses?room_id=${ROOM_ID}&question_id=${currentQuestionId}`)
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                responseData = data;
                // Re-render to show updated response data
                fetch(`/api/room/status?room_id=${ROOM_ID}&student_name=${encodeURIComponent(STUDENT_NAME)}`)
                    .then(r => r.json())
                    .then(d => renderState(d));
            }
        })
        .catch(err => console.error('Error fetching responses:', err));
}

function renderState(data) {
    if (currentState === "WAITING") {
        showWaitingState();
    } else if (currentState === "ACTIVE") {
        showActiveState(data.question_data);
    } else if (currentState === "LOCKED") {
        showLockedState();
    }
}

// --- Renderers ---

function showWaitingState() {
    viewport.innerHTML = `
        <h3 style="margin-bottom: 20px; color: #64748B;">State: WAITING</h3>
        <div class="state-card waiting">
            <h3>👀 Eyes on Teacher</h3>
            <p>Listen to the presentation and engage with the instructor.</p>
        </div>
    `;
}

function showLockedState() {
    viewport.innerHTML = `
        <h3 style="margin-bottom: 20px; color: #64748B;">State: LOCKED</h3>
        <div class="state-card" style="background: #FEF3C7; border: 2px solid #F59E0B;">
            <h3>⏱️ Time's Up!</h3>
            <p>Awaiting feedback from instructor...</p>
        </div>
    `;
}

function showActiveState(qData) {
    if (!qData) {
        viewport.innerHTML = `<div class="state-card"><h3>Loading Question...</h3></div>`;
        return;
    }

    let formHTML = '';
    
    if (hasSubmitted) {
        formHTML = `
            <div style="text-align: center; color: #10B981; font-weight: bold; margin-top: 20px; padding: 20px; border: 2px dashed #10B981; border-radius: 8px; background: #ECFDF5;">
                ✅ Answer submitted successfully. Waiting for others...
            </div>
        `;
    } else {
        if (qData.type === 'MCQ') {
            const options = qData.options.split('|');
            // Check if this is a multi-select question
            const isMultiSelect = qData.is_multi_select === true;
            const inputType = isMultiSelect ? 'checkbox' : 'radio';
            
            let optionsHTML = options.map(opt => {
                const optParts = opt.split(':');
                const optVal = optParts[0].trim(); // Extract 'A', 'B', etc.
                return `
                    <label class="mcq-option">
                        <input type="${inputType}" name="answer" value="${optVal}">
                        <span>${opt}</span>
                    </label>
                `;
            }).join('');
            
            const instructionText = isMultiSelect ? '<p style="color: #64748B; font-style: italic; margin-bottom: 12px;">Select all that apply</p>' : '';
            
            formHTML = `
                ${instructionText}
                <div class="mcq-options" id="mcq-form">
                    ${optionsHTML}
                </div>
                <button class="btn-primary" style="margin-top: 20px;" onclick="submitAnswer('MCQ')">Submit Answer</button>
            `;
        } else if (qData.type === 'SHORT') {
            formHTML = `
                <textarea id="short-answer" class="short-answer-input" placeholder="Type your answer here..." autocomplete="off" rows="4"></textarea>
                <button class="btn-primary" onclick="submitAnswer('SHORT')">Submit Answer</button>
            `;
        }
    }

    let responsesHTML = '';
    if (showResponses && responseData) {
        responsesHTML = renderResponseDistribution();
    }

    viewport.innerHTML = `
        <h3 style="margin-bottom: 20px; color: #64748B;">State: ACTIVE</h3>
        <div class="question-container">
            <div class="timer-display" id="local-timer">--:--</div>
            <div class="question-prompt">
                ${qData.prompt.includes('`') ? renderCodeSnippet(qData.prompt) : qData.prompt}
            </div>
            ${formHTML}
            ${responsesHTML}
        </div>
    `;
    updateTimerDisplay();
}

function renderCodeSnippet(prompt) {
    // Basic backtick replacement for code snippet styling
    return prompt.replace(/`([^`]+)`/g, '<code>$1</code>');
}

function renderResponseDistribution() {
    if (!responseData || !responseData.question_data) return '';
    
    let html = `<div style="margin-top: 30px; padding: 20px; background: #F8FAFC; border-radius: 8px; border: 2px solid #CBD5E1;">
        <h4 style="margin: 0 0 15px 0; color: #475569;">📊 Class Response Distribution</h4>`;
    
    if (responseData.question_type === 'MCQ') {
        const qData = responseData.question_data;
        const options = qData.options.split('|');
        const correctOpt = qData.correct_answer.trim();
        const total = responseData.total_submitted;
        
        options.forEach(opt => {
            let optVal = opt.split(':')[0].trim();
            let count = responseData.stats[optVal] || 0;
            let pct = total > 0 ? Math.round((count / total) * 100) : 0;
            let isCorrect = (optVal === correctOpt);
            
            let barColor = isCorrect ? '#10B981' : '#EF4444';
            let labelSuffix = isCorrect ? ' ✓ (Correct)' : '';
            
            html += `
                <div style="margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 14px;">
                        <span style="font-weight: 500;">${opt}${labelSuffix}</span>
                        <span><strong>${pct}%</strong> (${count}/${total})</span>
                    </div>
                    <div style="background: #E2E8F0; border-radius: 4px; height: 24px; overflow: hidden;">
                        <div style="background: ${barColor}; height: 100%; width: ${pct}%; transition: width 0.3s;"></div>
                    </div>
                </div>
            `;
        });
        
    } else if (responseData.question_type === 'SHORT') {
        const qData = responseData.question_data;
        let correctNorm = qData ? qData.correct_answer.toLowerCase().trim() : "";
        
        const entries = Object.entries(responseData.stats).sort((a,b) => b[1].count - a[1].count);
        
        if (entries.length === 0) {
            html += `<p style="color: #94A3B8; margin: 10px 0;">No submissions yet.</p>`;
        }
        
        entries.forEach(([norm, info]) => {
            let isCorrect = (norm === correctNorm);
            let borderColor = isCorrect ? '#10B981' : '#EF4444';
            let icon = isCorrect ? '✓' : '✗';
            
            html += `
                <div style="margin-bottom: 10px; padding: 10px; background: white; border-left: 4px solid ${borderColor}; border-radius: 4px;">
                    <code style="font-size: 14px;">${info.raw}</code> 
                    <span style="color: #64748B; margin-left: 8px;">${icon} [${info.count} student${info.count > 1 ? 's' : ''}]</span>
                </div>
            `;
        });
    }
    
    html += `</div>`;
    return html;
}

// --- Auto-Submit on Lock ---
function attemptAutoSubmit(lockedData) {
    let ans = null;

    // Try to grab a Short Answer
    const shortInput = document.getElementById('short-answer');
    if (shortInput && shortInput.value.trim()) {
        ans = shortInput.value.trim();
    }

    // Try to grab a selected MCQ option
    const mcqSelected = document.querySelector('input[name="answer"]:checked');
    if (mcqSelected) {
        ans = mcqSelected.value;
    }

    if (ans && currentQuestionId) {
        fetch('/api/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                q_id: currentQuestionId,
                ans: ans,
                room_id: ROOM_ID,
                student_name: STUDENT_NAME
            })
        })
        .then(r => r.json())
        .then(result => {
            if (result.status === 'success') {
                hasSubmitted = true;
                showToast('Your answer was auto-submitted before time ran out.', 'info');
            }
        })
        .catch(err => console.error('Auto-submit failed:', err))
        .finally(() => {
            // Always render locked state after the attempt
            currentState = lockedData.room_state;
            renderState(lockedData);
        });
    } else {
        // Nothing to submit — just transition to locked
        currentState = lockedData.room_state;
        renderState(lockedData);
    }
}


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

// --- Interaction ---

function submitAnswer(type) {
    if (hasSubmitted) return;
    
    let ans = null;
    if (type === 'MCQ') {
        const selectedInputs = document.querySelectorAll('input[name="answer"]:checked');
        if (selectedInputs.length === 0) {
            showToast("Please select at least one option.", "error");
            return;
        }
        // If multiple selections, join with comma and space
        const values = Array.from(selectedInputs).map(input => input.value);
        ans = values.join(', ');
    } else if (type === 'SHORT') {
        const input = document.getElementById('short-answer');
        if (!input.value.trim()) {
            showToast("Please enter an answer.", "error");
            return;
        }
        ans = input.value.trim();
    }

    fetch('/api/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            q_id: currentQuestionId,
            ans: ans,
            room_id: ROOM_ID,
            student_name: STUDENT_NAME
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            hasSubmitted = true;
            showToast("Answer submitted successfully!", "success");
            // Force re-render to show success state
            fetch(`/api/room/status?room_id=${ROOM_ID}&student_name=${encodeURIComponent(STUDENT_NAME)}`)
                .then(r => r.json())
                .then(d => renderState(d));
        } else {
            showToast("Error submitting: " + data.message, "error");
        }
    })
    .catch(err => {
        console.error(err);
        showToast("Network error submitting answer.", "error");
    });
}

// --- Timer Logic ---

function updateTimerDisplay() {
    const timerEl = document.getElementById('local-timer');
    if (!timerEl) return;
    
    let m = Math.floor(timeRemaining / 60);
    let s = timeRemaining % 60;
    timerEl.textContent = `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

// Local tick to make timer smooth
setInterval(() => {
    if (currentState === "ACTIVE" && timeRemaining > 0) {
        timeRemaining--;
        updateTimerDisplay();
    }
}, 1000);

// Start
pollServer();
