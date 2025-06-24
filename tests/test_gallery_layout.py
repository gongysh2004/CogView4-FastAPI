#!/usr/bin/env python3
"""
Test script for the new 4-column gallery layout
"""

import requests
import json
import webbrowser
import time

def test_gallery_api():
    """Test the gallery API and display layout info"""
    base_url = "http://192.168.95.192:8000"
    
    try:
        response = requests.get(f"{base_url}/v1/gallery")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 图片走廊API正常")
            print(f"📊 图片总数: {data['total_count']}")
            
            # 显示图片分布信息
            images = data['images']
            print(f"📋 图片分布预览:")
            for i, img in enumerate(images):
                print(f"  图片 {i+1}: {img['prompt'][:50]}...")
            
            # 显示4列布局的预期分布
            print(f"\n🎯 4列布局分布:")
            for i in range(4):
                column_images = [j for j in range(len(images)) if j % 4 == i]
                print(f"  第{i+1}列: {len(column_images)} 张图片")
                if column_images:
                    print(f"    包含图片: {[j+1 for j in column_images]}")
            
            return True
        else:
            print(f"❌ API响应异常: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ API测试失败: {e}")
        return False

def open_gallery():
    """Open the gallery in browser"""
    try:
        print("\n🌐 正在打开图片走廊...")
        webbrowser.open("http://192.168.95.192:8000/gallery")
        print("✅ 图片走廊已在浏览器中打开")
        print("\n📱 测试说明:")
        print("1. 在大屏幕上应该看到4列布局")
        print("2. 每列中的图片垂直排列")
        print("3. 调整浏览器窗口大小测试响应式布局")
        print("4. 在中等屏幕上应该变成2列")
        print("5. 在小屏幕上应该变成1列")
        
    except Exception as e:
        print(f"❌ 无法打开浏览器: {e}")

def main():
    print("🎨 图片走廊4列布局测试")
    print("=" * 50)
    
    # 测试API
    if not test_gallery_api():
        print("❌ API测试失败，请确保服务器正在运行")
        return
    
    # 打开图片走廊
    open_gallery()
    
    print("\n🎉 测试完成！")
    print("请检查浏览器中的布局效果")

if __name__ == "__main__":
    main() 