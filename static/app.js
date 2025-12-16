// API Configuration
const API_BASE = 'http://localhost:8000';
let currentTaskId = null;
let accessToken = null;
let configOptions = null;

// Load configuration options on page load
async function loadConfigOptions() {
    try {
        const response = await fetch(`${API_BASE}/v1/video/config`);
        if (response.ok) {
            configOptions = await response.json();
            populateDropdowns();
        }
    } catch (error) {
        console.error('Failed to load config options:', error);
    }
}

// Populate dropdowns with config data
function populateDropdowns() {
    if (!configOptions) {
        console.error('No config options available');
        return;
    }

    console.log('Populating dropdowns with config:', configOptions);

    // Populate voices
    const voiceSelect = document.getElementById('voice_name');
    if (voiceSelect) {
        voiceSelect.innerHTML = configOptions.voices.map(v => 
            `<option value="${v.id}">${v.name}</option>`
        ).join('');
        console.log('Populated voices:', voiceSelect.options.length);
    } else {
        console.error('voice_name select not found');
    }

    // Populate languages
    const languageSelect = document.getElementById('language');
    if (languageSelect) {
        languageSelect.innerHTML = configOptions.languages.map(lang => 
            `<option value="${lang}">${lang.charAt(0).toUpperCase() + lang.slice(1)}</option>`
        ).join('');
        console.log('Populated languages:', languageSelect.options.length);
    } else {
        console.error('language select not found');
    }

    // Populate art styles
    const artStyleSelect = document.getElementById('art_style');
    if (artStyleSelect) {
        artStyleSelect.innerHTML = configOptions.art_styles.map(style => {
            const displayName = style.split('-').map(word => 
                word.charAt(0).toUpperCase() + word.slice(1)
            ).join(' ');
            return `<option value="${style}"${style === 'cinematic' ? ' selected' : ''}>${displayName}</option>`;
        }).join('');
        console.log('Populated art styles:', artStyleSelect.options.length);
    } else {
        console.error('art_style select not found');
    }

    // Populate story style descriptors
    const styleDescriptorSelect = document.getElementById('story_style_descriptor');
    if (styleDescriptorSelect) {
        styleDescriptorSelect.innerHTML = '<option value="">None</option>' + 
            configOptions.story_style_descriptors.map(desc => 
                `<option value="${desc}">${desc.charAt(0).toUpperCase() + desc.slice(1)}</option>`
            ).join('');
        console.log('Populated story style descriptors:', styleDescriptorSelect.options.length);
    } else {
        console.error('story_style_descriptor select not found');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', loadConfigOptions);

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
    const customStory = formData.get('custom_story');
    
    // Validate custom story is required and has minimum length
    if (!customStory || customStory.trim().length < 100) {
        alert('Please provide a story script of at least 100 characters');
        return;
    }
    
    const data = {
        custom_story: customStory.trim(),
        art_style: formData.get('art_style'),
        voice_name: formData.get('voice_name'),
        language: formData.get('language')
    };
    
    // Add optional fields if provided
    const customTitle = formData.get('custom_title');
    if (customTitle && customTitle.trim()) {
        data.custom_title = customTitle.trim();
    }
    
    const storyStyleDescriptor = formData.get('story_style_descriptor');
    if (storyStyleDescriptor && storyStyleDescriptor.trim()) {
        data.story_style_descriptor = storyStyleDescriptor.trim();
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
    
    // Show download link if video is completed
    const videoLink = document.getElementById('video-link');
    if (task.status === 'completed' && task.url) {
        videoLink.innerHTML = `- <a href="${task.url}" target="_blank" rel="noopener noreferrer" download style="color: #4CAF50; font-weight: bold;">Download Video</a>`;
    } else if (task.status === 'failed') {
        videoLink.innerHTML = '';
    }
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
    `;
    
    // Add download link if video is completed
    if (task.status === 'completed' && task.url) {
        html += `<p><strong>Video:</strong> <a href="${task.url}" target="_blank" rel="noopener noreferrer" download style="color: #4CAF50; font-weight: bold;">Download Video</a></p>`;
    }
    
    html += `
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
