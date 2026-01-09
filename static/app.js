// API Configuration
const API_BASE = 'http://localhost:8000';
let currentTaskId = null;
let accessToken = null;
let configOptions = null;
let statusPollingInterval = null;

// Default AI System Prompts (for restore functionality)
const DEFAULT_AI_SYSTEM_PROMPTS = {
    character_generation: {
        system: `You are an expert at analyzing stories and creating detailed, vivid character descriptions, focusing on overall appearance. Your skills include:
1. Extracting subtle character details from narrative context
2. Creating consistent and believable descriptions of characters
3. Focusing on permanent features and distinguishing attributes
4. Adapting descriptions to fit the story's genre and tone
5. Balancing physical features with character essence
6. Translating character personalities into comprehensive physical attributes
7. Accurately estimating and describing characters' attributes based on story context
8. Avoiding any mention of clothing or attire in character descriptions`
    },
    video_prompt_generation: {
        system: `You are an expert in video generation. You specialize in creating SIMPLE, MINIMAL motion prompts.

CRITICAL RULES:
1. Keep motion descriptions SHORT and GENERAL
2. Use broad terms like "gentle movement" instead of specific detailed actions
3. Avoid describing complex or specific human movements
4. Prioritize subtlety over detail
5. When in doubt, use less description

You create simple, understated motion descriptions that avoid unintended distortions.`
    },
    storyboard_generation: {
        system: `You are a highly skilled storyboard artist with expertise in visual storytelling across all genres. You excel at:
1. Creating vivid, cinematic scene descriptions for any type of narrative
2. Adapting to various story styles and art styles while maintaining the original narrative's essence
3. Incorporating cinematographic techniques into your descriptions
4. Faithfully representing the original story using exact quotes for subtitles
5. Ensuring visual narrative accurately captures key moments, emotions, and atmosphere
6. Describing characters and settings in detail with consistency
7. Specifying appropriate camera angles, compositions, shot sizes, and lighting
8. Maintaining logical consistency between scene content and technical descriptions
9. Applying creative visual guidance while preserving story integrity
10. ALWAYS ensuring every scene description explicitly reflects the specified art style
11. Describing all visual elements in ways that clearly convey the artistic treatment

CRITICAL: You NEVER use the words "animate", "animated", "animation", "stylized", "illustration", or "illustrated" in your descriptions.
Instead, you use terms like "rendered", "depicted", "portrayed", or "designed".
The art style specification handles the visual treatment - you focus on describing what is seen in that style.`
    }
};

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

    // Populate caption fonts
    const captionFontSelect = document.getElementById('caption_font');
    if (captionFontSelect) {
        captionFontSelect.innerHTML = configOptions.caption_fonts.map(font => 
            `<option value="${font}"${font === 'BebasNeue' ? ' selected' : ''}>${font}</option>`
        ).join('');
        console.log('Populated caption fonts:', captionFontSelect.options.length);
    } else {
        console.error('caption_font select not found');
    }
    
    // Restore saved form values from localStorage
    restoreFormValues();
}

// Save form values to localStorage
function saveFormValues() {
    const formData = {
        custom_story: document.getElementById('custom_story')?.value || '',
        custom_title: document.getElementById('custom_title')?.value || '',
        tweak_prompt: document.getElementById('tweak_prompt')?.value || '',
        story_style_descriptor: document.getElementById('story_style_descriptor')?.value || '',
        art_style: document.getElementById('art_style')?.value || '',
        voice_name: document.getElementById('voice_name')?.value || '',
        language: document.getElementById('language')?.value || '',
        caption_font: document.getElementById('caption_font')?.value || ''
    };
    localStorage.setItem('videoFormData', JSON.stringify(formData));
    console.log('Form data saved to localStorage');
}

// Restore form values from localStorage
function restoreFormValues() {
    const savedData = localStorage.getItem('videoFormData');
    if (!savedData) return;
    
    try {
        const formData = JSON.parse(savedData);
        
        if (formData.custom_story) document.getElementById('custom_story').value = formData.custom_story;
        if (formData.custom_title) document.getElementById('custom_title').value = formData.custom_title;
        if (formData.tweak_prompt) document.getElementById('tweak_prompt').value = formData.tweak_prompt;
        if (formData.story_style_descriptor) document.getElementById('story_style_descriptor').value = formData.story_style_descriptor;
        if (formData.art_style) document.getElementById('art_style').value = formData.art_style;
        if (formData.voice_name) document.getElementById('voice_name').value = formData.voice_name;
        if (formData.language) document.getElementById('language').value = formData.language;
        if (formData.caption_font) document.getElementById('caption_font').value = formData.caption_font;
        
        console.log('Form data restored from localStorage');
    } catch (error) {
        console.error('Error restoring form data:', error);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadConfigOptions();
    
    // Add event listeners to save form values when they change
    const formFields = [
        'custom_story', 'custom_title', 'tweak_prompt',
        'story_style_descriptor', 'art_style', 'voice_name', 
        'language', 'caption_font'
    ];
    
    formFields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            const eventType = field.tagName === 'TEXTAREA' || field.type === 'text' ? 'input' : 'change';
            field.addEventListener(eventType, saveFormValues);
        }
    });
});

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
    
    // Update active button
    const buttons = document.querySelectorAll('.tab-button');
    buttons.forEach(btn => {
        if (btn.textContent.toLowerCase().includes(tabName)) {
            btn.classList.add('active');
        }
    });
    
    // Refresh running tasks when status tab is opened
    if (tabName === 'status') {
        refreshRunningTasks();
    }
}

