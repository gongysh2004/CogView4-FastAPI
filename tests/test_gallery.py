#!/usr/bin/env python3
"""
Test script for the gallery functionality
"""

import requests
import json

def test_gallery_api():
    """Test the gallery API endpoint"""
    base_url = "http://192.168.95.192:8000"
    
    try:
        # Test gallery API
        response = requests.get(f"{base_url}/v1/gallery")
        print(f"Gallery API Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Gallery Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            print(f"Number of images: {data.get('total_count', 0)}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Error testing gallery API: {e}")

def test_gallery_page():
    """Test the gallery page redirect"""
    base_url = "http://192.168.95.192:8000"
    
    try:
        response = requests.get(f"{base_url}/gallery", allow_redirects=False)
        print(f"Gallery page redirect status: {response.status_code}")
        print(f"Redirect location: {response.headers.get('location', 'None')}")
        
    except Exception as e:
        print(f"Error testing gallery page: {e}")

if __name__ == "__main__":
    print("Testing Gallery Functionality...")
    print("=" * 50)
    
    test_gallery_api()
    print()
    test_gallery_page() 