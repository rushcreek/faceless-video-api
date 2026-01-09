"""Test that image generation returns UUID which can be used for video generation"""
import asyncio
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from app.services.image_api import runware_flux_api

async def test_image_uuid():
    print("🧪 Testing image generation with UUID extraction...")
    
    # Generate a test image
    result = await runware_flux_api(
        task_id="test-uuid-extraction",
        prompt="A beautiful sunset over mountains, dramatic clouds, golden hour"
    )
    
    if result:
        print(f"\n✅ Image generated successfully!")
        print(f"   URL: {result.get('url')}")
        print(f"   Cost: ${result.get('cost', 'N/A')}")
        print(f"   UUID: {result.get('uuid')}")
        
        if result.get('uuid'):
            print(f"\n🎉 SUCCESS: UUID extracted! This can be used for video generation.")
            print(f"   The UUID '{result.get('uuid')}' will persist even after the URL expires.")
        else:
            print(f"\n⚠️ WARNING: No UUID returned. Check if Runware API returns imageUUID field.")
    else:
        print(f"\n❌ FAILED: No result from image generation")

if __name__ == "__main__":
    asyncio.run(test_image_uuid())
