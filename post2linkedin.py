"""
LinkedIn MCP Server - DEPRECATED

This standalone MCP server has been integrated into the main Faceless Video API.

The LinkedIn posting functionality is now available through:
- Backend: app/services/linkedin.py
- API Endpoint: POST /v1/video/tasks/{task_id}/post-to-linkedin
- Frontend: "Post to LinkedIn" button in the video status panel

Configuration:
Add these to your .env file:
- LINKEDIN_ACCESS_TOKEN: Your LinkedIn API access token
- LINKEDIN_MEMBER_URN: Your LinkedIn member URN (e.g., urn:li:person:XXXXXXXXXX)

To get your credentials:
1. Go to https://developer.linkedin.com/
2. Create an app with 'w_member_social' permission
3. Generate an access token
4. Get your Member URN from the /me endpoint

Original standalone MCP code is preserved below for reference.
"""

import requests
import json
import os
import mimetypes
from fastmcp import FastMCP

# =============================================================================
# LINKEDIN API CONFIGURATION - REPLACE WITH YOUR ACTUAL CREDENTIALS
# =============================================================================

# LinkedIn API Credentials (REPLACE WITH YOUR VALUES)
LINKEDIN_ACCESS_TOKEN = "YOUR_LINKEDIN_ACCESS_TOKEN_HERE"
LINKEDIN_MEMBER_URN = "urn:li:person:YOUR_MEMBER_ID_HERE"
LINKEDIN_API_BASE = "https://api.linkedin.com/v2"

def get_linkedin_headers():
    return {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json"
    }

def handle_linkedin_response(response):
    try:
        if response.status_code in [200, 201, 204]:
            return {"success": True, "data": response.json() if response.content else None}
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "message": response.text,
                "status_code": response.status_code
            }
    except Exception as e:
        return {"success": False, "error": "JSON Parse Error", "message": str(e)}

mcp = FastMCP(name="LinkedIn MCP Server", version="1.0.0")

# =============================================================================
# TOOLS SECTION - LinkedIn Actions
# =============================================================================

def register_upload(media_type: str, file_path: str) -> dict:
    """
    Register an upload with LinkedIn to get upload URL and asset URN.
    Step 1 of media upload process.
    
    Args:
        media_type: IMAGE, VIDEO, or DOCUMENT
        file_path: Path to the file to upload
        
    Returns:
        Dict with asset URN and upload URL
    """
    try:
        url = f"{LINKEDIN_API_BASE}/assets?action=registerUpload"
        headers = get_linkedin_headers()
        
        # Determine recipe based on media type
        if media_type.upper() == "IMAGE":
            recipe = "urn:li:digitalmediaRecipe:feedshare-image"
        elif media_type.upper() == "VIDEO":
            recipe = "urn:li:digitalmediaRecipe:feedshare-video"
        elif media_type.upper() == "DOCUMENT":
            recipe = "urn:li:digitalmediaRecipe:feedshare-document"
        else:
            return {"success": False, "error": f"Unsupported media type: {media_type}"}
        
        payload = {
            "registerUploadRequest": {
                "recipes": [recipe],
                "owner": LINKEDIN_MEMBER_URN,
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent"
                    }
                ],
                "supportedUploadMechanism": ["SYNCHRONOUS_UPLOAD"]
            }
        }
        
        print(f"Registering {media_type} upload...")
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code in [200, 201]:
            data = response.json()
            asset_urn = data["value"]["asset"]
            upload_url = data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
            return {
                "success": True,
                "asset": asset_urn,
                "uploadUrl": upload_url
            }
        else:
            return {
                "success": False,
                "error": f"Registration failed: HTTP {response.status_code}",
                "message": response.text
            }
    except Exception as e:
        return {"success": False, "error": f"Registration error: {str(e)}"}

