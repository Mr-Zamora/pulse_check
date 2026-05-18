// Admin Dashboard JavaScript

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

// --- Initialize ---
function init() {
    loadStats();
    loadRoomList();
}

// --- Statistics ---
function loadStats() {
    fetch('/api/admin/stats')
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                document.getElementById('stat-rooms').textContent = data.stats.rooms;
                document.getElementById('stat-students').textContent = data.stats.students;
                document.getElementById('stat-questions').textContent = data.stats.questions;
                document.getElementById('stat-responses').textContent = data.stats.responses;
            }
        })
        .catch(err => {
            console.error('Error loading stats:', err);
        });
}

// --- Room Management ---
function loadRoomList() {
    fetch('/api/admin/rooms')
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                renderRoomTable(data.rooms);
                loadStats(); // Refresh stats too
            } else {
                showToast('Error loading rooms: ' + data.message, 'error');
            }
        })
        .catch(err => {
            console.error('Error loading rooms:', err);
            showToast('Network error loading rooms', 'error');
        });
}

function renderRoomTable(rooms) {
    const container = document.getElementById('room-list');
    
    if (rooms.length === 0) {
        container.innerHTML = '<p style="color: #94A3B8; margin-top: 15px;">No active rooms</p>';
        return;
    }
    
    let html = '<table><thead><tr><th>Room ID</th><th>State</th><th>Question</th><th>Students</th><th>Time</th><th class="actions-cell">Actions</th></tr></thead><tbody>';
    
    rooms.forEach(room => {
        const questionDisplay = room.question_id || '<em style="color: #94A3B8;">None</em>';
        const timeDisplay = room.time_remaining ? `${room.time_remaining}s` : '-';
        const stateClass = `state-${room.state.toLowerCase()}`;
        
        const safeId = room.room_id.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        html += `<tr>
            <td><strong>${safeId}</strong></td>
            <td><span class="state-badge ${stateClass}">${room.state}</span></td>
            <td>${questionDisplay}</td>
            <td>${room.student_count}</td>
            <td>${timeDisplay}</td>
            <td class="actions-cell">
                <button class="btn-small delete-room-btn" data-room-id="${safeId}" title="Delete this room">🗑️</button>
            </td>
        </tr>`;
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;

    container.querySelectorAll('.delete-room-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            deleteRoom(this.dataset.roomId);
        });
    });
}

function deleteRoom(roomId) {
    if (!confirm(`Delete room ${roomId}? This will remove the room and all its state data.`)) {
        return;
    }
    
    fetch('/api/admin/delete_room', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room_id: roomId })
    })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                showToast(`Room ${roomId} deleted`, 'success');
                loadRoomList();
            } else {
                showToast('Error: ' + data.message, 'error');
            }
        })
        .catch(err => {
            console.error(err);
            showToast('Network error deleting room', 'error');
        });
}

function deleteAllRooms() {
    if (!confirm('⚠️ Delete ALL rooms? This will clear all room state data. This cannot be undone!')) {
        return;
    }
    
    fetch('/api/admin/delete_all_rooms', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                showToast('All rooms deleted', 'success');
                loadRoomList();
            } else {
                showToast('Error: ' + data.message, 'error');
            }
        })
        .catch(err => {
            console.error(err);
            showToast('Network error deleting rooms', 'error');
        });
}

// --- Data Management ---
function deleteAllResponses() {
    if (!confirm('⚠️ Delete ALL responses? This will clear all student answer history. This cannot be undone!')) {
        return;
    }
    
    fetch('/api/admin/delete_all_responses', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                showToast('All responses deleted', 'success');
                loadStats();
            } else {
                showToast('Error: ' + data.message, 'error');
            }
        })
        .catch(err => {
            console.error(err);
            showToast('Network error deleting responses', 'error');
        });
}

function clearDisconnected() {
    if (!confirm('Clear all disconnected students from the database?')) {
        return;
    }
    
    fetch('/api/admin/clear_disconnected', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                showToast(data.message, 'success');
                loadStats();
            } else {
                showToast('Error: ' + data.message, 'error');
            }
        })
        .catch(err => {
            console.error(err);
            showToast('Network error clearing disconnected students', 'error');
        });
}

// --- Backup ---
function downloadBackup() {
    window.location.href = '/api/admin/backup';
    showToast('Downloading backup...', 'info');
}

// Initialize on page load
window.addEventListener('DOMContentLoaded', init);
