import asyncio
from app.services.runware_video_sdk import generate_video_from_image

async def main():
    image_url = "https://im.runware.ai/image/ws/2/ii/c9a0f823-e24b-418e-aa2b-c3d3c12426b5.jpg"
    prompt = "Slow pan across cityscape at dawn"
    
    print("Testing video generation...")
    result = await generate_video_from_image(image_url, prompt, duration=2, fps=24)
    
    if result:
        print(f"\nSUCCESS: {result}")
    else:
        print("\nFAILED")

asyncio.run(main())
