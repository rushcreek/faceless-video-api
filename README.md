# Faceless Video API - Complete Guide

## 🎬 Overview

The Faceless Video API is a comprehensive video generation system that creates AI-powered videos from text stories. It features:

- **AI Story Generation**: Convert text stories into cinematic videos
- **Multiple Art Styles**: Choose from 15+ artistic styles (cinematic, anime, pixar, etc.)
- **Voice Synthesis**: 9 different AI voices in multiple languages
- **Social Media Integration**: Built-in LinkedIn posting capabilities
- **Web Interface**: User-friendly control panel for video generation
- **REST API**: Full programmatic access via HTTP endpoints

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Virtual environment (recommended)
- FFmpeg (optional, for audio processing)

### Installation

1. **Clone or copy the project**:
   ```bash
   cd faceless-video-api
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   # On Windows:
   & venv/Scripts/Activate.ps1
   # On Linux/Mac:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the server**:
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. **Access the web interface**:
   - Local: http://localhost:8000
   - Network: http://YOUR_IP:8000 (e.g., http://192.168.12.199:8000)

## 🌐 Network Access

The server is configured to be accessible from other machines on your local network.

### Current Network Setup
- **Server IP**: 192.168.12.199
- **Port**: 8000
- **Access URL**: http://192.168.12.199:8000

### Firewall Considerations
Ensure your firewall allows incoming connections on port 8000. The server binds to `0.0.0.0` to accept connections from any network interface.

## 🔧 API Usage

### Authentication

All API endpoints require authentication. First, obtain an access token:

```bash
curl -X POST "http://localhost:8000/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=Tri2468!"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Video Generation

Generate a video from a text story:

```bash
curl -X POST "http://localhost:8000/v1/video" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "custom_story": "Once upon a time, there was a curious cat who loved to explore. Every day, the cat would venture into the forest, discovering new wonders and making friends with woodland creatures. One sunny morning, the cat found a magical tree that granted wishes. The cat wished for endless adventures and lived happily ever after.",
    "art_style": "cinematic",
    "voice_name": "theo",
    "language": "english",
    "caption_font": "BebasNeue"
  }'
```

### Check Generation Status

Monitor video generation progress:

