from moviepy.editor import *
import numpy as np
from PIL import Image
import cv2
import logging

logger = logging.getLogger(__name__)

def fade(clip, duration=1, type="both"):
    if type == "in":
        return clip.fadein(duration)
    elif type == "out":
        return clip.fadeout(duration)
    elif type == "both":
        return clip.fadein(duration).fadeout(duration)
    else:
        raise ValueError("type must be 'in', 'out', or 'both'")


def shake(clip, effect_duration=1, max_offset=5):
    def shake_effect(get_frame, t):
        frame = get_frame(t)

        # Only apply the effect during the specified duration
        if t < effect_duration:
            dx = np.random.randint(-max_offset, max_offset + 1)
            dy = np.random.randint(-max_offset, max_offset + 1)

            # Convert NumPy array to PIL Image
            pil_image = Image.fromarray(frame)

            # Create a new image with a black background
            result = Image.new("RGB", pil_image.size, (0, 0, 0))

            # Paste the original image with an offset
            result.paste(pil_image, (dx, dy))

            # Convert back to NumPy array
            return np.array(result)
        else:
            return frame

    return clip.fl(shake_effect)


def zoom(clip, mode="in", position="center", speed=1, min_duration=5.0, max_zoom_ratio=0.15):
    """
    Apply zoom effect with duration-based moderation.
    
    Args:
        clip: The video clip to apply zoom to
        mode: "in" or "out" for zoom direction
        position: Where to zoom from/to (center, left, right, etc.)
        speed: Base zoom speed multiplier (default: 1)
        min_duration: Duration threshold below which zoom is moderated (default: 5.0 seconds)
        max_zoom_ratio: Maximum zoom ratio for full-duration clips (default: 0.15 = 15% zoom)
    """
    if hasattr(clip, "fps") and clip.fps is not None and clip.fps > 1:
        fps = clip.fps
    else:
        # Default to 24 fps for ImageClips and clips without proper fps
        fps = 24

    duration = clip.duration
    total_frames = max(1, int(duration * fps))  # ensure at least 1 frame

    # Calculate zoom factor based on duration
    # Shorter clips get proportionally less zoom
    if duration < min_duration:
        # Scale zoom proportionally: 2s clip gets 40% of full zoom, 3s gets 60%, etc.
        duration_factor = duration / min_duration
        effective_zoom_ratio = max_zoom_ratio * duration_factor
    else:
        effective_zoom_ratio = max_zoom_ratio

    logger.info(f"🔍 Zoom effect: mode={mode}, fps={fps}, duration={duration:.2f}s, total_frames={total_frames}, effective_zoom_ratio={effective_zoom_ratio:.4f}")

    def main(getframe, t):
        frame = getframe(t)
        h, w = frame.shape[:2]
        
        # Validate frame dimensions
        if h == 0 or w == 0:
            return frame
        
        i = t * fps
        if mode == "out":
            i = total_frames - i
        
        # Use effective_zoom_ratio instead of hardcoded 0.1
        zoom = 1 + (i * ((effective_zoom_ratio * speed) / total_frames))
        
        # compute the extra zoom to avoid black bars
        extra_zoom = max(w / (w - 2), h / (h - 2))
        zoom *= extra_zoom
        
        # Ensure zoom factor is valid
        if zoom <= 0 or not np.isfinite(zoom):
            return frame

        positions = {
            "center": [(w - (w / zoom)) / 2, (h - (h / zoom)) / 2],
            "left": [0, (h - (h / zoom)) / 2],
            "right": [w - (w / zoom), (h - (h / zoom)) / 2],
            "top": [(w - (w / zoom)) / 2, 0],
            "topleft": [0, 0],
            "topright": [w - (w / zoom), 0],
            "bottom": [(w - (w / zoom)) / 2, h - (h / zoom)],
            "bottomleft": [0, h - (h / zoom)],
            "bottomright": [w - (w / zoom), h - (h / zoom)],
        }
        tx, ty = positions[position]
        
        # Ensure transformation matrix values are valid
        if not (np.isfinite(tx) and np.isfinite(ty)):
            return frame
        
        M = np.array([[zoom, 0, -tx * zoom], [0, zoom, -ty * zoom]])
        
        try:
            frame = cv2.warpAffine(frame, M, (w, h))
        except Exception as e:
            # If warpAffine fails, return original frame
            pass
            
        return frame

    return clip.fl(main)