// Clear form
function clearForm() {
    document.getElementById('video-form').reset();
    document.getElementById('video-result').style.display = 'none';
    localStorage.removeItem('videoFormData');
    console.log('Form cleared and localStorage removed');
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
    
    const tweakPrompt = formData.get('tweak_prompt');
    if (tweakPrompt && tweakPrompt.trim()) {
        data.tweak_prompt = tweakPrompt.trim();
    }
    
    const captionFont = formData.get('caption_font');
    if (captionFont && captionFont.trim()) {
        data.caption_font = captionFont.trim();
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
            
            // Start polling status every 5 seconds
            startStatusPolling();
        } else {
            const error = await response.json();
            alert('Error: ' + (error.detail || 'Failed to generate video'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to submit request: ' + error.message);
    }
});

// Start polling task status
function startStatusPolling() {
    // Clear any existing polling
    stopStatusPolling();
    
    // Poll immediately, then every 5 seconds
    pollTaskStatus();
    statusPollingInterval = setInterval(pollTaskStatus, 5000);
}

// Stop polling task status
function stopStatusPolling() {
    if (statusPollingInterval) {
        clearInterval(statusPollingInterval);
        statusPollingInterval = null;
    }
}

// Poll current task status
async function pollTaskStatus() {
    if (!currentTaskId) return;
    
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
            
            // Update main tab
            updateTaskDisplay(task);
            
            // Update Task Status tab if it's being viewed
            const statusTab = document.getElementById('status-tab');
            const statusTaskId = document.getElementById('status_task_id').value;
            if (statusTab && statusTab.classList.contains('active') && statusTaskId === currentTaskId) {
                // Check if images are already displayed
                const statusResult = document.getElementById('status-result');
                const hasImages = statusResult && statusResult.querySelector('.image-grid');
                
                // If task just completed (100% progress or completed status), always refresh with full details
                if (task.status === 'completed' || task.progress >= 1.0) {
                    // Refresh with full task details including video link and all features
                    displayFullTaskStatus(task);
                } else if (hasImages) {
                    // Only update status and progress, not images
                    updateTaskStatusOnly(task);
                } else {
                    // First time or no images yet - do full update
                    displayFullTaskStatus(task);
                }
            }
            
            // Stop polling AFTER updating the UI if task is completed or failed
            if (task.status === 'completed' || task.status === 'failed') {
                stopStatusPolling();
            }
        }
    } catch (error) {
        console.error('Error polling task status:', error);
    }
}

// Check task status (called when user clicks Check Status button)
async function checkTaskStatus() {
    if (!currentTaskId) {
        alert('No task ID available');
        return;
    }
    
    // Switch to status tab and populate task ID
    switchTab('status');
    document.getElementById('status_task_id').value = currentTaskId;
    
    // Fetch the status
    await fetchTaskStatus();
}

// Fetch task status by ID
async function fetchTaskStatus() {
    const taskId = document.getElementById('status_task_id').value.trim();
    if (!taskId) {
        alert('Please enter a task ID');
        return;
    }
    
    // Update currentTaskId and start polling
    currentTaskId = taskId;
    
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
            
            // Start polling if task is still in progress
            if (task.status !== 'completed' && task.status !== 'failed') {
                startStatusPolling();
            }
        } else {
            alert('Task not found');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to fetch task: ' + error.message);
    }
}

// Update task display (main tab)
function updateTaskDisplay(task) {
    const statusBadge = document.getElementById('task-status');
    statusBadge.textContent = task.status;
    statusBadge.className = `status-badge ${task.status}`;
    
    // Update task ID if different
    const taskIdElement = document.getElementById('task-id');
    if (taskIdElement.textContent !== task.task_id) {
        taskIdElement.textContent = task.task_id;
    }
    
    // Show download link if video is completed
    const videoLink = document.getElementById('video-link');
    if (task.status === 'completed' && task.url) {
        videoLink.innerHTML = `- <a href="${task.url}" target="_blank" rel="noopener noreferrer" download style="color: #4CAF50; font-weight: bold;">Download Video</a>`;
    } else if (task.status === 'failed') {
        videoLink.innerHTML = `- <span style="color: #f44336;">Failed</span>`;
    } else {
        videoLink.innerHTML = '';
    }
}