```bash
curl -X GET "http://localhost:8000/v1/video/tasks/TASK_ID_HERE" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Post to LinkedIn

Share completed videos on LinkedIn:

```bash
curl -X POST "http://localhost:8000/v1/video/tasks/TASK_ID/post-to-linkedin" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{"content": "Check out my new AI-generated video!"}'
```

## 📋 API Reference

### Endpoints

#### Authentication
- `POST /v1/auth/token` - Get access token

#### Video Generation
- `GET /v1/video/config` - Get configuration options
- `PUT /v1/video/config` - Update video settings
- `POST /v1/video` - Generate new video
- `GET /v1/video/tasks/{task_id}` - Get task status
- `POST /v1/video/tasks/{task_id}/cancel` - Cancel task
- `POST /v1/video/tasks/{task_id}/images/{image_id}/regenerate` - Regenerate scene
- `POST /v1/video/tasks/{task_id}/post-to-linkedin` - Post to LinkedIn

### Required Fields for Video Generation

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `custom_story` | string | Yes | Story text (min 100 characters) |
| `art_style` | string | Yes | Visual style |
| `voice_name` | string | Yes | AI voice to use |
| `language` | string | Yes | Audio language |
| `caption_font` | string | Yes | Font for subtitles |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `custom_title` | string | Video title |
| `story_style_descriptor` | string | Visual tone modifier |
| `tweak_prompt` | string | Image generation refinements |

## 🎨 Configuration Options

### Art Styles
- `cinematic`, `photorealistic`, `anime`, `comic-book`, `pixar-art`
- `oil-painting`, `watercolor`, `sketch`, `noir`, `cyberpunk`
- `fantasy`, `minimalist`, `impressionist`, `pop-art`, `steampunk`

### Voices
- `theo`, `dan-wegner`, `cathy`, `tessa`, `dana`
- `spencer`, `clyde`, `hugo`, `james`

### Languages
- `english`, `czech`, `danish`, `dutch`, `french`, `german`
- `greek`, `hindi`, `indonesian`, `italian`, `chinese`
- `japanese`, `norwegian`, `polish`, `portuguese`, `russian`
- `spanish`, `swedish`, `turkish`, `ukrainian`

### Caption Fonts
- `BakbakOne`, `Bangers`, `BebasNeue`, `Bungee`, `Caveat`
- `Creepster`, `Jua`, `Knewave`, `LuckiestGuy`, `Montserrat`
- `NotoSans`, `OpenSans`, `PermanentMarker`, `RampartOne`
- `Ranchers`, `TitanOne`

### Story Style Descriptors
- `dark`, `mysterious`, `uplifting`, `dramatic`, `whimsical`
- `melancholic`, `suspenseful`, `inspirational`, `nostalgic`
- `surreal`, `epic`, `intimate`, `energetic`, `calm`, `chaotic`

## 🖥️ Web Interface

The web interface provides a user-friendly way to generate videos without using the API directly.

### Features
- **Video Generation Form**: Create videos with guided inputs
- **Task Status Dashboard**: Monitor generation progress
- **Settings Panel**: Configure video parameters
- **LinkedIn Integration**: Post videos directly to LinkedIn
- **Image Regeneration**: Modify individual scenes

### Accessing the Interface
1. Start the server as described above
2. Open http://localhost:8000 in your web browser
3. Use the tabs to navigate between video generation and task status

## 🔄 Moving to Another Machine

### Option 1: Access Current Server (Recommended)
Your server is already network-accessible. Simply use:
- **URL**: http://192.168.12.199:8000
- **From any device on the same network**

### Option 2: Copy Frontend Files Only
For standalone frontend that connects to your backend:

1. **Create frontend files** with the content provided below
2. **Modify API endpoint** in `app.js`:
   ```javascript
   const API_BASE = 'http://192.168.12.199:8000'; // Change from localhost
   ```
3. **Open `index.html`** in a web browser

### Option 3: Full Project Copy
For complete functionality:

1. **Copy entire project folder** to target machine
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Run server**: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

## 📁 Project Structure

```
faceless-video-api/
├── app/
│   ├── api/
│   │   └── endpoints/
│   │       ├── auth.py
│   │       ├── video.py
│   │       └── video_clips.py
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   ├── security.py
│   │   └── __init__.py
│   ├── db/
│   │   ├── base.py
│   │   ├── init_db.py
│   │   ├── session.py
│   │   └── __init__.py
│   ├── models/
│   │   ├── image.py
│   │   ├── user.py
│   │   ├── video_task.py
│   │   └── video.py
│   ├── schemas/
│   │   ├── image.py
│   │   ├── token.py
│   │   └── video.py
│   ├── services/
│   │   ├── audio_generator.py
│   │   ├── image_api.py
│   │   ├── image_generator.py
│   │   ├── linkedin.py
│   │   ├── runware_video_sdk.py
│   │   ├── runware_video.py
│   │   ├── storage.py
│   │   ├── story_generator.py
│   │   ├── video_generator.py
│   │   └── video_task_processor.py
│   └── utils/
│       ├── helpers.py
│       ├── image_utils.py
│       └── transitions.py
├── static/
│   ├── index.html    # Web interface
│   ├── style.css     # Styling
│   └── app.js        # Frontend logic
├── assets/
├── data/
├── docs/
├── logs/
├── config.json       # Configuration
├── requirements.txt  # Dependencies
└── README.md         # This file
```

## 🔗 LinkedIn Integration

### Setup Requirements
1. **LinkedIn Developer Account**: https://developer.linkedin.com/
2. **LinkedIn App**: Create an app with UGC posts and OpenID Connect products
3. **Access Token**: Generate token with required scopes

### Configuration
Add to your `.env` file:
```
LINKEDIN_ACCESS_TOKEN=your_linkedin_access_token
LINKEDIN_MEMBER_URN=urn:li:person:your_member_id
```

### Posting Videos
Videos can be posted directly from the web interface or via API after generation completes.

## ⚙️ Advanced Configuration

### Video Settings
Configure output parameters in `config.json`:
- Resolution, FPS, zoom effects
- Caption styling and positioning
- Closing screen branding

### AI Prompts
Customize system prompts for:
- Character generation
- Video motion prompts
- Storyboard creation

### Product Mention Detection
Automatically detect product keywords and apply special image generation prompts.

## 🐛 Troubleshooting

### Common Issues

**Server won't start:**
- Ensure virtual environment is activated
- Check if port 8000 is available
- Verify all dependencies are installed

**Authentication fails:**
- Check username/password (default: admin/Tri2468!)
- Ensure token hasn't expired

**Video generation fails:**
- Check API keys in configuration
- Verify FFmpeg installation
- Check available disk space

**Network access issues:**
- Confirm firewall allows port 8000
- Check IP address is correct
- Ensure devices are on same network

### Logs
Check `logs/app.log` for detailed error information.

## 📄 Frontend Files

The web interface consists of three main files that can be used independently:

### `index.html`
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Faceless Video API - Control Panel</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>🎬 Dan's Faceless Video Generator</h1>
            <p>Control Panel</p>
        </header>

        <div class="tabs">
            <button class="tab-button active" onclick="switchTab('video')">Video Generation</button>
            <button class="tab-button" onclick="switchTab('status')">Task Status</button>
        </div>

        <!-- Video Generation Tab -->
        <div id="video-tab" class="tab-content active">
            <h2>Generate Video</h2>
            <form id="video-form">
                <div class="form-group full-width">
                    <label for="custom_story">Story Script (Required) *</label>
                    <textarea id="custom_story" name="custom_story" rows="8" required placeholder="Enter your story script here (minimum 100 characters)..."></textarea>
                    <small>Provide the complete story script for your video</small>
                </div>

                <div class="form-group full-width">
                    <label for="custom_title">Story Title (Optional)</label>
                    <input type="text" id="custom_title" name="custom_title" placeholder="Leave blank for default title">
                </div>

                <div class="form-group full-width">
                    <label for="tweak_prompt">Image Tweak Prompt (Optional)</label>
                    <textarea id="tweak_prompt" name="tweak_prompt" rows="3" placeholder="Add specific guidance to refine image generation (e.g., 'more vibrant colors', 'softer lighting', 'focus on facial expressions')..."></textarea>
                    <small>Provide additional instructions to fine-tune how images are generated</small>
                </div>

                <!-- Advanced Settings (collapsed by default) -->
                <details class="settings-section">
                    <summary>Advanced Settings</summary>
                    <div class="settings-content">
                        <p class="settings-intro">Configure video generation parameters, branding, and visual appearance.</p>

                        <!-- Settings content here -->
                        <div class="button-group">
                            <button type="button" class="btn btn-secondary" onclick="loadSettings()">🔄 Reload</button>
                            <button type="button" class="btn btn-primary" onclick="saveSettings()">💾 Save Settings</button>
                        </div>
                    </div>
                </details>

                <div class="form-grid">
                    <div class="form-group">
                        <label for="story_style_descriptor">Visual Tone (Optional)</label>
                        <select id="story_style_descriptor" name="story_style_descriptor">
                            <!-- Populated dynamically -->
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="art_style">Art Style *</label>
                        <select id="art_style" name="art_style" required>
                            <!-- Populated dynamically -->
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="voice_name">Voice *</label>
                        <select id="voice_name" name="voice_name" required>
                            <!-- Populated dynamically -->
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="language">Language *</label>
                        <select id="language" name="language" required>
                            <!-- Populated dynamically -->
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="caption_font">Caption Font *</label>
                        <select id="caption_font" name="caption_font" required>
                            <!-- Populated dynamically -->
                        </select>
                    </div>
                </div>

                <div class="button-group">
                    <button type="submit" class="btn btn-primary">🎬 Generate Video</button>
                    <button type="button" class="btn btn-secondary" onclick="clearForm()">Clear Form</button>
                </div>
            </form>

            <div id="video-result" class="result-box" style="display: none;">
                <h3>Generation Started!</h3>
                <p>Task ID: <strong id="task-id"></strong></p>
                <p>Status: <span id="task-status" class="status-badge">queued</span> <span id="video-link"></span></p>
                <div id="linkedin-post-section" style="display: none; margin-top: 15px;">
                    <div class="form-group">
                        <label for="linkedin-post-content">LinkedIn Post Content:</label>
                        <textarea id="linkedin-post-content" rows="3" placeholder="Write a caption for your LinkedIn post..." style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;"></textarea>
                    </div>
                    <button class="btn btn-linkedin" onclick="postToLinkedIn()" id="linkedin-post-btn">
                        <span class="linkedin-icon">in</span> Post to LinkedIn
                    </button>
                    <span id="linkedin-status-message" style="margin-left: 10px; display: none;"></span>
                </div>
                <button class="btn btn-secondary" onclick="checkTaskStatus()">Check Status</button>
            </div>
        </div>

        <!-- Task Status Tab -->
        <div id="status-tab" class="tab-content">
            <h2>Check Task Status</h2>

            <!-- Running Tasks Panel -->
            <div class="running-tasks-panel">
                <div class="panel-header">
                    <h3>🔄 Active Tasks</h3>
                    <button class="btn btn-secondary btn-small" onclick="refreshRunningTasks()">🔄 Refresh</button>
                </div>
                <div id="running-tasks-list" class="running-tasks-list">
                    <p class="loading-message">Loading tasks...</p>
                </div>
            </div>

            <!-- Completed Tasks Panel -->
            <div class="completed-tasks-panel">
                <div class="panel-header">
                    <h3>✅ Completed Tasks</h3>
                    <button class="btn btn-secondary btn-small" onclick="refreshRunningTasks()">🔄 Refresh</button>
                </div>
                <div id="completed-tasks-list" class="completed-tasks-list">
                    <p class="loading-message">Loading tasks...</p>
                </div>
            </div>

            <!-- Task Lookup -->
            <div class="task-lookup-section">
                <h3>Look up Task by ID</h3>
                <div class="form-group">
                    <label for="status_task_id">Task ID:</label>
                    <input type="text" id="status_task_id" placeholder="Enter task ID">
                    <button class="btn btn-primary" onclick="fetchTaskStatus()">Check Status</button>
                </div>
            </div>

            <div id="status-result" class="status-container"></div>
        </div>
    </div>

    <script src="app.js"></script>
</body>
</html>
```