def upload_media_binary(upload_url: str, file_path: str) -> dict:
    """
    Upload binary media file to LinkedIn.
    Step 2 of media upload process.
    
    Args:
        upload_url: Upload URL from registration
        file_path: Path to the file to upload
        
    Returns:
        Dict with success status
    """
    try:
        file_size = os.path.getsize(file_path)
        print(f"Uploading binary file: {file_path} (Size: {file_size} bytes)")
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"
        
        headers = {
            "Content-Type": mime_type,
            "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}"
        }
        
        with open(file_path, 'rb') as file:
            # Use a longer timeout for larger files, especially videos
            # 10 minutes (600s) for videos/documents, less for images
            if file_size > 50 * 1024 * 1024:  # >50MB
                timeout = 600  # 10 minutes
            elif file_size > 10 * 1024 * 1024:  # >10MB
                timeout = 300  # 5 minutes
            else:
                timeout = 120  # 2 minutes
            
            print(f"Uploading with timeout: {timeout}s ({timeout//60} minutes)")
            
            response = requests.put(upload_url, headers=headers, data=file, timeout=timeout)
            
        if response.status_code in [200, 201]:
            print("Binary upload successful!")
            return {"success": True, "message": "File uploaded successfully"}
        else:
            return {
                "success": False,
                "error": f"Upload failed: HTTP {response.status_code}",
                "message": response.text
            }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Upload timeout",
            "message": "The file upload took too long. Try a smaller file or check your connection."
        }
    except Exception as e:
        return {"success": False, "error": f"Upload error: {str(e)}"}

@mcp.tool
def create_post(content: str, media_type: str = "TEXT", file_path: str = None) -> dict:
    """
    Create a LinkedIn post with optional media (image, video, or document).
    
    Args:
        content: Text content of the post
        media_type: Type of media - "TEXT", "IMAGE", "VIDEO", or "DOCUMENT"
        file_path: Absolute path to media file (required for IMAGE/VIDEO/DOCUMENT)
    
    Returns:
        Dict with success status and post URN or error details
    
    Examples:
        - Text only: create_post("Hello LinkedIn!", "TEXT")
        - With image: create_post("Check this out!", "IMAGE", "C:/path/to/image.jpg")
        - With video: create_post("Watch this!", "VIDEO", "C:/path/to/video.mp4")
        - With document: create_post("Read my report", "DOCUMENT", "C:/path/to/doc.pdf")
    """
    # Strip whitespace from media_type to handle input errors
    media_type = media_type.strip().upper()
    print(f"Creating {media_type} post: {content[:50]}...")
    
    # Validate inputs
    if media_type not in ["TEXT", "IMAGE", "VIDEO", "DOCUMENT"]:
        return {
            "success": False,
            "error": f"Invalid media_type: {media_type}. Must be TEXT, IMAGE, VIDEO, or DOCUMENT"
        }
    
    if media_type != "TEXT" and not file_path:
        return {
            "success": False,
            "error": f"{media_type} posts require a file_path parameter"
        }
    
    if file_path and not os.path.exists(file_path):
        return {
            "success": False,
            "error": f"File not found: {file_path}"
        }
    
    # Step 1: Upload media if needed
    asset_urn = None
    if media_type != "TEXT":
        print(f"Step 1: Registering {media_type} upload...")
        register_result = register_upload(media_type, file_path)
        
        if not register_result["success"]:
            return register_result
        
        asset_urn = register_result["asset"]
        upload_url = register_result["uploadUrl"]
        
        print(f"Step 2: Uploading binary file...")
        upload_result = upload_media_binary(upload_url, file_path)
        
        if not upload_result["success"]:
            return upload_result
        
        print(f"Media uploaded successfully! Asset URN: {asset_urn}")
    
    # Step 2.5: For videos, wait a bit for processing
    if media_type == "VIDEO":
        import time
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        # Wait longer for larger videos
        wait_time = min(120, max(30, int(file_size_mb * 2)))  # 2 seconds per MB, 30-120 seconds
        print(f"Waiting for video processing ({wait_time} seconds)...")
        time.sleep(wait_time)
    
    # Step 3: Create the post
    url = f"{LINKEDIN_API_BASE}/ugcPosts"
    headers = get_linkedin_headers()
    
    # Build payload based on media type
    if media_type == "TEXT":
        payload = {
            "author": LINKEDIN_MEMBER_URN,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
    elif media_type == "IMAGE":
        payload = {
            "author": LINKEDIN_MEMBER_URN,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content},
                    "shareMediaCategory": "IMAGE",
                    "media": [
                        {
                            "status": "READY",
                            "media": asset_urn
                        }
                    ]
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
    elif media_type == "VIDEO":
        payload = {
            "author": LINKEDIN_MEMBER_URN,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content},
                    "shareMediaCategory": "VIDEO",
                    "media": [
                        {
                            "status": "READY",
                            "media": asset_urn
                        }
                    ]
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
    elif media_type == "DOCUMENT":
        payload = {
            "author": LINKEDIN_MEMBER_URN,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content},
                    "shareMediaCategory": "ARTICLE",
                    "media": [
                        {
                            "status": "READY",
                            "media": asset_urn
                        }
                    ]
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
    
    print(f"Step 4: Creating LinkedIn post...")
    # Use very long timeout for post creation with media (10 minutes for videos/documents)
    if media_type in ["VIDEO", "DOCUMENT"]:
        post_timeout = 600  # 10 minutes
    elif media_type == "IMAGE":
        post_timeout = 120  # 2 minutes
    else:
        post_timeout = 30  # 30 seconds for text
    
    print(f"Post creation timeout: {post_timeout}s ({post_timeout//60} minutes)")
    response = requests.post(url, headers=headers, json=payload, timeout=post_timeout)
    result = handle_linkedin_response(response)
    
    if result["success"]:
        print("Post created successfully!")
        if result.get("data"):
            post_urn = result["data"].get("id")
            if post_urn:
                result["post_urn"] = post_urn
        if asset_urn:
            result["asset_urn"] = asset_urn
    else:
        print(f"Post creation failed: {result.get('error', 'Unknown error')}")
    
    return result

@mcp.tool
def update_post(post_id: str, new_text: str) -> dict:
    """
    Update the text of a LinkedIn UGC post. Only works for UGC posts you created.
    """
    # Properly encode the URN for URL (replace : with %3A)
    if not post_id.startswith("urn:li:ugcPost:"):
        post_id = f"urn:li:ugcPost:{post_id}"
    encoded_post_id = post_id.replace(":", "%3A")
    url = f"{LINKEDIN_API_BASE}/ugcPosts/{encoded_post_id}"
    headers = get_linkedin_headers()
    payload = {
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": new_text}
            }
        }
    }
    response = requests.patch(url, headers=headers, json=payload)
    return handle_linkedin_response(response)

