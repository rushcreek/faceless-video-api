from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
import os
from pathlib import Path

router = APIRouter()

class EnvSettings(BaseModel):
    CARTESIA_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_KEY: Optional[str] = None
    FAL_KEY: Optional[str] = None
    DATABASE_URL: Optional[str] = None
    SECRET_KEY: Optional[str] = None
    ADMIN_USERNAME: Optional[str] = None
    ADMIN_EMAIL: Optional[str] = None
    ADMIN_PASSWORD: Optional[str] = None
    R2_BUCKET_NAME: Optional[str] = None
    R2_ENDPOINT: Optional[str] = None
    R2_PUBLIC_ENDPOINT: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None

@router.get("/env")
async def get_env_settings() -> Dict[str, str]:
    """Get current .env settings (with sensitive values masked)"""
    env_file = Path(__file__).parent.parent.parent.parent / ".env"
    
    if not env_file.exists():
        raise HTTPException(status_code=404, detail=".env file not found")
    
    settings = {}
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"')
                
                # Mask sensitive values
                if any(sensitive in key.upper() for sensitive in ['KEY', 'PASSWORD', 'SECRET']):
                    if value:
                        settings[key] = value[:4] + '...' if len(value) > 4 else '***'
                else:
                    settings[key] = value
    
    return settings

@router.post("/env")
async def update_env_settings(settings: Dict[str, str]) -> Dict[str, str]:
    """Update .env file with new settings"""
    env_file = Path(__file__).parent.parent.parent.parent / ".env"
    
    if not env_file.exists():
        raise HTTPException(status_code=404, detail=".env file not found")
    
    # Read existing .env
    existing_lines = {}
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key = line.split('=', 1)[0].strip()
                existing_lines[key] = line
    
    # Update with new values
    for key, value in settings.items():
        if value:  # Only update non-empty values
            existing_lines[key] = f'{key}="{value}"'
    
    # Write back to .env
    with open(env_file, 'w') as f:
        f.write("#Cartesian Environment Variables\n")
        if "CARTESIA_API_KEY" in existing_lines:
            f.write(existing_lines["CARTESIA_API_KEY"] + "\n")
        
        f.write("\n# OpenAI Configuration (Default)\n")
        if "OPENAI_BASE_URL" in existing_lines:
            f.write(existing_lines["OPENAI_BASE_URL"] + "\n")
        if "OPENAI_API_KEY" in existing_lines:
            f.write(existing_lines["OPENAI_API_KEY"] + "\n")
        
        f.write("\n# Azure OpenAI Configuration (Optional)\n")
        f.write("# Uncomment and configure these if using Azure OpenAI\n")
        if "AZURE_OPENAI_ENDPOINT" in existing_lines:
            f.write("# " + existing_lines["AZURE_OPENAI_ENDPOINT"] + "\n")
        if "AZURE_OPENAI_API_KEY" in existing_lines:
            f.write("# " + existing_lines["AZURE_OPENAI_API_KEY"] + "\n")
        
        f.write("\n# AI Service Keys (Choose one)\n")
        f.write("# Option 1: FAL (Default)\n")
        if "FAL_KEY" in existing_lines:
            f.write(existing_lines["FAL_KEY"] + "\n")
        f.write("# Option 2: Replicate (Alternative)\n")
        if "REPLICATE_API_TOKEN" in existing_lines:
            f.write("# " + existing_lines["REPLICATE_API_TOKEN"] + "\n")
        
        f.write("\n# Database Configuration\n")
        f.write("# Format: postgresql://username:password@host:port/database_name\n")
        if "DATABASE_URL" in existing_lines:
            f.write(existing_lines["DATABASE_URL"] + "\n")
        
        f.write("\n# Authentication\n")
        f.write("# Generate a secure random string for SECRET_KEY\n")
        if "SECRET_KEY" in existing_lines:
            f.write(existing_lines["SECRET_KEY"] + "\n")
        
        f.write("\n# Admin User Configuration\n")
        if "ADMIN_USERNAME" in existing_lines:
            f.write(existing_lines["ADMIN_USERNAME"] + "\n")
        if "ADMIN_EMAIL" in existing_lines:
            f.write(existing_lines["ADMIN_EMAIL"] + "\n")
        if "ADMIN_PASSWORD" in existing_lines:
            f.write(existing_lines["ADMIN_PASSWORD"] + "\n")
        
        f.write("\n# Storage Configuration (Cloudflare R2)\n")
        if "R2_BUCKET_NAME" in existing_lines:
            f.write(existing_lines["R2_BUCKET_NAME"] + "\n")
        if "R2_ENDPOINT" in existing_lines:
            f.write(existing_lines["R2_ENDPOINT"] + "\n")
        if "R2_PUBLIC_ENDPOINT" in existing_lines:
            f.write(existing_lines["R2_PUBLIC_ENDPOINT"] + "\n")
        if "R2_ACCESS_KEY_ID" in existing_lines:
            f.write(existing_lines["R2_ACCESS_KEY_ID"] + "\n")
        if "R2_SECRET_ACCESS_KEY" in existing_lines:
            f.write(existing_lines["R2_SECRET_ACCESS_KEY"] + "\n")
    
    return {"message": "Settings updated successfully. Please restart the server for changes to take effect."}
