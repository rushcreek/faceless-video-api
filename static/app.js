// API Configuration
const API_BASE = 'http://localhost:8000';
let currentTaskId = null;
let accessToken = null;

// Tab Switching
function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(`${tabName}-tab`).classList.add('active');
    event.target.classList.add('active');
}

// Clear form
function clearForm() {
    document.getElementById('video-form').reset();
    document.getElementById('video-result').style.display = 'none';
}

// Get authentication token
async function getAuthToken() {
    if (accessToken) return accessToken;
    
    try {
        const response = await fetch(`${API_BASE}/v1/auth/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: 'username=admin&password=Tri2468!'
        });
        
        if (response.ok) {
            const data = await response.json();
            accessToken = data.access_token;
            return accessToken;
        } else {
            throw new Error('Authentication failed');
        }
    } catch (error) {
        console.error('Auth error:', error);
        alert('Authentication failed. Please check your credentials.');
        return null;
    }
}

// Video form submission
document.getElementById('video-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const token = await getAuthToken();
    if (!token) return;
    
    const formData = new FormData(e.target);
    const data = {
        story_topic: formData.get('story_topic'),
        art_style: formData.get('art_style'),
        duration: formData.get('duration'),
        voice_name: formData.get('voice_name'),
        language: formData.get('language')
    };
    
    // Add optional fields if provided
    if (formData.get('custom_title')) {
        data.custom_title = formData.get('custom_title');
    }
    if (formData.get('custom_story')) {
        data.custom_story = formData.get('custom_story');
    }
    
    try {
        const response = await fetch(`${API_BASE}/v1/video`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            const result = await response.json();
            currentTaskId = result.task_id;
            
            document.getElementById('task-id').textContent = result.task_id;
            document.getElementById('task-status').textContent = result.status;
            document.getElementById('task-status').className = 'status-badge';
            document.getElementById('video-result').style.display = 'block';
            
            // Auto-check status every 5 seconds
            setTimeout(checkTaskStatus, 5000);
        } else {
            const error = await response.json();
            alert('Error: ' + (error.detail || 'Failed to generate video'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to submit request: ' + error.message);
    }
});

// Check task status
async function checkTaskStatus() {
    if (!currentTaskId) {
        alert('No task ID available');
        return;
    }
    
    const token = await getAuthToken();
    if (!token) return;
    
    try {
        const response = await fetch(`${API_BASE}/v1/video/tasks/${currentTaskId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const task = await response.json();
            updateTaskDisplay(task);
            
            // Continue polling if still processing
            if (task.status === 'processing' || task.status === 'queued') {
                setTimeout(checkTaskStatus, 5000);
            }
        } else {
            alert('Failed to fetch task status');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to check status: ' + error.message);
    }
}

// Fetch task status by ID
async function fetchTaskStatus() {
    const taskId = document.getElementById('status_task_id').value.trim();
    if (!taskId) {
        alert('Please enter a task ID');
        return;
    }
    
    const token = await getAuthToken();
    if (!token) return;
    
    try {
        const response = await fetch(`${API_BASE}/v1/video/tasks/${taskId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const task = await response.json();
            displayFullTaskStatus(task);
        } else {
            alert('Task not found');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to fetch task: ' + error.message);
    }
}

// Update task display
function updateTaskDisplay(task) {
    const statusBadge = document.getElementById('task-status');
    statusBadge.textContent = task.status;
    statusBadge.className = `status-badge ${task.status}`;
}

// Display full task status
function displayFullTaskStatus(task) {
    const container = document.getElementById('status-result');
    
    let html = `
        <div class="task-card">
            <h3>${task.story_title || 'Untitled'}</h3>
            <p><strong>Status:</strong> <span class="status-badge ${task.status}">${task.status}</span></p>
            <p><strong>Task ID:</strong> ${task.task_id}</p>
            <p><strong>Created:</strong> ${new Date(task.created_at).toLocaleString()}</p>
            
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${(task.progress * 100).toFixed(0)}%">
                    ${(task.progress * 100).toFixed(0)}%
                </div>
            </div>
    `;
    
    if (task.story_description) {
        html += `<p><strong>Description:</strong> ${task.story_description}</p>`;
    }
    
    if (task.story_text) {
        html += `
            <details>
                <summary><strong>Story Text</strong></summary>
                <p style="margin-top: 10px; white-space: pre-wrap;">${task.story_text}</p>
            </details>
        `;
    }
    
    if (task.url) {
        html += `
            <div class="video-player">
                <h4>Generated Video:</h4>
                <video controls>
                    <source src="${task.url}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
                <p><a href="${task.url}" target="_blank">Open in new tab</a></p>
            </div>
        `;
    }
    
    if (task.images && task.images.length > 0) {
        html += `
            <h4>Generated Images (${task.images.length}):</h4>
            <div class="image-grid">
        `;
        
        task.images.forEach((img, idx) => {
            if (img.urls && img.urls.length > 0) {
                html += `
                    <div class="image-card">
                        <img src="${img.urls[0]}" alt="Scene ${idx + 1}">
                        <p>${img.subtitles || `Scene ${idx + 1}`}</p>
                    </div>
                `;
            }
        });
        
        html += `</div>`;
    }
    
    if (task.error_message) {
        html += `<p style="color: red;"><strong>Error:</strong> ${task.error_message}</p>`;
    }
    
    html += `</div>`;
    
    container.innerHTML = html;
}

// Admin settings functions
async function loadAdminSettings() {
    try {
        const response = await fetch(`${API_BASE}/v1/admin/env`);
        if (response.ok) {
            const settings = await response.json();
            
            // Populate form fields
            Object.keys(settings).forEach(key => {
                const field = document.getElementById(key.toLowerCase());
                if (field) {
                    field.value = settings[key] || '';
                }
            });
            
            showAdminMessage('Settings loaded successfully', 'success');
        } else {
            showAdminMessage('Failed to load settings', 'error');
        }
    } catch (error) {
        console.error('Error loading settings:', error);
        showAdminMessage('Note: Admin API endpoint not implemented yet. This is a local-only interface.', 'warning');
    }
}

async function saveAdminSettings() {
    const form = document.getElementById('admin-form');
    const formData = new FormData(form);
    const settings = {};
    
    for (let [key, value] of formData.entries()) {
        if (value) {
            settings[key.toUpperCase()] = value;
        }
    }
    
    try {
        const response = await fetch(`${API_BASE}/v1/admin/env`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        if (response.ok) {
            showAdminMessage('Settings saved successfully! Please restart the server for changes to take effect.', 'success');
        } else {
            showAdminMessage('Failed to save settings', 'error');
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        showAdminMessage('Note: This interface requires an admin API endpoint to be implemented on the backend. For now, please edit .env file directly.', 'warning');
    }
}

function showAdminMessage(message, type) {
    const resultBox = document.getElementById('admin-result');
    resultBox.style.display = 'block';
    resultBox.className = 'result-box';
    
    if (type === 'error') {
        resultBox.style.background = '#ffebee';
        resultBox.style.borderLeftColor = '#f44336';
    } else if (type === 'warning') {
        resultBox.style.background = '#fff3cd';
        resultBox.style.borderLeftColor = '#ffc107';
    } else {
        resultBox.style.background = '#f0f7ff';
        resultBox.style.borderLeftColor = '#667eea';
    }
    
    resultBox.innerHTML = `<p>${message}</p>`;
    
    setTimeout(() => {
        resultBox.style.display = 'none';
    }, 5000);
}

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    console.log('Faceless Video API Control Panel Ready');
});
