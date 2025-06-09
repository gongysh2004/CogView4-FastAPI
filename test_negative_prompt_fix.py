#!/usr/bin/env python3
"""
Test that None negative_prompt values are handled correctly in batch requests
"""

import asyncio
import aiohttp
import json

async def test_mixed_negative_prompts():
    """Test batching with mixed negative prompts including None values"""
    print("🧪 Testing Mixed Negative Prompts (including None)")
    
    # Test with some None negative prompts - should still batch together
    requests = [
        {
            "prompt": "A beautiful sunset",
            "negative_prompt": "ugly, blurry",  # Has negative prompt
            "size": "1024x1024",
            "guidance_scale": 7.5,
            "num_inference_steps": 25,
            "n": 1
        },
        {
            "prompt": "A peaceful forest",
            "negative_prompt": None,  # No negative prompt (None)
            "size": "1024x1024",
            "guidance_scale": 7.5,
            "num_inference_steps": 25,
            "n": 1
        }
    ]
    
    print("📝 Requests with mixed negative prompts:")
    for i, req in enumerate(requests):
        neg_prompt = req.get('negative_prompt', None)
        neg_display = f"'{neg_prompt}'" if neg_prompt else "None"
        print(f"   {i+1}. '{req['prompt']}' | negative: {neg_display}")
    
    print("\n💡 Expected: All should batch together despite different negative prompts")
    print("🔧 The fix should convert None values to empty strings for the tokenizer")
    
    async def send_test_request(session, req_data, idx):
        try:
            async with session.post(
                "http://localhost:8000/v1/images/generations",
                json=req_data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Request {idx+1}: Success - got {len(result['data'])} images")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Request {idx+1}: Failed with status {response.status}")
                    print(f"   Error: {error_text[:100]}...")
                    return False
        except Exception as e:
            print(f"❌ Request {idx+1}: Exception - {e}")
            return False
    
    print("\n🚀 Sending test requests...")
    
    async with aiohttp.ClientSession() as session:
        tasks = [
            send_test_request(session, req, i) 
            for i, req in enumerate(requests)
        ]
        
        results = await asyncio.gather(*tasks)
    
    successful = sum(results)
    print(f"\n📊 Results: {successful}/{len(requests)} successful")
    
    if successful == len(requests):
        print("🎉 All requests succeeded! The None negative_prompt fix is working!")
    else:
        print("⚠️  Some requests failed - check server logs for details")
    
    return successful == len(requests)

async def main():
    print("🔧 Testing None Negative Prompt Fix")
    print("=" * 40)
    
    try:
        # Check server
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/health") as response:
                if response.status != 200:
                    print("❌ Server not running on port 8000")
                    return
                print("✅ Server is running")
        
        success = await test_mixed_negative_prompts()
        
        if success:
            print("\n🎉 Fix verified! None negative prompts are handled correctly.")
        else:
            print("\n❌ Fix verification failed - check server logs.")
        
        print("\n💡 What to look for in server logs:")
        print("   - 'Submitted batch [id] with X prompts' (batching is working)")
        print("   - No 'ValueError: text input must be of type' errors")
        print("   - Successful processing of requests with None negative prompts")
        
    except Exception as e:
        print(f"❌ Test error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 