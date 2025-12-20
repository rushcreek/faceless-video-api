"""
MoviePy configuration for ImageMagick
This file configures MoviePy to use the correct ImageMagick binary path
"""
import os

# Path to ImageMagick binary (magick.exe for ImageMagick 7+)
IMAGEMAGICK_BINARY = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"

# Verify the path exists
if not os.path.exists(IMAGEMAGICK_BINARY):
    print(f"WARNING: ImageMagick not found at {IMAGEMAGICK_BINARY}")
else:
    print(f"ImageMagick configured at: {IMAGEMAGICK_BINARY}")
