#!/usr/bin/env python3
"""
Test script for prompt batching optimization in CogView4 API
"""

import asyncio
import aiohttp
import time
import json
from typing import List

async def test_prompt_batching():
    """Test prompt batching by sending multiple requests with same parameters"""
    
    # Test prompts with same parameters but DIFFERENT negative prompts (should still be batched)
    test_cases = [
        {"prompt": "A futuristic city with flying cars", "negative_prompt": "blurry, low quality"},
        {"prompt": "A peaceful mountain landscape with a lake", "negative_prompt": "dark, gloomy"},
        {"prompt": "A bustling marketplace in medieval times", "negative_prompt": "modern, contemporary"},
        {"prompt": "An underwater coral reef with colorful fish", "negative_prompt": "black and white, monochrome"},
        {"prompt": "A space station orbiting Earth", "negative_prompt": "terrestrial, ground-based"},
        {"prompt": "A cozy cabin in a snowy forest", "negative_prompt": "urban, city"},
        {"prompt": "A desert oasis with palm trees", "negative_prompt": "cold, winter"},
        {"prompt": "A steampunk workshop with gears and machines", "negative_prompt": "minimalist, clean"}
    ]
    
    # Same parameters for all requests (except prompts and negative_prompts)
    common_params = {
        "size": "1024x1024",
        "guidance_scale": 7.5,
        "num_inference_steps": 10,
        "n": 1
    }
    
    print("🚀 Testing Prompt Batching Optimization")
    print(f"📝 Sending {len(test_cases)} requests with identical parameters but DIFFERENT negative prompts")
    print(f"⚙️  Parameters: {common_params}")
    print("🔗 Each prompt has its own negative prompt (should still batch together)")
    print()
    
    # Show prompt/negative_prompt pairs
    for i, case in enumerate(test_cases[:3]):  # Show first 3 as example
        print(f"   {i+1}. '{case['prompt'][:40]}...' | neg: '{case['negative_prompt'][:30]}...'")
    print(f"   ... and {len(test_cases)-3} more pairs")
    print()
    
    async def single_request(session: aiohttp.ClientSession, case: dict, idx: int):
        """Send a single request"""
        start_time = time.time()
        
        payload = {
            **case,
            **common_params
        }
        
        try:
            async with session.post(
                "http://localhost:8000/v1/images/generations",
                json=payload
            ) as response:
                result = await response.json()
                duration = time.time() - start_time
                
                if response.status == 200:
                    print(f"✅ Request {idx+1}: '{case['prompt'][:40]}...' completed in {duration:.2f}s")
                    return True, duration
                else:
                    print(f"❌ Request {idx+1}: Failed with status {response.status}")
                    return False, duration
                    
        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ Request {idx+1}: Error - {e}")
            return False, duration
    
    # Test concurrent requests (should trigger batching)
    print("🔄 Sending requests concurrently (should trigger batching)...")
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        tasks = [
            single_request(session, case, i) 
            for i, case in enumerate(test_cases)
        ]
        
        results = await asyncio.gather(*tasks)
    
    total_duration = time.time() - start_time
    successful = sum(1 for success, _ in results if success)
    
    print()
    print("📊 Results:")
    print(f"   Total requests: {len(test_cases)}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {len(test_cases) - successful}")
    print(f"   Total time: {total_duration:.2f}s")
    print(f"   Average time per request: {total_duration/len(test_cases):.2f}s")
    
    if successful > 0:
        individual_times = [duration for success, duration in results if success]
        avg_individual = sum(individual_times) / len(individual_times)
        print(f"   Average individual request time: {avg_individual:.2f}s")
    
    return results

async def test_streaming_batching():
    """Test streaming with batching"""
    print("\n🎥 Testing Streaming with Batching")
    
    prompts = [
        "A robot walking through a neon city",
        "A dragon flying over mountains",
        "A wizard casting spells in a library"
    ]
    
    async def stream_request(session: aiohttp.ClientSession, prompt: str, idx: int):
        """Send a streaming request"""
        payload = {
            "prompt": prompt,
            "stream": True,
            "size": "1024x1024",
            "guidance_scale": 7.5,
            "num_inference_steps": 10,
            "n": 1
        }
        
        print(f"🌊 Starting stream {idx+1}: '{prompt[:30]}...'")
        
        try:
            async with session.post(
                "http://localhost:8000/v1/images/generations",
                json=payload
            ) as response:
                
                steps_received = 0
                async for line in response.content:
                    if line.startswith(b'data: '):
                        data_str = line[6:].decode('utf-8').strip()
                        if data_str == '[DONE]':
                            break
                        
                        try:
                            data = json.loads(data_str)
                            if 'step' in data:
                                steps_received += 1
                                if steps_received % 5 == 0:  # Log every 5 steps
                                    print(f"   Stream {idx+1}: Step {data['step']}/{data.get('total_steps', '?')}")
                        except json.JSONDecodeError:
                            continue
                
                print(f"✅ Stream {idx+1} completed with {steps_received} steps")
                return True
                
        except Exception as e:
            print(f"❌ Stream {idx+1}: Error - {e}")
            return False
    
    # Send streaming requests concurrently
    async with aiohttp.ClientSession() as session:
        tasks = [
            stream_request(session, prompt, i) 
            for i, prompt in enumerate(prompts)
        ]
        
        results = await asyncio.gather(*tasks)
    
    successful = sum(results)
    print(f"📊 Streaming Results: {successful}/{len(prompts)} successful")