// Update only status and progress (don't refresh images)
function updateTaskStatusOnly(task) {
    const container = document.getElementById('status-result');
    if (!container) return;
    
    // Update status badge
    const statusBadge = container.querySelector('.status-badge');
    if (statusBadge) {
        statusBadge.textContent = task.status;
        statusBadge.className = `status-badge ${task.status}`;
    }
    
    // Update progress bar
    const progressFill = container.querySelector('.progress-fill');
    if (progressFill) {
        const progress = (task.progress * 100).toFixed(0);
        progressFill.style.width = `${progress}%`;
        progressFill.textContent = `${progress}%`;
        
        // Update progress bar color based on status
        progressFill.classList.remove('completed', 'failed');
        if (task.status === 'completed') {
            progressFill.classList.add('completed');
        } else if (task.status === 'failed') {
            progressFill.classList.add('failed');
        }
    }
    
    // Update status message
    let statusMsgEl = container.querySelector('.status-message');
    if (task.status_message) {
        if (!statusMsgEl) {
            // Create status message element if it doesn't exist
            statusMsgEl = document.createElement('p');
            statusMsgEl.className = 'status-message';
            statusMsgEl.style.cssText = 'color: #666; font-style: italic; margin-top: 10px;';
            const progressBar = container.querySelector('.progress-bar');
            if (progressBar) {
                progressBar.parentNode.insertBefore(statusMsgEl, progressBar.nextSibling);
            }
        }
        statusMsgEl.textContent = task.status_message;
    } else if (statusMsgEl) {
        statusMsgEl.remove();
    }
    
    // Add or update download link if completed
    if (task.status === 'completed' && task.url) {
        // Try to find existing video paragraph
        let videoPara = null;
        const strongs = container.querySelectorAll('p > strong');
        for (let strong of strongs) {
            if (strong.textContent === 'Video:') {
                videoPara = strong.parentElement;
                break;
            }
        }
        
        // If not found, create it after the Created timestamp
        if (!videoPara) {
            videoPara = document.createElement('p');
            const taskIdPara = container.querySelector('p:nth-of-type(3)'); // Created is 3rd paragraph
            if (taskIdPara && taskIdPara.nextSibling) {
                taskIdPara.parentNode.insertBefore(videoPara, taskIdPara.nextSibling);
            } else if (taskIdPara) {
                taskIdPara.parentNode.appendChild(videoPara);
            }
        }
        
        // Update the content with download link
        if (videoPara && !videoPara.querySelector('a')) {
            videoPara.innerHTML = `<strong>Video:</strong> <a href="${task.url}" target="_blank" rel="noopener noreferrer" download style="color: #4CAF50; font-weight: bold;">Download Video</a>`;
        }
    }
}

