#!/usr/bin/env python3
"""
Simple demo of prompt batching with proper prompt-negative_prompt pairing
"""

import asyncio
import aiohttp
import json

async def demo_batching():
    print("🎯 CogView4 Prompt Batching Demo")
    print("=" * 50)
    print()
    
    # Example: These requests will be BATCHED together
    requests = [
        {
            "prompt": "A dragon in mountains",
            "negative_prompt": "blurry, dark",
            "size": "1024x1024",
            "guidance_scale": 7.5,
            "num_inference_steps": 30,
            "n": 1
        },
        {
            "prompt": "A peaceful forest",
            "negative_prompt": "gloomy, urban",
            "size": "1024x1024",
            "guidance_scale": 7.5,
            "num_inference_steps": 30,
            "n": 1
        },
        {
            "prompt": "A space station",
            "negative_prompt": "old-fashioned, primitive",
            "size": "1024x1024",
            "guidance_scale": 7.5,
            "num_inference_steps": 30,
            "n": 1
        }
    ]
    
    print("📝 Sending 3 requests with identical generation parameters:")
    print("   • Size: 1024x1024")
    print("   • Guidance Scale: 7.5") 
    print("   • Inference Steps: 30")
    print("   • Images per request: 1")
    print()
    
    print("🔗 Each request has its own prompt-negative_prompt pair:")
    for i, req in enumerate(requests):
        print(f"   {i+1}. Prompt: '{req['prompt']}'")
        print(f"      Negative: '{req['negative_prompt']}'")
        print()
    
    print("💡 Expected behavior:")
    print("   ✅ All 3 requests should be BATCHED together")
    print("   ✅ Each prompt paired with its own negative_prompt")
    print("   ✅ Single inference call processes all 3 prompts")
    print("   ✅ GPU efficiency improved through batching")
    print()
    
    # Send requests concurrently
    async def send_request(session, req_data, idx):
        async with session.post(
            "http://localhost:8000/v1/images/generations",
            json=req_data
        ) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Request {idx+1} completed successfully")
                return True
            else:
                print(f"❌ Request {idx+1} failed with status {response.status}")
                return False
    
    print("🚀 Sending requests...")
    
    try:
        async with aiohttp.ClientSession() as session:
            tasks = [send_request(session, req, i) for i, req in enumerate(requests)]
            results = await asyncio.gather(*tasks)
        
        successful = sum(results)
        print()
        print(f"📊 Results: {successful}/{len(requests)} requests successful")
        
        if successful == len(requests):
            print()
            print("🎉 Demo completed successfully!")
            print("🔍 Check your server logs to see the batching in action")
            print("📜 Look for log messages like:")
            print("     'Submitted batch [batch_id] with 3 prompts'")
            print("     'Processing batched request [batch_id] with 3 prompts'")
        else:
            print("⚠️  Some requests failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure the CogView4 API server is running on port 8000")

async def check_server():
    """Check if server is running"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/health") as response:
                if response.status == 200:
                    health = await response.json()
                    print(f"✅ Server is healthy")
                    print(f"   Workers: {health.get('active_workers', 'unknown')}")
                    print(f"   Batching: {'enabled' if 'BatchManager' in str(health) else 'check logs'}")
                    return True
                else:
                    print("❌ Server unhealthy")
                    return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("💡 Start the server with: python cogview4_api_server.py")
        return False

async def main():
    print("🔍 Checking server status...")
    if await check_server():
        print()
        await demo_batching()
    else:
        print("\n💡 Please start the CogView4 API server first:")
        print("   cd CogView4-FastAPI")
        print("   python cogview4_api_server.py")

if __name__ == "__main__":
    asyncio.run(main()) 