### `style.css`
```css
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: Arial, Helvetica, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    padding: 20px;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    background: white;
    border-radius: 20px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    overflow: hidden;
}

header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 30px;
    text-align: center;
}

header h1 {
    font-size: 2.5em;
    margin-bottom: 10px;
}

header p {
    font-size: 1.1em;
    opacity: 0.9;
}

.tabs {
    display: flex;
    background: #f5f5f5;
    border-bottom: 2px solid #e0e0e0;
}

.tab-button {
    flex: 1;
    padding: 15px 20px;
    background: none;
    border: none;
    font-size: 1em;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s;
    color: #666;
}

.tab-button:hover {
    background: #e8e8e8;
}

.tab-button.active {
    background: white;
    color: #667eea;
    border-bottom: 3px solid #667eea;
}

.tab-content {
    display: none;
    padding: 30px;
    animation: fadeIn 0.3s;
}

.tab-content.active {
    display: block;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

h2 {
    color: #333;
    margin-bottom: 20px;
    font-size: 1.8em;
}

h3 {
    color: #667eea;
    margin: 20px 0 15px 0;
    font-size: 1.3em;
}

.form-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin-bottom: 20px;
}

.form-group {
    display: flex;
    flex-direction: column;
}

.form-group.full-width {
    width: 100%;
    margin-bottom: 20px;
}

label {
    font-weight: 600;
    margin-bottom: 8px;
    color: #555;
    font-size: 0.95em;
}

input[type="text"],
input[type="email"],
input[type="password"],
input[type="number"],
input[type="url"],
select,
textarea {
    padding: 12px;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    font-size: 1em;
    transition: all 0.3s;
    font-family: inherit;
}

input:focus,
select:focus,
textarea:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

textarea {
    resize: vertical;
    min-height: 100px;
}

.button-group {
    display: flex;
    gap: 10px;
    margin-top: 20px;
}

.btn {
    padding: 14px 28px;
    border: none;
    border-radius: 8px;
    font-size: 1em;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s;
    flex: 1;
}

.btn-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}

.btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
}

.btn-secondary {
    background: #f5f5f5;
    color: #666;
}

.btn-secondary:hover {
    background: #e0e0e0;
}

.btn-linkedin {
    background: #0077B5;
    color: white;
    display: inline-flex;
    align-items: center;
    gap: 8px;
}

.btn-linkedin:hover {
    background: #005885;
    transform: translateY(-2px);
    box-shadow: 0 10px 20px rgba(0, 119, 181, 0.3);
}

.linkedin-icon {
    background: white;
    color: #0077B5;
    font-weight: bold;
    font-size: 0.9em;
    padding: 2px 5px;
    border-radius: 3px;
}

.result-box {
    margin-top: 30px;
    padding: 20px;
    background: #f0f7ff;
    border-left: 4px solid #667eea;
    border-radius: 8px;
}

.result-box h3 {
    margin-top: 0;
    color: #667eea;
}

.status-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.9em;
    font-weight: 600;
    background: #ffd93d;
    color: #333;
}

.status-badge.completed {
    background: #4caf50;
    color: white;
}

.status-badge.processing {
    background: #2196f3;
    color: white;
}

.status-badge.failed {
    background: #f44336;
    color: white;
}

/* Additional CSS styles for settings, tasks, etc. would go here */
/* (Full CSS content is quite extensive - see the actual style.css file) */
```