// Display full task status
function displayFullTaskStatus(task) {
    const container = document.getElementById('status-result');
    
    // Use story_title from the task, fallback to custom_title, then 'Untitled'
    const title = task.story_title || task.custom_title || 'Untitled';
    
    let html = `
        <div class="task-card">
            <h3>${title}</h3>
            <p><strong>Status:</strong> <span class="status-badge ${task.status}">${task.status}</span></p>
            <p><strong>Task ID:</strong> ${task.task_id}</p>
            <p><strong>Created:</strong> ${new Date(task.created_at).toLocaleString()}</p>
    `;
    
    // Add download link if video is completed
    if (task.status === 'completed' && task.url) {
        html += `<p><strong>Video:</strong> <a href="${task.url}" target="_blank" rel="noopener noreferrer" download style="color: #4CAF50; font-weight: bold;">Download Video</a></p>`;
    }
    
    // Add status class to progress bar
    const progressClass = task.status === 'completed' ? 'completed' : (task.status === 'failed' ? 'failed' : '');
    
    html += `
            <div class="progress-bar">
                <div class="progress-fill ${progressClass}" style="width: ${(task.progress * 100).toFixed(0)}%">
                    ${(task.progress * 100).toFixed(0)}%
                </div>
            </div>
    `;
    
    // Add status message if present
    if (task.status_message) {
        html += `<p class="status-message" style="color: #666; font-style: italic; margin-top: 10px;">${task.status_message}</p>`;
    }
    
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
        // Sort images to maintain story sequence
        // Use scene_number if available (new tasks), otherwise use created_at (old tasks)
        const sortedImages = [...task.images].sort((a, b) => {
            // If both have scene_number, use that
            if (a.scene_number !== undefined && a.scene_number !== null && 
                b.scene_number !== undefined && b.scene_number !== null) {
                return a.scene_number - b.scene_number;
            }
            // If only one has scene_number, prioritize it
            if (a.scene_number !== undefined && a.scene_number !== null) return -1;
            if (b.scene_number !== undefined && b.scene_number !== null) return 1;
            // Fall back to created_at for old tasks
            return new Date(a.created_at) - new Date(b.created_at);
        });
        
        html += `
            <h4>Generated Images (${sortedImages.length}):</h4>
            <div class="image-grid">
        `;
        
        sortedImages.forEach((img, idx) => {
            if (img.urls && img.urls.length > 0) {
                html += `
                    <div class="image-card" data-image-id="${img.id}">
                        <img src="${img.urls[0]}" alt="Scene ${idx + 1}">
                        <p>${img.subtitles || `Scene ${idx + 1}`}</p>
                `;
                
                // Add editable image prompt - collapsed by default
                const imagePrompt = img.enhanced_prompt || img.prompt || '';
                html += `
                    <details class="prompt-details" style="margin-top: 10px;">
                        <summary style="cursor: pointer; color: #2196F3; font-weight: bold; font-size: 0.9em; padding: 8px 0;">
                            🖼️ Image Prompt
                        </summary>
                        <div style="margin-top: 8px; padding: 10px; background: #f8f9fa; border-radius: 4px; border: 1px solid #e0e0e0;">
                            <textarea 
                                id="image-prompt-${idx}" 
                                class="prompt-textarea"
                                placeholder="Image generation prompt will appear here..."
                                style="width: 100%; min-height: 100px; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85em; font-family: inherit; resize: vertical; background: white;"
                                oninput="onPromptChanged(${idx}, 'image')"
                            >${imagePrompt}</textarea>
                        </div>
                    </details>
                `;
                
                // Add editable video generation request if available
                if (img.video_generation_request) {
                    const videoReq = img.video_generation_request;
                    html += `
                        <details class="prompt-details" style="margin-top: 10px;">
                            <summary style="cursor: pointer; color: #667eea; font-weight: bold; font-size: 0.9em; padding: 8px 0;">
                                📹 Video Motion Prompt
                            </summary>
                            <div style="margin-top: 8px; padding: 10px; background: #f8f9fa; border-radius: 4px; border: 1px solid #e0e0e0;">
                                <label style="display: block; margin-bottom: 6px; font-weight: 600; font-size: 0.85em; color: #333;">Motion Prompt:</label>
                                <textarea 
                                    id="video-prompt-${idx}" 
                                    class="prompt-textarea"
                                    style="width: 100%; min-height: 60px; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85em; font-family: inherit; margin-bottom: 12px; background: white; resize: vertical;"
                                    oninput="onPromptChanged(${idx}, 'video')"
                                >${videoReq.prompt || ''}</textarea>
                                
                                <label style="display: block; margin-bottom: 6px; font-weight: 600; font-size: 0.85em; color: #333;">Negative Prompt:</label>
                                <textarea 
                                    id="video-negative-${idx}" 
                                    class="prompt-textarea"
                                    style="width: 100%; min-height: 50px; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85em; font-family: inherit; background: white; resize: vertical;"
                                    oninput="onPromptChanged(${idx}, 'video')"
                                >${videoReq.negative_prompt || ''}</textarea>
                            </div>
                        </details>
                    `;
                }
                
                // Add regenerate button (hidden initially)
                html += `
                    <button 
                        id="regenerate-btn-${idx}" 
                        class="regenerate-button" 
                        style="display: none; width: 100%; margin-top: 10px; padding: 8px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;"
                        onclick="regenerateScene(${idx})"
                    >
                        🔄 Regenerate with New Prompts
                    </button>
                `;
                
                html += `</div>`;
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

// Copy video generation request to clipboard
function copyVideoRequest(imageIndex) {
    const taskId = document.getElementById('status_task_id').value.trim();
    if (!taskId) return;
    
    // Get the current task from the last fetch
    fetch(`${API_BASE}/v1/video/tasks/${taskId}`)
        .then(response => response.json())
        .then(task => {
            if (task.images && task.images[imageIndex] && task.images[imageIndex].video_generation_request) {
                const videoReq = task.images[imageIndex].video_generation_request;
                const jsonStr = JSON.stringify(videoReq, null, 2);
                
                // Copy to clipboard
                navigator.clipboard.writeText(jsonStr).then(() => {
                    alert('Video request JSON copied to clipboard!');
                }).catch(err => {
                    console.error('Failed to copy:', err);
                    // Fallback: show the JSON in a prompt
                    prompt('Copy this JSON:', jsonStr);
                });
            }
        })
        .catch(error => {
            console.error('Error fetching task:', error);
        });
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

// Running Tasks Panel Functions
async function refreshRunningTasks() {
    const listContainer = document.getElementById('running-tasks-list');
    listContainer.innerHTML = '<div class="loading-message">Loading tasks...</div>';
    
    try {
        const token = await getAuthToken();
        if (!token) {
            listContainer.innerHTML = '<div class="loading-message" style="color: #f44336;">Authentication required</div>';
            return;
        }
        
        const response = await fetch(`${API_BASE}/v1/video/tasks?limit=50`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            displayRunningTasks(data.tasks || []);
        } else {
            listContainer.innerHTML = '<div class="loading-message" style="color: #f44336;">Failed to load tasks</div>';
        }
    } catch (error) {
        console.error('Error fetching tasks:', error);
        listContainer.innerHTML = '<div class="loading-message" style="color: #f44336;">Error loading tasks</div>';
    }
}

function displayRunningTasks(tasks) {
    const activeListContainer = document.getElementById('running-tasks-list');
    const completedListContainer = document.getElementById('completed-tasks-list');
    
    // Filter active tasks (not completed or failed)
    const activeTasks = tasks.filter(task => 
        task.status === 'queued' || 
        task.status === 'processing' || 
        task.status === 'waiting_for_clips'
    );
    
    // Filter completed and failed tasks
    const completedTasks = tasks.filter(task => 
        task.status === 'completed' || 
        task.status === 'failed'
    );
    
    // Display active tasks
    if (activeTasks.length === 0) {
        activeListContainer.innerHTML = '<div class="no-tasks-message">No active tasks</div>';
    } else {
        activeListContainer.innerHTML = activeTasks.map(task => {
            const title = task.story_title || task.custom_title || 'Untitled Video';
            const progress = Math.round((task.progress || 0) * 100);
            const statusMessage = task.status_message || '';
            const createdAt = new Date(task.created_at).toLocaleString();
            
            return `
                <div class="task-card">
                    <div class="task-info">
                        <div class="task-title">${title}</div>
                        <div class="task-id">ID: ${task.task_id}</div>
                        <div class="task-meta">
                            <span class="status-badge ${task.status}">${task.status.replace('_', ' ')}</span>
                            <span class="task-progress">${progress}%</span>
                            ${statusMessage ? `<span class="task-message">${statusMessage}</span>` : ''}
                        </div>
                        <div class="task-id" style="font-size: 0.75em; color: #999;">Created: ${createdAt}</div>
                    </div>
                    <div class="task-actions">
                        <button class="btn-view" onclick="viewTaskDetails('${task.task_id}')">View</button>
                        <button class="btn-kill" onclick="confirmCancelTask('${task.task_id}')">Kill</button>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    // Display completed tasks
    if (completedTasks.length === 0) {
        completedListContainer.innerHTML = '<div class="no-tasks-message">No completed tasks</div>';
    } else {
        completedListContainer.innerHTML = completedTasks.map(task => {
            const title = task.story_title || task.custom_title || 'Untitled Video';
            const createdAt = new Date(task.created_at).toLocaleString();
            const completedAt = task.updated_at ? new Date(task.updated_at).toLocaleString() : createdAt;
            const costDisplay = task.total_cost != null ? `$${task.total_cost.toFixed(4)}` : 'N/A';
            
            return `
                <div class="task-card completed">
                    <div class="task-info-compact">
                        <span class="task-title-compact">${title}</span>
                        <span class="task-separator">|</span>
                        <span class="task-id-compact">${task.task_id.substring(0, 8)}...</span>
                        <span class="task-separator">|</span>
                        <span class="status-badge ${task.status}">${task.status}</span>
                        <span class="task-separator">|</span>
                        <span class="task-cost-compact">💰 ${costDisplay}</span>
                        <span class="task-separator">|</span>
                        <span class="task-time-compact">⏱ ${completedAt}</span>
                    </div>
                    <div class="task-actions-compact">
                        <button class="btn-view-compact" onclick="viewTaskDetails('${task.task_id}')">View</button>
                        <button class="btn-delete-compact" onclick="confirmDeleteTask('${task.task_id}')">×</button>
                    </div>
                </div>
            `;
        }).join('');
    }
}

function viewTaskDetails(taskId) {
    // Set the task ID in the lookup input
    document.getElementById('status_task_id').value = taskId;
    // Fetch the task status
    fetchTaskStatus();
    // Scroll to the status result area
    setTimeout(() => {
        const statusResult = document.getElementById('status-result');
        if (statusResult) {
            statusResult.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }, 100);
}

async function confirmDeleteTask(taskId) {
    if (!confirm(`Are you sure you want to permanently delete task ${taskId.substring(0, 8)}...? This cannot be undone.`)) {
        return;
    }
    
    await deleteTaskFromPanel(taskId);
}

async function deleteTaskFromPanel(taskId) {
    try {
        const token = await getAuthToken();
        if (!token) {
            alert('Authentication required');
            return;
        }
        
        const response = await fetch(`${API_BASE}/v1/video/tasks/${taskId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const result = await response.json();
            console.log('Task deleted:', result);
            // Refresh the task list
            await refreshRunningTasks();
        } else {
            const error = await response.json();
            alert(`Failed to delete task: ${error.detail || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error deleting task:', error);
        alert('Error deleting task. Check console for details.');
    }
}

async function confirmCancelTask(taskId) {
    if (!confirm(`Are you sure you want to cancel task ${taskId.substring(0, 8)}...?`)) {
        return;
    }
    
    await cancelTaskFromPanel(taskId);
}

async function cancelTaskFromPanel(taskId) {
    try {
        const token = await getAuthToken();
        if (!token) {
            alert('Authentication required');
            return;
        }
        
        const response = await fetch(`${API_BASE}/v1/video/tasks/${taskId}/cancel`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        // Always refresh the list regardless of response
        // This handles both success and "already cancelled" cases gracefully
        await refreshRunningTasks();
        
        if (!response.ok) {
            // Only show error if it's a real error (not "already cancelled")
            try {
                const error = await response.json();
                // Don't alert for "already cancelled" errors
                if (!error.detail?.includes('already')) {
                    console.error('Cancel task error:', error);
                }
            } catch (e) {
                console.error('Cancel task failed:', response.status, response.statusText);
            }
        }
    } catch (error) {
        console.error('Error cancelling task:', error);
        // Refresh anyway to show current state
        await refreshRunningTasks();
    }
}

// Track original prompts for change detection
let originalPrompts = {};

// Store task images data globally for regeneration
let currentTaskImages = [];

// Called when any prompt is changed
function onPromptChanged(sceneIdx, promptType) {
    const regenerateBtn = document.getElementById(`regenerate-btn-${sceneIdx}`);
    if (!regenerateBtn) return;
    
    // Initialize original prompts if not done
    if (!originalPrompts[sceneIdx]) {
        const imagePrompt = document.getElementById(`image-prompt-${sceneIdx}`);
        const videoPrompt = document.getElementById(`video-prompt-${sceneIdx}`);
        const videoNegative = document.getElementById(`video-negative-${sceneIdx}`);
        
        originalPrompts[sceneIdx] = {
            image: imagePrompt ? imagePrompt.defaultValue : '',
            video: videoPrompt ? videoPrompt.defaultValue : '',
            negative: videoNegative ? videoNegative.defaultValue : ''
        };
    }
    
    // Check if any prompts have changed
    const imagePrompt = document.getElementById(`image-prompt-${sceneIdx}`);
    const videoPrompt = document.getElementById(`video-prompt-${sceneIdx}`);
    const videoNegative = document.getElementById(`video-negative-${sceneIdx}`);
    
    const hasChanges = 
        (imagePrompt && imagePrompt.value !== originalPrompts[sceneIdx].image) ||
        (videoPrompt && videoPrompt.value !== originalPrompts[sceneIdx].video) ||
        (videoNegative && videoNegative.value !== originalPrompts[sceneIdx].negative);
    
    // Show/hide regenerate button
    regenerateBtn.style.display = hasChanges ? 'block' : 'none';
}

// Regenerate a specific scene with new prompts
async function regenerateScene(sceneIdx) {
    const taskId = document.getElementById('status_task_id').value.trim();
    if (!taskId) {
        alert('No task ID available');
        return;
    }
    
    // Get the image ID from the card
    const imageCards = document.querySelectorAll('.image-card');
    if (!imageCards[sceneIdx]) {
        alert('Scene not found');
        return;
    }
    
    const imageId = imageCards[sceneIdx].dataset.imageId;
    if (!imageId) {
        alert('Image ID not found');
        return;
    }
    
    // Get updated prompts
    const imagePromptEl = document.getElementById(`image-prompt-${sceneIdx}`);
    const videoPromptEl = document.getElementById(`video-prompt-${sceneIdx}`);
    const videoNegativeEl = document.getElementById(`video-negative-${sceneIdx}`);
    
    const updates = {};
    
    if (imagePromptEl && imagePromptEl.value !== originalPrompts[sceneIdx]?.image) {
        updates.image_prompt = imagePromptEl.value;
    }
    
    if (videoPromptEl || videoNegativeEl) {
        const videoRequest = {};
        if (videoPromptEl && videoPromptEl.value !== originalPrompts[sceneIdx]?.video) {
            videoRequest.prompt = videoPromptEl.value;
        }
        if (videoNegativeEl && videoNegativeEl.value !== originalPrompts[sceneIdx]?.negative) {
            videoRequest.negative_prompt = videoNegativeEl.value;
        }
        
        if (Object.keys(videoRequest).length > 0) {
            updates.video_generation_request = videoRequest;
        }
    }
    
    if (Object.keys(updates).length === 0) {
        alert('No changes detected');
        return;
    }
    
    if (!confirm(`Regenerate scene ${sceneIdx + 1} with new prompts?`)) {
        return;
    }
    
    try {
        const token = await getAuthToken();
        if (!token) return;
        
        const regenerateBtn = document.getElementById(`regenerate-btn-${sceneIdx}`);
        regenerateBtn.disabled = true;
        regenerateBtn.textContent = '⏳ Regenerating...';
        
        const response = await fetch(`${API_BASE}/v1/video/tasks/${taskId}/images/${imageId}/regenerate`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updates)
        });
        
        if (response.ok) {
            alert('Scene regeneration started! The page will refresh when complete.');
            
            // Update original prompts
            if (updates.image_prompt) {
                originalPrompts[sceneIdx].image = updates.image_prompt;
            }
            if (updates.video_generation_request?.prompt) {
                originalPrompts[sceneIdx].video = updates.video_generation_request.prompt;
            }
            if (updates.video_generation_request?.negative_prompt) {
                originalPrompts[sceneIdx].negative = updates.video_generation_request.negative_prompt;
            }
            
            regenerateBtn.style.display = 'none';
            regenerateBtn.disabled = false;
            regenerateBtn.textContent = '🔄 Regenerate with New Prompts';
            
            // Refresh task status after a delay
            setTimeout(() => fetchTaskStatus(), 3000);
        } else {
            const error = await response.json();
            alert(`Failed to regenerate: ${error.detail || 'Unknown error'}`);
            regenerateBtn.disabled = false;
            regenerateBtn.textContent = '🔄 Regenerate with New Prompts';
        }
    } catch (error) {
        console.error('Error regenerating scene:', error);
        alert('Failed to regenerate scene');
        const regenerateBtn = document.getElementById(`regenerate-btn-${sceneIdx}`);
        regenerateBtn.disabled = false;
        regenerateBtn.textContent = '🔄 Regenerate with New Prompts';
    }
}

// ==================== SETTINGS MANAGEMENT ====================

// Convert hex color to RGB array
function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? [
        parseInt(result[1], 16),
        parseInt(result[2], 16),
        parseInt(result[3], 16)
    ] : [0, 0, 0];
}

// Convert RGB array to hex color
function rgbToHex(rgb) {
    if (!Array.isArray(rgb) || rgb.length !== 3) return '#000000';
    return '#' + rgb.map(x => {
        const hex = Math.max(0, Math.min(255, x)).toString(16);
        return hex.length === 1 ? '0' + hex : hex;
    }).join('');
}

// Convert color name to hex
function colorNameToHex(colorName) {
    const colors = {
        'white': '#ffffff',
        'yellow': '#ffff00',
        'red': '#ff0000',
        'blue': '#0000ff',
        'green': '#00ff00',
        'black': '#000000',
        'orange': '#ffa500',
        'cyan': '#00ffff',
        'magenta': '#ff00ff'
    };
    return colors[colorName.toLowerCase()] || colorName;
}

// Load settings from server and populate form
async function loadSettings() {
    try {
        const response = await fetch(`${API_BASE}/v1/video/config`);
        if (!response.ok) {
            throw new Error('Failed to load settings');
        }
        
        const config = await response.json();
        console.log('Loaded settings:', config);
        
        // Populate closing screen settings
        if (config.video_settings?.closing_screen) {
            const cs = config.video_settings.closing_screen;
            document.getElementById('primary_logo_url').value = cs.primary_logo_url || '';
            document.getElementById('secondary_image_url').value = cs.secondary_image_url || '';
            document.getElementById('closing_bg_color').value = rgbToHex(cs.background_color || [0, 0, 0]);
            document.getElementById('closing_duration').value = cs.duration || 4;
        }
        
        // Populate caption settings
        if (config.video_settings?.captions) {
            const captions = config.video_settings.captions;
            document.getElementById('caption_font_size').value = captions.font_size || 80;
            document.getElementById('max_words_per_phrase').value = captions.max_words_per_phrase || 5;
            document.getElementById('caption_vertical_position').value = captions.vertical_position || 0.75;
            document.getElementById('caption_position_display').textContent = captions.vertical_position || 0.75;
            document.getElementById('caption_text_color').value = colorNameToHex(captions.text_color || 'white');
            document.getElementById('caption_highlight_color').value = colorNameToHex(captions.highlight_color || 'yellow');
        }
        
        // Populate video output settings
        if (config.video_settings?.output) {
            const output = config.video_settings.output;
            document.getElementById('video_width').value = output.width || 1080;
            document.getElementById('video_height').value = output.height || 1920;
            document.getElementById('video_fps').value = output.fps || 20;
            document.getElementById('zoom_speed').value = output.zoom_speed || 0.03;
            document.getElementById('audio_fadeout').value = output.audio_fadeout_duration || 0.3;
        }
        
        // Populate product mention settings
        if (config.product_mention) {
            const pm = config.product_mention;
            document.getElementById('product_mention_enabled').checked = pm.enabled !== false;
            document.getElementById('product_keywords').value = (pm.keywords || []).join(', ');
            document.getElementById('product_prompt_template').value = pm.prompt_template || '';
            document.getElementById('product_reference_images').value = (pm.reference_images || []).join('\n');
        }
        
        // Populate AI prompts settings
        if (config.ai_prompts) {
            const ai = config.ai_prompts;
            if (ai.video_motion) {
                document.getElementById('video_default_prompt').value = ai.video_motion.default_prompt || '';
                document.getElementById('video_negative_prompt').value = ai.video_motion.negative_prompt || '';
            }
            if (ai.image_generation) {
                document.getElementById('image_negative_prompt').value = ai.image_generation.negative_prompt || '';
            }
        }
        
        // Populate AI System Prompts (Danger Zone)
        if (config.ai_system_prompts) {
            const sys = config.ai_system_prompts;
            if (sys.character_generation?.system) {
                document.getElementById('character_system_prompt').value = sys.character_generation.system;
            }
            if (sys.video_prompt_generation?.system) {
                document.getElementById('video_prompt_system_prompt').value = sys.video_prompt_generation.system;
            }
            if (sys.storyboard_generation?.system) {
                document.getElementById('storyboard_system_prompt').value = sys.storyboard_generation.system;
            }
        } else {
            // Use defaults if not set
            document.getElementById('character_system_prompt').value = DEFAULT_AI_SYSTEM_PROMPTS.character_generation.system;
            document.getElementById('video_prompt_system_prompt').value = DEFAULT_AI_SYSTEM_PROMPTS.video_prompt_generation.system;
            document.getElementById('storyboard_system_prompt').value = DEFAULT_AI_SYSTEM_PROMPTS.storyboard_generation.system;
        }
        
        console.log('Settings loaded successfully');
    } catch (error) {
        console.error('Error loading settings:', error);
        alert('Failed to load settings: ' + error.message);
    }
}

// Save settings to server
async function saveSettings() {
    try {
        // Get auth token
        const token = await getAuthToken();
        if (!token) {
            alert('Authentication required to save settings');
            return;
        }
        
        // Build the settings object
        const settings = {
            video_settings: {
                closing_screen: {
                    primary_logo_url: document.getElementById('primary_logo_url').value.trim(),
                    secondary_image_url: document.getElementById('secondary_image_url').value.trim(),
                    background_color: hexToRgb(document.getElementById('closing_bg_color').value),
                    duration: parseFloat(document.getElementById('closing_duration').value) || 4
                },
                captions: {
                    font_size: parseInt(document.getElementById('caption_font_size').value) || 80,
                    max_words_per_phrase: parseInt(document.getElementById('max_words_per_phrase').value) || 5,
                    vertical_position: parseFloat(document.getElementById('caption_vertical_position').value) || 0.75,
                    text_color: document.getElementById('caption_text_color').value,
                    highlight_color: document.getElementById('caption_highlight_color').value
                },
                output: {
                    width: parseInt(document.getElementById('video_width').value) || 1080,
                    height: parseInt(document.getElementById('video_height').value) || 1920,
                    fps: parseInt(document.getElementById('video_fps').value) || 20,
                    zoom_speed: parseFloat(document.getElementById('zoom_speed').value) || 0.03,
                    audio_fadeout_duration: parseFloat(document.getElementById('audio_fadeout').value) || 0.3
                }
            },
            product_mention: {
                enabled: document.getElementById('product_mention_enabled').checked,
                keywords: document.getElementById('product_keywords').value
                    .split(',')
                    .map(k => k.trim())
                    .filter(k => k.length > 0),
                prompt_template: document.getElementById('product_prompt_template').value.trim(),
                reference_images: document.getElementById('product_reference_images').value
                    .split('\n')
                    .map(url => url.trim())
                    .filter(url => url.length > 0)
            },
            ai_prompts: {
                video_motion: {
                    default_prompt: document.getElementById('video_default_prompt').value.trim(),
                    negative_prompt: document.getElementById('video_negative_prompt').value.trim()
                },
                image_generation: {
                    negative_prompt: document.getElementById('image_negative_prompt').value.trim()
                }
            },
            ai_system_prompts: {
                character_generation: {
                    system: document.getElementById('character_system_prompt').value.trim()
                },
                video_prompt_generation: {
                    system: document.getElementById('video_prompt_system_prompt').value.trim()
                },
                storyboard_generation: {
                    system: document.getElementById('storyboard_system_prompt').value.trim()
                }
            }
        };
        
        console.log('Saving settings:', settings);
        
        const response = await fetch(`${API_BASE}/v1/video/config`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(settings)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save settings');
        }
        
        const result = await response.json();
        console.log('Settings saved:', result);
        alert('Settings saved successfully!');
    } catch (error) {
        console.error('Error saving settings:', error);
        alert('Failed to save settings: ' + error.message);
    }
}

// Update caption position display when slider changes
document.addEventListener('DOMContentLoaded', () => {
    const positionSlider = document.getElementById('caption_vertical_position');
    const positionDisplay = document.getElementById('caption_position_display');
    
    if (positionSlider && positionDisplay) {
        positionSlider.addEventListener('input', (e) => {
            positionDisplay.textContent = parseFloat(e.target.value).toFixed(2);
        });
    }
    
    // Enhance number inputs in settings with custom buttons
    enhanceNumberInputs();
    
    // Load settings when page loads
    loadSettings();
});

// Enhance number inputs with custom increment/decrement buttons
function enhanceNumberInputs() {
    const settingsSection = document.querySelector('.settings-section');
    if (!settingsSection) return;
    
    const numberInputs = settingsSection.querySelectorAll('input[type="number"]');
    
    numberInputs.forEach(input => {
        // Skip if already wrapped
        if (input.parentElement.classList.contains('number-input-wrapper')) return;
        
        // Create wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'number-input-wrapper';
        
        // Insert wrapper and move input inside
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);
        
        // Create button container
        const buttons = document.createElement('div');
        buttons.className = 'number-buttons';
        
        // Create increment button
        const incrementBtn = document.createElement('button');
        incrementBtn.type = 'button';
        incrementBtn.className = 'number-btn';
        incrementBtn.innerHTML = '▲';
        incrementBtn.addEventListener('click', () => {
            input.stepUp();
            input.dispatchEvent(new Event('input', { bubbles: true }));
        });
        
        // Create decrement button
        const decrementBtn = document.createElement('button');
        decrementBtn.type = 'button';
        decrementBtn.className = 'number-btn';
        decrementBtn.innerHTML = '▼';
        decrementBtn.addEventListener('click', () => {
            input.stepDown();
            input.dispatchEvent(new Event('input', { bubbles: true }));
        });
        
        buttons.appendChild(incrementBtn);
        buttons.appendChild(decrementBtn);
        wrapper.appendChild(buttons);
    });
}

// Restore a single system prompt to its default value
function restoreDefaultPrompt(promptType) {
    const promptMap = {
        'character': {
            id: 'character_system_prompt',
            key: 'character_generation'
        },
        'video_prompt': {
            id: 'video_prompt_system_prompt',
            key: 'video_prompt_generation'
        },
        'storyboard': {
            id: 'storyboard_system_prompt',
            key: 'storyboard_generation'
        }
    };
    
    const mapping = promptMap[promptType];
    if (!mapping) {
        console.error('Unknown prompt type:', promptType);
        return;
    }
    
    const defaultValue = DEFAULT_AI_SYSTEM_PROMPTS[mapping.key]?.system || '';
    const textarea = document.getElementById(mapping.id);
    
    if (textarea) {
        textarea.value = defaultValue;
        console.log(`Restored ${promptType} prompt to default`);
    }
}

// Restore all system prompts to their default values
function restoreAllDefaultPrompts() {
    if (!confirm('Are you sure you want to restore ALL system prompts to their defaults? This cannot be undone until you reload.')) {
        return;
    }
    
    restoreDefaultPrompt('character');
    restoreDefaultPrompt('video_prompt');
    restoreDefaultPrompt('storyboard');
    
    console.log('All system prompts restored to defaults');
    alert('All system prompts have been restored to defaults. Click "Save Settings" to apply the changes.');
}

// ==================== END SETTINGS MANAGEMENT ====================

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    console.log('Faceless Video API Control Panel Ready');
});