async def test_mixed_parameters():
    """Test requests with different parameters (should NOT be batched)"""
    print("\n🔀 Testing Mixed Parameters (should NOT batch)")
    
    requests = [
        {"prompt": "A sunset over the ocean", "size": "1024x1024", "guidance_scale": 7.5},
        {"prompt": "A forest in autumn", "size": "1024x1024", "guidance_scale": 8.0},  # Different guidance
        {"prompt": "A city at night", "size": "512x512", "guidance_scale": 7.5},  # Different size
        {"prompt": "A mountain peak", "size": "1024x1024", "guidance_scale": 7.5},  # Same as first
    ]
    
    print("📝 Sending requests with mixed parameters:")
    for i, req in enumerate(requests):
        print(f"   Request {i+1}: size={req['size']}, guidance={req['guidance_scale']}")
    
    async def mixed_request(session: aiohttp.ClientSession, req_data: dict, idx: int):
        """Send request with specific parameters"""
        payload = {
            "num_inference_steps": 10,
            "n": 1,
            **req_data
        }
        
        start_time = time.time()
        async with session.post(
            "http://localhost:8000/v1/images/generations",
            json=payload
        ) as response:
            duration = time.time() - start_time
            success = response.status == 200
            
            if success:
                print(f"✅ Mixed request {idx+1} completed in {duration:.2f}s")
            else:
                print(f"❌ Mixed request {idx+1} failed")
                
            return success, duration
    
    async with aiohttp.ClientSession() as session:
        tasks = [
            mixed_request(session, req, i) 
            for i, req in enumerate(requests)
        ]
        
        results = await asyncio.gather(*tasks)
    
    successful = sum(1 for success, _ in results if success)
    print(f"📊 Mixed Parameters Results: {successful}/{len(requests)} successful")

async def test_prompt_negative_prompt_pairing():
    """Test that prompts and negative prompts are correctly paired in batches"""
    print("\n🔗 Testing Prompt-Negative Prompt Pairing")
    
    # Test cases with specific prompt/negative_prompt pairs
    test_pairs = [
        {
            "prompt": "A beautiful sunset over mountains",
            "negative_prompt": "ugly, deformed",
            "expected_combination": "Beautiful sunset WITHOUT ugly/deformed elements"
        },
        {
            "prompt": "A cute cat playing with yarn",
            "negative_prompt": "dog, aggressive",
            "expected_combination": "Cute cat WITHOUT dog/aggressive elements"
        },
        {
            "prompt": "A modern kitchen with marble counters",
            "negative_prompt": "messy, cluttered",
            "expected_combination": "Modern kitchen WITHOUT messy/cluttered elements"
        }
    ]
    
    print("📝 Testing specific prompt-negative_prompt pairs:")
    for i, pair in enumerate(test_pairs):
        print(f"   {i+1}. Prompt: '{pair['prompt']}'")
        print(f"      Negative: '{pair['negative_prompt']}'")
        print(f"      Expected: {pair['expected_combination']}")
        print()
    
    # These should all be batched together since they have same generation parameters
    common_params = {
        "size": "1024x1024",
        "guidance_scale": 7.5,
        "num_inference_steps": 10,
        "n": 1
    }
    
    async def paired_request(session: aiohttp.ClientSession, pair: dict, idx: int):
        """Send a request with specific prompt/negative_prompt pair"""
        payload = {
            "prompt": pair["prompt"],
            "negative_prompt": pair["negative_prompt"],
            **common_params
        }
        
        start_time = time.time()
        try:
            async with session.post(
                "http://localhost:8000/v1/images/generations",
                json=payload
            ) as response:
                duration = time.time() - start_time
                success = response.status == 200
                
                if success:
                    print(f"✅ Pair {idx+1}: Generated in {duration:.2f}s")
                    print(f"   Prompt: '{pair['prompt'][:50]}...'")
                    print(f"   Negative: '{pair['negative_prompt']}'")
                else:
                    print(f"❌ Pair {idx+1}: Failed with status {response.status}")
                    
                return success, duration
                
        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ Pair {idx+1}: Error - {e}")
            return False, duration
    
    print("🔄 Sending paired requests concurrently...")
    print("💡 These should be batched together with proper prompt-negative_prompt pairing")
    
    async with aiohttp.ClientSession() as session:
        tasks = [
            paired_request(session, pair, i) 
            for i, pair in enumerate(test_pairs)
        ]
        
        results = await asyncio.gather(*tasks)
    
    successful = sum(1 for success, _ in results if success)
    print(f"\n📊 Pairing Results: {successful}/{len(test_pairs)} successful")
    
    if successful == len(test_pairs):
        print("✅ All prompt-negative_prompt pairs processed successfully!")
        print("🔍 Check server logs to confirm they were batched together")
    else:
        print("⚠️  Some pairs failed - check server logs for details")

