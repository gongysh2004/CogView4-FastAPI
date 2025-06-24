#!/usr/bin/env python3
"""
Test script for the prompt optimization API endpoint
"""

import requests
import json
import time

# API server URL
BASE_URL = "http://localhost:8000"

def test_prompt_optimization():
    """Test the prompt optimization API"""
    
    # Test cases with different types of prompts
    test_cases = [
        {
            "name": "Simple English prompt",
            "prompt": "a cat sitting on a chair",
            "retry_times": 3
        },
        {
            "name": "Chinese prompt",
            "prompt": "一只可爱的小猫坐在椅子上",
            "retry_times": 3
        },
        {
            "name": "Complex English prompt",
            "prompt": "An anime girl with blue hair in a magical forest with glowing butterflies",
            "retry_times": 5
        },
        {
            "name": "Complex Chinese prompt", 
            "prompt": "一个蓝头发的动漫女孩在魔法森林里，周围有发光的蝴蝶",
            "retry_times": 5
        }
    ]
    
    print("🧪 Testing Prompt Optimization API")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {test_case['name']}")
        print(f"Original prompt: {test_case['prompt']}")
        
        # Prepare request
        payload = {
            "prompt": test_case["prompt"],
            "retry_times": test_case["retry_times"]
        }
        
        try:
            # Make API call
            start_time = time.time()
            response = requests.post(
                f"{BASE_URL}/v1/prompt/optimize",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            end_time = time.time()
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success! ({end_time - start_time:.2f}s)")
                print(f"Optimized prompt: {result['optimized_prompt']}")
                print(f"Success: {result['success']}")
                print(f"Message: {result['message']}")
            else:
                print(f"❌ Error: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Testing completed!")

def test_api_health():
    """Test if the API server is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API server is running and healthy")
            return True
        else:
            print(f"❌ API server returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to API server: {e}")
        print("Make sure the server is running on http://localhost:8000")
        return False

if __name__ == "__main__":
    print("🚀 Prompt Optimization API Test")
    print("=" * 50)
    
    # Check if server is running
    if test_api_health():
        test_prompt_optimization()
    else:
        print("\n💡 To start the server, run:")
        print("   python main.py")
        print("   or")
        print("   ./start_server.sh") 