@mcp.tool
def delete_post(post_id: str) -> dict:
    """
    Delete a LinkedIn post. Handles both UGC and Share types.
    - For UGC posts: urn:li:ugcPost:{id}
    - For Shares: urn:li:share:{id}
    """
    if post_id.startswith("urn:li:ugcPost:"):
        encoded_post_id = post_id.replace(":", "%3A")
        url = f"{LINKEDIN_API_BASE}/ugcPosts/{encoded_post_id}"
    elif post_id.startswith("urn:li:share:"):
        encoded_post_id = post_id.replace(":", "%3A")
        url = f"{LINKEDIN_API_BASE}/shares/{encoded_post_id}"
    else:
        return {"success": False, "error": "Invalid post_id format. Must start with urn:li:ugcPost: or urn:li:share:"}
    headers = get_linkedin_headers()
    response = requests.delete(url, headers=headers)
    if response.status_code == 204:
        return {"success": True, "message": f"Post {post_id} deleted successfully"}
    else:
        return handle_linkedin_response(response)

# =============================================================================
# SERVER INITIALIZATION AND STARTUP
# =============================================================================

if __name__ == "__main__":
    print("LinkedIn MCP Server Starting...")
    print(f"API Base: {LINKEDIN_API_BASE}")
    print(f"Using Access Token: ...{LINKEDIN_ACCESS_TOKEN[-10:]}")
    print("="*60)
    print("MEDIA SUPPORT ENABLED:")
    print("  - TEXT posts (text only) - 30s timeout")
    print("  - IMAGE posts (jpg, png, gif) - 2 min timeout")
    print("  - VIDEO posts (mp4, mov, avi) - 10 min timeout")
    print("  - DOCUMENT posts (pdf, doc, docx, ppt, pptx) - 10 min timeout")
    print("="*60)
    print("NOTE: Large video/document uploads may take several minutes.")
    print("If timeout occurs but post appears on LinkedIn, upload succeeded!")
    print("="*60)
    print("Use create_post() with file_path parameter to upload media")
    mcp.run()