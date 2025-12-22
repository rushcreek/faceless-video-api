import asyncio
from app.models.image import Image

async def check_task_images(task_id):
    images = await Image.list_by_task(task_id)
    print(f"\n{'='*80}")
    print(f"Task ID: {task_id}")
    print(f"Total images in database: {len(images)}")
    print(f"{'='*80}\n")
    
    for img in images:
        url_info = f"{img.urls[0][:70]}..." if img.urls else "❌ NO URL"
        print(f"Scene {img.scene_number:2d}: {img.status:10s} | {url_info}")
    
    print(f"\n{'='*80}")
    print(f"Summary: {sum(1 for i in images if i.urls)} images with URLs, {sum(1 for i in images if not i.urls)} without URLs")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    task_id = "403438d8-4afd-41ce-a0b2-0ce3a908d3ab"
    asyncio.run(check_task_images(task_id))