async def test_num_images_batching():
    """Test that only requests with same num_images are batched together"""
    print("\n🔢 Testing num_images Batching Rules")
    
    # Test cases with different num_images values (using smaller values to avoid timeouts)
    test_cases = [
        {
            "name": "Single image requests (should batch together)",
            "requests": [
                {"prompt": "A mountain landscape", "n": 1, "guidance_scale": 7.5},
                {"prompt": "A forest scene", "n": 1, "guidance_scale": 7.5},  # Same n=1
                {"prompt": "A ocean view", "n": 1, "guidance_scale": 7.5},    # Same n=1
            ]
        },
        {
            "name": "Double image requests (should batch together)",
            "requests": [
                {"prompt": "A city skyline", "n": 2, "guidance_scale": 7.5},
                {"prompt": "A desert landscape", "n": 2, "guidance_scale": 7.5},  # Same n=2
            ]
        },
        {
            "name": "Mixed image counts (should NOT batch together)",
            "requests": [
                {"prompt": "A space station", "n": 1, "guidance_scale": 7.5},
                {"prompt": "A robot design", "n": 2, "guidance_scale": 7.5},  # Different n=2 (reduced from 3)
            ]
        }
    ]
    
    for case in test_cases:
        print(f"\n📝 {case['name']}:")
        for i, req in enumerate(case['requests']):
            print(f"   {i+1}. '{req['prompt']}' (n={req['n']})")
        
        # Add common parameters
        requests = []
        for req in case['requests']:
            full_req = {
                **req,
                "size": "512x512",  # Reduced size for faster processing
                "num_inference_steps": 10,
                "negative_prompt": "blurry, low quality"
            }
            requests.append(full_req)
        
        # Send requests concurrently with timeout
        async def send_case_request(session, req_data, idx):
            start_time = time.time()
            try:
                async with session.post(
                    "http://localhost:8000/v1/images/generations",
                    json=req_data
                ) as response:
                    duration = time.time() - start_time
                    success = response.status == 200
                    
                    if success:
                        result = await response.json()
                        num_images = len(result['data'])
                        print(f"   ✅ Request {idx+1}: {duration:.2f}s, got {num_images} images")
                    else:
                        error_text = await response.text()
                        print(f"   ❌ Request {idx+1}: Failed with status {response.status}")
                        print(f"      Error: {error_text[:100]}...")
                        
                    return success, duration
            except asyncio.TimeoutError:
                duration = time.time() - start_time
                print(f"   ❌ Request {idx+1}: Timeout after {duration:.2f}s")
                return False, duration
            except Exception as e:
                duration = time.time() - start_time
                print(f"   ❌ Request {idx+1}: Error - {e}")
                return False, duration
        
        print(f"🔄 Sending {len(requests)} requests...")
        
        # Use a timeout for the entire batch
        try:
            async with aiohttp.ClientSession() as session:
                tasks = [
                    send_case_request(session, req, i) 
                    for i, req in enumerate(requests)
                ]
                
                # Add timeout to the entire gather operation
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=600  # 10 minutes total timeout
                )
                
                # Handle exceptions in results
                successful = 0
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        print(f"   ❌ Request {i+1}: Exception - {result}")
                    elif isinstance(result, tuple) and len(result) == 2:
                        success, duration = result
                        if success:
                            successful += 1
                
        except asyncio.TimeoutError:
            print(f"   ❌ Batch timeout after 10 minutes")
            successful = 0
        except Exception as e:
            print(f"   ❌ Batch error: {e}")
            successful = 0
        
        print(f"📊 Case Result: {successful}/{len(requests)} successful")

async def main():
    """Run all tests"""
    print("🧪 CogView4 Prompt Batching Tests")
    print("=" * 50)
    
    # Check if server is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/health") as response:
                if response.status != 200:
                    print("❌ Server not responding. Make sure CogView4 API is running on port 8000")
                    return
                
                health_data = await response.json()
                print(f"✅ Server is healthy")
                print(f"   Workers: {health_data.get('active_workers', 'unknown')}")
                print(f"   Model loaded: {health_data.get('model_loaded', 'unknown')}")
                print()
    
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("   Make sure CogView4 API is running on port 8000")
        return
    
    # Run tests
    try:
        await test_prompt_batching()
        await test_streaming_batching()
        await test_mixed_parameters()
        await test_prompt_negative_prompt_pairing()
        await test_num_images_batching()
        
        print("\n🎉 All tests completed!")
        print("\n💡 Tips:")
        print("   - Check server logs to see batching in action")
        print("   - Set ENABLE_PROMPT_BATCHING=false to disable batching")
        print("   - Adjust batch_timeout and max_batch_size in WorkerPool")
        
    except Exception as e:
        print(f"\n❌ Test error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 