### `app.js`
```javascript
// API Configuration
const API_BASE = 'http://localhost:8000';
let currentTaskId = null;
let accessToken = null;
let configOptions = null;
let statusPollingInterval = null;

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
    if (!configOptions) return;

    // Populate voices
    const voiceSelect = document.getElementById('voice_name');
    if (voiceSelect) {
        voiceSelect.innerHTML = configOptions.voices.map(v =>
            `<option value="${v.id}">${v.name}</option>`
        ).join('');
    }

    // Populate languages
    const languageSelect = document.getElementById('language');
    if (languageSelect) {
        languageSelect.innerHTML = configOptions.languages.map(lang =>
            `<option value="${lang}">${lang.charAt(0).toUpperCase() + lang.slice(1)}</option>`
        ).join('');
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
    }

    // Populate story style descriptors
    const styleDescriptorSelect = document.getElementById('story_style_descriptor');
    if (styleDescriptorSelect) {
        styleDescriptorSelect.innerHTML = '<option value="">None</option>' +
            configOptions.story_style_descriptors.map(desc =>
                `<option value="${desc}">${desc.charAt(0).toUpperCase() + desc.slice(1)}</option>`
            ).join('');
    }

    // Populate caption fonts
    const captionFontSelect = document.getElementById('caption_font');
    if (captionFontSelect) {
        captionFontSelect.innerHTML = configOptions.caption_fonts.map(font =>
            `<option value="${font}"${font === 'BebasNeue' ? ' selected' : ''}>${font}</option>`
        ).join('');
    }

    restoreFormValues();
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
        }
    } catch (error) {
        console.error('Auth error:', error);
    }
    return null;
}

// Video form submission
document.getElementById('video-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const token = await getAuthToken();
    if (!token) return;

    const formData = new FormData(e.target);
    const customStory = formData.get('custom_story');

    if (!customStory || customStory.trim().length < 100) {
        alert('Please provide a story script of at least 100 characters');
        return;
    }

    const data = {
        custom_story: customStory.trim(),
        art_style: formData.get('art_style'),
        voice_name: formData.get('voice_name'),
        language: formData.get('language'),
        caption_font: formData.get('caption_font')
    };

    // Add optional fields
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

// Tab switching
function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });

    document.getElementById(`${tabName}-tab`).classList.add('active');

    const buttons = document.querySelectorAll('.tab-button');
    buttons.forEach(btn => {
        if (btn.textContent.toLowerCase().includes(tabName)) {
            btn.classList.add('active');
        }
    });

    if (tabName === 'status') {
        refreshRunningTasks();
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadConfigOptions();
});

// Additional JavaScript functions would go here
// (Full JS content is extensive - see the actual app.js file)
```

