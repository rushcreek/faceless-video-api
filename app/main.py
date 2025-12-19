from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.endpoints import video, image, auth, admin, video_clips
from app.core.config import settings
from app.core.logging import setup_logging
import os

app = FastAPI(title=settings.PROJECT_NAME)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000", "http://0.0.0.0:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
app.include_router(video.router, prefix="/v1", tags=["video"])
app.include_router(image.router, prefix="/v1", tags=["image"])
app.include_router(admin.router, prefix="/v1/admin", tags=["admin"])
app.include_router(video_clips.router, prefix="/v1/video", tags=["video-clips"])

# Mount static files for the UI
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="ui")