# Faceless Video API

A FastAPI-based service that powers automated video content creation through AI. Generate complete faceless videos from text input with AI-powered story generation, image creation, and video production.

---
> ## 🎬 Special Offer from FacelessVideos.app!
> 
> ### Create Professional Faceless Videos with AI - In One Click!
>
> ✨ **One-stop automated video creation platform:**
> - 🤖 Generate complete faceless videos from just text input
> - 🎨 Choose between Flux Schnell and Flux Dev AI models
> - 🎁 **Limited Time**: New users get 1000 FREE credits!
>
> [🚀 Start Creating Now →](https://facelessvideos.app/)
---

## Table of Contents
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick Start Guide](#quick-start-guide)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Running the Service](#running-the-service)
- [API Documentation](#api-documentation)
- [Configuration Settings](#configuration-settings)
- [Troubleshooting](#troubleshooting)

## Features

### Story Generation
- Rich story type support:
  - Scary Stories
  - Mystery Tales
  - Bedtime Stories
  - Interesting History
  - Urban Legends
  - Motivational Stories
  - Fun Facts
  - Long Form Jokes
  - Life Pro Tips
  - Philosophy
  - Love Stories
  - Custom Topics

### Image Generation
- AI-powered image creation from story scenes
- Multiple style options:
  - Photorealistic
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