## 📞 Support

For issues or questions:
1. Check the logs in `logs/app.log`
2. Verify your configuration in `config.json`
3. Ensure all dependencies are installed
4. Check network connectivity for API calls

## 📝 License

This project is proprietary. All rights reserved.

---

**Last Updated**: February 5, 2026
**Server IP**: 192.168.12.199
**Port**: 8000
  - Cinematic
  - Anime
  - Comic-book
  - Pixar-art
- Consistent character appearance across scenes

### Video Production
- Automated video compilation with subtitles
- Multi-language support:
  - English, Chinese, French, German
  - Spanish, Japanese, Russian
  - And many more...
- Multiple voice options:
  - Echo, Alloy, Onyx
  - Fable, Nova, Shimmer
- Customizable video duration (short/long)

### System Features
- RESTful API endpoints
- Token-based authentication
- PostgreSQL database
- Async processing with background tasks
- Progress tracking and status updates
- Error handling and recovery
- API rate limiting and monitoring

## Prerequisites

Before you begin, ensure you have the following installed on your machine:

### Required Software
- **Python 3.12+** - [Download Python](https://www.python.org/downloads/)
- **PostgreSQL 14+** - [Download PostgreSQL](https://www.postgresql.org/download/)
- **FFmpeg** - Required for video processing
  - **macOS**: `brew install ffmpeg`
  - **Ubuntu/Debian**: `sudo apt-get install ffmpeg`
  - **Windows**: [Download FFmpeg](https://ffmpeg.org/download.html)

### Required API Keys
You'll need accounts and API keys for the following services:

1. **OpenAI API** - For story generation and transcription
   - Sign up at [OpenAI Platform](https://platform.openai.com/)
   - Generate API key from [API Keys page](https://platform.openai.com/api-keys)

2. **Image Generation Service** (Choose one):
   - **FAL.ai** (Recommended) - [Get API key](https://fal.ai/)
   - **Replicate** (Alternative) - [Get API key](https://replicate.com/)
   - **Runware** (Alternative) - [Get API key](https://runware.ai/)

3. **Cartesia** - For text-to-speech
   - Sign up at [Cartesia](https://cartesia.ai/)

4. **Cloudflare R2** - For video storage
   - Create account at [Cloudflare](https://cloudflare.com/)
   - Set up R2 bucket in [Cloudflare Dashboard](https://dash.cloudflare.com/)

5. **PostgreSQL Database** - Either local or hosted
   - Local: Install PostgreSQL from link above
   - Hosted: [Supabase](https://supabase.com/), [Neon](https://neon.tech/), or [Railway](https://railway.app/)

## Quick Start Guide

### 1. Clone the Repository
```bash
git clone https://github.com/rushcreek/faceless-video-api.git
cd faceless-video-api
```

### 2. Create Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
Create a `.env` file in the project root:
```bash
cp .env.example .env
```

Then edit `.env` with your actual credentials (see [Environment Configuration](#environment-configuration) below).

### 5. Initialize Database
```bash
# Make sure PostgreSQL is running first!
python -m app.scripts.run_init_db
```
⚠️ **Warning**: This will drop all existing tables and recreate them. You'll be prompted for confirmation.

### 6. Run the Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Access the Application
Open your browser and navigate to:
- **Web UI**: http://localhost:8000/
- **API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## Environment Configuration

## Environment Configuration

Create a `.env` file in the project root with the following variables:

### Minimum Required Configuration
```bash
# OpenAI Configuration (Required)
OPENAI_API_KEY="sk-proj-***********************************"
OPENAI_BASE_URL="https://api.openai.com/v1"

# Image Generation - FAL.ai (Required - Choose one service)
FAL_KEY="********-****-****-****-************:********************************"

# OR use Replicate instead:
# REPLICATE_API_TOKEN="r8_********************************"

# OR use Runware instead:
# RUNWARE_API_KEY="********************************"

# Cartesia TTS (Required)
CARTESIA_API_KEY="********************************"

# Database (Required)
DATABASE_URL="postgresql://username:password@localhost:5432/faceless_db"

# JWT Secret (Required - generate a random string)
SECRET_KEY="your-secret-key-here-use-a-long-random-string"

# Admin User (Required)
ADMIN_USERNAME="admin"
ADMIN_EMAIL="admin@example.com"
ADMIN_PASSWORD="your-secure-password-here"

# Cloudflare R2 Storage (Required)
R2_BUCKET_NAME="your-bucket-name"
R2_ENDPOINT="https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com"
R2_PUBLIC_ENDPOINT="https://pub-YOUR_HASH.r2.dev"
R2_ACCESS_KEY_ID="your-r2-access-key-id"
R2_SECRET_ACCESS_KEY="your-r2-secret-access-key"
```

### Optional: Azure OpenAI Configuration
If you prefer to use Azure OpenAI instead of standard OpenAI:
```bash
# Azure OpenAI (Optional - instead of standard OpenAI)
AZURE_OPENAI_ENDPOINT="https://your-resource-name.openai.azure.com/"
AZURE_OPENAI_API_KEY="your-azure-openai-key"
# Also set "use_azure_openai": true in config.json
```

### Configuration Tips

1. **Generate a secure SECRET_KEY**:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Database URL Format**:
   - Local: `postgresql://username:password@localhost:5432/faceless_db`
   - Supabase: `postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`
   - Neon: Use the connection string from your Neon dashboard

3. **Cloudflare R2 Setup**:
   - Go to R2 in Cloudflare Dashboard
   - Create a new bucket
   - Generate API tokens in Account Settings → R2 API Tokens
   - Enable public access for the bucket (for video URLs)

## Database Setup

### Option 1: Local PostgreSQL

1. **Install PostgreSQL** (if not already installed)
   - macOS: `brew install postgresql`
   - Ubuntu: `sudo apt-get install postgresql`
   - Windows: Download from [PostgreSQL website](https://www.postgresql.org/download/)

2. **Start PostgreSQL**
   - macOS: `brew services start postgresql`
   - Ubuntu: `sudo systemctl start postgresql`
   - Windows: PostgreSQL should start automatically

3. **Create Database**
   ```bash
   # Using psql
   psql postgres
   CREATE DATABASE faceless_db;
   \q
   
   # OR using createdb command
   createdb faceless_db
   ```

4. **Update DATABASE_URL in .env**
   ```bash
   DATABASE_URL="postgresql://your_username:your_password@localhost:5432/faceless_db"
   ```

### Option 2: Hosted PostgreSQL (Supabase, Neon, Railway)

1. Create a new database in your hosting provider
2. Copy the connection string
3. Update DATABASE_URL in `.env` with the connection string
4. Ensure the database allows connections from your IP

### Initialize Database Tables

Required environment variables in `.env`:
```bash
# OpenAI Configuration (Default)
OPENAI_BASE_URL="your-openai-base-url"
OPENAI_API_KEY="sk-***********************************"

# Azure OpenAI Configuration (Optional)
# AZURE_OPENAI_ENDPOINT="https://your-azure-openai-endpoint/"
# AZURE_OPENAI_API_KEY="your-azure-openai-key"
# Note: To use Azure OpenAI, set "use_azure_openai": true in config.json

# AI Service Keys (Choose one)
# Option 1: FAL (Default)
FAL_KEY="********-****-****-****-************:********************************"
# Option 2: Replicate (Alternative)
# REPLICATE_API_TOKEN="r8_********************************"
# Note: To use Replicate, set "use_fal_flux": false in config.json

# Database Configuration
DATABASE_URL="your-postgresql-database-url"

# JWT Secret Key
SECRET_KEY="your-secret-key"

# Admin User Configuration
ADMIN_USERNAME="admin"
ADMIN_EMAIL="admin@example.com"
ADMIN_PASSWORD="cNv4wL8KuP3o%"

# Storage Configuration (Cloudflare R2)
R2_BUCKET_NAME="faceless-dev-1-videos"
R2_ENDPOINT="https://{hash}.r2.cloudflarestorage.com"
R2_PUBLIC_ENDPOINT="https://pub-{hash}.r2.dev"
R2_ACCESS_KEY_ID="your-r2-access-key-id"
R2_SECRET_ACCESS_KEY="your-r2-secret-access-key"
```

## Requirements

- Python 3.8+
- PostgreSQL database

## Installation

1. Clone the repository
```bash
git clone https://github.com/SmartClipAI/faceless-video-api
cd faceless-video-api
```

2. Create and activate virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Environment Configuration

Copy the environment template and configure the variables:
```bash
cp .env.example .env  # Linux/Mac
# or
copy .env.example .env  # Windows
```

## Database Setup

1. Ensure PostgreSQL is running

2. Create database
```bash
createdb faceless_db  # Using PostgreSQL CLI
```

3. Configure database connection
   Edit your `.env` file to set the database URL:
   ```bash
   DATABASE_URL=postgresql://username:password@localhost:5432/faceless_db
   ```
   Replace `username`, `password` with your PostgreSQL credentials.

4. Initialize database tables
```bash
# OpenAI Configuration (Default)
OPENAI_BASE_URL="your-openai-base-url"
OPENAI_API_KEY="sk-***********************************"

# Azure OpenAI Configuration (Optional)
# AZURE_OPENAI_ENDPOINT="https://your-azure-openai-endpoint/"
# AZURE_OPENAI_API_KEY="your-azure-openai-key"
# Note: To use Azure OpenAI, set "use_azure_openai": true in config.json

# AI Service Keys (Choose one)
# Option 1: FAL (Default)
FAL_KEY="********-****-****-****-************:********************************"
# Option 2: Replicate (Alternative)
# REPLICATE_API_TOKEN="r8_********************************"
# Note: To use Replicate, set "use_fal_flux": false in config.json

# Database Configuration
DATABASE_URL="your-postgresql-database-url"

# JWT Secret Key
SECRET_KEY="your-secret-key"

# Admin User Configuration
ADMIN_USERNAME="admin"
ADMIN_EMAIL="admin@example.com"
ADMIN_PASSWORD="cNv4wL8KuP3o%"

# Storage Configuration (Cloudflare R2)
R2_BUCKET_NAME="faceless-dev-1-videos"
R2_ENDPOINT="https://{hash}.r2.cloudflarestorage.com"
R2_PUBLIC_ENDPOINT="https://pub-{hash}.r2.dev"
R2_ACCESS_KEY_ID="your-r2-access-key-id"
R2_SECRET_ACCESS_KEY="your-r2-secret-access-key"
```

## Requirements

- Python 3.8+
- PostgreSQL database

## Installation

1. Clone the repository
```bash
git clone https://github.com/SmartClipAI/faceless-video-api
cd faceless-video-api
```

2. Create and activate virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Environment Configuration

Copy the environment template and configure the variables:
```bash
cp .env.example .env
```

## Database Setup

1. Ensure PostgreSQL is running

2. Create database
```bash
createdb faceless_db  # Using PostgreSQL CLI
```

3. Configure database connection
   Edit your `.env` file to set the database URL:
   ```bash
   DATABASE_URL=postgresql://username:password@localhost:5432/faceless_db
   ```
   Replace `username`, `password` with your PostgreSQL credentials.

4. Initialize database tables
### Initialize Database Tables

Run the initialization script to create all necessary tables:
```bash
python -m app.scripts.run_init_db
```

⚠️ **WARNING**: This command will:
- Drop all existing tables
- Delete all data in the database  
- Recreate all tables from scratch
- Create a default admin user with credentials from `.env`

You will be prompted for confirmation before the operation proceeds.

## Running the Service

### Development Mode (with auto-reload)
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using the Web Interface
Once the server is running, open your browser to:
- **http://localhost:8000/** - Main web interface for generating videos

### Verify Installation
1. Open http://localhost:8000/ in your browser
2. You should see the video generation interface
3. Try generating a test video with a short story

## API Documentation

After starting the service, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Authentication in Swagger UI

To test API endpoints in Swagger UI:

1. Click the green **"Authorize"** button at the top right
2. Enter your credentials:
   - **Username**: Your admin username (from `.env`, default: `admin`)
   - **Password**: Your admin password (from `.env`)
3. Click **"Authorize"** to save credentials
4. You can now test all protected endpoints

### Getting an Access Token (Alternative Method)

Use the `/v1/auth/token` endpoint:
1. Expand the **POST /v1/auth/token** endpoint in Swagger UI
2. Click "Try it out"
3. Fill in the form:
   - `grant_type`: `password`
   - `username`: your admin username
   - `password`: your admin password
4. Click "Execute"
5. Copy the `access_token` from the response
6. Use this token in the Authorization header: `Bearer <your-token>`

## Configuration Settings

## Configuration Settings

Edit `config.json` to customize application behavior:

```json
{
    "openai": {
      "model": "gpt-4o",           // AI model for story generation
      "temperature": 0.9           // Creativity (0.0-1.0, higher = more creative)
    },
    "tts": {
      "speech_rate": 1.1           // Narration speed (1.0 = normal)
    },
    "use_azure_openai": false,     // true = Azure OpenAI, false = standard OpenAI
    "use_fal_flux": true,          // true = FAL, false = Replicate
    "use_fal_flux_dev": false,     // true = flux-dev model, false = flux-schnell (faster)
    "use_runware_flux": false      // true = use Runware for image generation
}
```

### Image Generation Service Selection

Choose which service to use in `config.json`:

1. **FAL.ai Flux Schnell** (Default - Fast):
   ```json
   {
     "use_fal_flux": true,
     "use_fal_flux_dev": false,
     "use_runware_flux": false
   }
   ```

2. **FAL.ai Flux Dev** (Higher Quality):
   ```json
   {
     "use_fal_flux": true,
     "use_fal_flux_dev": true,
     "use_runware_flux": false
   }
   ```

3. **Runware** (Alternative):
   ```json
   {
     "use_runware_flux": true,
     "use_fal_flux": false
   }
   ```

4. **Replicate** (Alternative):
   ```json
   {
     "use_fal_flux": false,
     "use_runware_flux": false
   }
   ```

## Troubleshooting

### Common Issues

**1. Database Connection Error**
```
Error: could not connect to server
```
**Solution**:
- Ensure PostgreSQL is running: `brew services start postgresql` (macOS)
- Verify DATABASE_URL in `.env` is correct
- Check if database exists: `psql -l`

**2. FFmpeg Not Found**
```
Error: FFmpeg not found
```
**Solution**:
- Install FFmpeg: `brew install ffmpeg` (macOS) or see [Prerequisites](#prerequisites)
- Verify installation: `ffmpeg -version`

**3. OpenAI API Error**
```
Error: Incorrect API key provided
```
**Solution**:
- Verify OPENAI_API_KEY in `.env` is correct
- Check API key at https://platform.openai.com/api-keys
- Ensure you have credits in your OpenAI account

**4. Image Generation Fails**
```
Error: Failed to generate image
```
**Solution**:
- Verify FAL_KEY or REPLICATE_API_TOKEN in `.env`
- Check your API credits/balance
- Ensure correct service is selected in `config.json`

**5. Port Already in Use**
```
Error: Address already in use
```
**Solution**:
- Change port: `uvicorn app.main:app --reload --port 8001`
- Or kill process using port 8000: `lsof -ti:8000 | xargs kill`

**6. Module Import Errors**
```
ModuleNotFoundError: No module named 'X'
```
**Solution**:
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`
- Update pip: `pip install --upgrade pip`

**7. Video Generation Hangs**
**Solution**:
- Check logs in `logs/app.log`
- Verify all API keys are valid
- Ensure sufficient disk space for video files
- Check R2/storage credentials

### Getting Help

- **Logs**: Check `logs/app.log` for detailed error messages
- **GitHub Issues**: [Create an issue](https://github.com/rushcreek/faceless-video-api/issues)
- **API Errors**: Use Swagger UI at http://localhost:8000/docs to test endpoints

## Supported Fonts

## Supported Fonts

The application supports the following fonts for video captions:

- Titan One
- Ranchers
- Rampart One
- Permanent Marker
- Open Sans
- Noto Sans
- Montserrat
- Luckiest Guy
- Knewave
- Jua
- Creepster
- Caveat
- Bungee
- Bebas Neue (Default)
- Bangers
- Bakbak One

## License

[MIT License](LICENSE)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Submit a Pull Request

## Support

For issues and questions:
- Create a [GitHub Issue](https://github.com/rushcreek/faceless-video-api/issues)
- Check existing issues for solutions
- Review logs in `logs/app.log`

---

**Need help getting started?** Follow the [Quick Start Guide](#quick-start-guide) step-by-step, and you'll be generating videos in minutes!