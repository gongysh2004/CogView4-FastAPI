#!/usr/bin/env python3
"""
Test script for multiple image generation
"""

import requests
import json
import time

def test_non_streaming_multiple_images():
    """Test non-streaming multiple image generation"""
    print("Testing non-streaming multiple image generation...")
    
    url = "http://localhost:8000/v1/images/generations"
    data = {
        "prompt": "A cute cat sitting on a chair",
        "n": 3,  # Generate 3 images
        "size": "512x512",
        "stream": False,
        "num_inference_steps": 10,
        "guidance_scale": 5.0
    }
    
    start_time = time.time()
    response = requests.post(url, json=data)
    end_time = time.time()
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success! Generated {len(result['data'])} images in {end_time - start_time:.2f}s")
        for i, img_data in enumerate(result['data']):
            print(f"   Image {i+1}: {len(img_data['b64_json'])} bytes")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")

def test_streaming_multiple_images():
    """Test streaming multiple image generation"""
    print("\nTesting streaming multiple image generation...")
    
    url = "http://localhost:8000/v1/images/generations"
    data = {
        "prompt": "A beautiful landscape with mountains",
        "n": 2,  # Generate 2 images
        "size": "512x512", 
        "stream": True,
        "num_inference_steps": 10,
        "guidance_scale": 5.0
    }
    
    start_time = time.time()
    response = requests.post(url, json=data, stream=True)
    
    if response.status_code == 200:
        image_count = 0
        step_count = 0
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data_str = line[6:].strip()
                    if data_str == '[DONE]':
                        end_time = time.time()
                        print(f"✅ Streaming completed! Got {image_count} images, {step_count} steps in {end_time - start_time:.2f}s")
                        break
                    elif data_str:
                        try:
                            data = json.loads(data_str)
                            if 'image' in data and data.get('is_final', False):
                                image_count += 1
                                print(f"   Final image {image_count} received (step {data['step']}, image_index {data.get('image_index', 'N/A')})")
                            elif 'step' in data:
                                step_count += 1
                                img_info = f" (img {data.get('image_index', 0)+1}/{data.get('total_images', 1)})" if data.get('total_images', 1) > 1 else ""
                                print(f"   Step {data['step']}/{data.get('total_steps', 'N/A')}{img_info} - {data.get('progress', 0)*100:.1f}%")
                        except json.JSONDecodeError:
                            pass
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    print("Testing CogView4 Multiple Image Generation")
    print("=" * 50)
    
    # Test health first
    try:
        health_response = requests.get("http://localhost:8000/health")
        if health_response.status_code == 200:
            health = health_response.json()
            print(f"Server Status: {health.get('status', 'unknown')}")
            print(f"Model Loaded: {health.get('model_loaded', False)}")
            print(f"Active Workers: {health.get('active_workers', 0)}")
            print()
        else:
            print("❌ Server not responding")
            exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running on localhost:8000")
        exit(1)
    
    # Run tests
    test_non_streaming_multiple_images()
    test_streaming_multiple_images()
    
    print("\nTest completed!") 