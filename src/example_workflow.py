#!/usr/bin/env python3
"""
Example workflow: Optimize prompt then generate image
Demonstrates how to use the prompt optimization API to improve image generation results
"""

import requests
import json
import time
import base64
from PIL import Image
import io

# API server URL
BASE_URL = "http://localhost:8000"

def optimize_prompt(prompt: str, retry_times: int = 5) -> str:
    """Optimize a prompt using the API"""
    print(f"🔧 Optimizing prompt: '{prompt}'")
    
    payload = {
        "prompt": prompt,
        "retry_times": retry_times
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/v1/prompt/optimize",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                print(f"✅ Optimization successful!")
                print(f"📝 Original: {result['original_prompt']}")
                print(f"🚀 Optimized: {result['optimized_prompt']}")
                return result['optimized_prompt']
            else:
                print(f"❌ Optimization failed: {result['message']}")
                return prompt
        else:
            print(f"❌ API error: {response.status_code}")
            return prompt
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return prompt

def generate_image(prompt: str, save_path: str = None) -> bool:
    """Generate an image using the optimized prompt"""
    print(f"🎨 Generating image with prompt: '{prompt[:100]}...'")
    
    payload = {
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
        "guidance_scale": 5.0,
        "num_inference_steps": 50,
        "stream": False
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/v1/images/generations",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=120
        )
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            if result['data'] and len(result['data']) > 0:
                image_data = result['data'][0]
                if image_data['b64_json']:
                    print(f"✅ Image generated successfully! ({end_time - start_time:.2f}s)")
                    
                    # Save image if path provided
                    if save_path:
                        image_bytes = base64.b64decode(image_data['b64_json'])
                        image = Image.open(io.BytesIO(image_bytes))
                        image.save(save_path)
                        print(f"💾 Image saved to: {save_path}")
                    
                    return True
                else:
                    print("❌ No image data in response")
                    return False
            else:
                print("❌ No data in response")
                return False
        else:
            print(f"❌ Generation failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Generation request failed: {e}")
        return False

def workflow_example():
    """Complete workflow example: optimize prompt then generate image"""
    
    # Test cases
    test_cases = [
        {
            "name": "Simple Scene",
            "prompt": "a cat sitting on a chair",
            "output_file": "optimized_cat_chair.png"
        },
        {
            "name": "Chinese Scene", 
            "prompt": "一只可爱的小猫坐在椅子上",
            "output_file": "optimized_chinese_cat.png"
        },
        {
            "name": "Complex Scene",
            "prompt": "An anime girl with blue hair in a magical forest with glowing butterflies",
            "output_file": "optimized_anime_forest.png"
        }
    ]
    
    print("🚀 Prompt Optimization + Image Generation Workflow")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_case['name']}")
        print("-" * 40)
        
        # Step 1: Optimize the prompt
        optimized_prompt = optimize_prompt(test_case['prompt'])
        
        # Step 2: Generate image with optimized prompt
        success = generate_image(optimized_prompt, test_case['output_file'])
        
        if success:
            print(f"🎉 Workflow completed successfully for '{test_case['name']}'")
        else:
            print(f"❌ Workflow failed for '{test_case['name']}'")
        
        print("-" * 40)
    
    print("\n🏁 All workflows completed!")
    print("💡 Check the generated images to see the difference!")

def compare_original_vs_optimized():
    """Compare image generation with original vs optimized prompts"""
    
    original_prompt = "a beautiful sunset"
    
    print("🔍 Comparing Original vs Optimized Prompts")
    print("=" * 50)
    
    # Generate with original prompt
    print("\n📝 Step 1: Generate with original prompt")
    original_success = generate_image(original_prompt, "original_sunset.png")
    
    # Optimize prompt
    print("\n🔧 Step 2: Optimize the prompt")
    optimized_prompt = optimize_prompt(original_prompt)
    
    # Generate with optimized prompt
    print("\n🎨 Step 3: Generate with optimized prompt")
    optimized_success = generate_image(optimized_prompt, "optimized_sunset.png")
    
    if original_success and optimized_success:
        print("\n✅ Comparison completed!")
        print("📁 Check 'original_sunset.png' vs 'optimized_sunset.png'")
        print("💡 Notice the difference in detail and quality!")
    else:
        print("\n❌ Comparison failed - check the errors above")

if __name__ == "__main__":
    print("🎯 CogView4 Prompt Optimization Workflow Examples")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API server is running and healthy")
            
            # Run examples
            print("\n" + "=" * 60)
            workflow_example()
            
            print("\n" + "=" * 60)
            compare_original_vs_optimized()
            
        else:
            print(f"❌ API server returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to API server: {e}")
        print("\n💡 To start the server, run:")
        print("   python3 main.py")
        print("   or")
        print("   ./start_server.sh") 