#!/usr/bin/env python3
"""
Test script for JSON-driven gallery functionality
"""

import requests
import json
import webbrowser
import os

def test_gallery_api():
    """Test the gallery API and display JSON data info"""
    base_url = "http://192.168.95.192:8000"
    
    try:
        response = requests.get(f"{base_url}/v1/gallery")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 图片走廊API正常")
            print(f"📊 图片总数: {data['total_count']}")
            
            # 显示图片信息
            images = data['images']
            print(f"\n📋 图片信息:")
            for i, img in enumerate(images):
                print(f"  图片 {i+1}:")
                print(f"    ID: {img['id']}")
                print(f"    URL: {img['image_url']}")
                print(f"    Prompt: {img['prompt'][:50]}...")
                print(f"    Size: {img['size']}")
                print(f"    Seed: {img['seed']}")
                print(f"    Timestamp: {img['timestamp']}")
                print()
            
            # 显示4列布局的预期分布
            print(f"🎯 4列等宽布局分布:")
            for i in range(4):
                column_images = [j for j in range(len(images)) if j % 4 == i]
                print(f"  第{i+1}列: {len(column_images)} 张图片 (宽度: 25%)")
                if column_images:
                    print(f"    包含图片: {[j+1 for j in column_images]}")
            
            return True
        else:
            print(f"❌ API响应异常: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ API测试失败: {e}")
        return False

def check_json_file():
    """Check if the JSON file exists and is valid"""
    json_file_path = "static/images/gallery.json"
    
    print(f"📁 检查JSON文件: {json_file_path}")
    
    if not os.path.exists(json_file_path):
        print(f"❌ JSON文件不存在: {json_file_path}")
        return False
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ JSON文件格式正确")
        print(f"📊 包含 {len(data.get('images', []))} 张图片")
        
        # 验证数据结构
        if 'images' not in data:
            print(f"❌ JSON文件缺少 'images' 键")
            return False
        
        # 验证每张图片的必要字段
        for i, img in enumerate(data['images']):
            required_fields = ['id', 'url', 'prompt', 'size']
            missing_fields = [field for field in required_fields if field not in img]
            if missing_fields:
                print(f"❌ 图片 {i+1} 缺少必要字段: {missing_fields}")
                return False
        
        print(f"✅ 所有图片数据格式正确")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON文件格式错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 读取JSON文件失败: {e}")
        return False

def open_gallery():
    """Open the gallery in browser"""
    try:
        print("\n🌐 正在打开图片走廊...")
        webbrowser.open("http://192.168.95.192:8000/gallery")
        print("✅ 图片走廊已在浏览器中打开")
        print("\n📱 JSON驱动Gallery测试说明:")
        print("1. 图片数据来自 static/images/gellery.json 文件")
        print("2. 图片URL指向 static/images/ 目录下的实际图片文件")
        print("3. 每张图片包含完整的生成参数信息")
        print("4. 4列等宽布局显示所有图片")
        print("5. 点击'生成同款'可以复制图片的生成参数")
        
    except Exception as e:
        print(f"❌ 无法打开浏览器: {e}")

def main():
    print("🎨 JSON驱动图片走廊测试")
    print("=" * 50)
    
    # 检查JSON文件
    if not check_json_file():
        print("❌ JSON文件检查失败")
        return
    
    # 测试API
    if not test_gallery_api():
        print("❌ API测试失败，请确保服务器正在运行")
        return
    
    # 打开图片走廊
    open_gallery()
    
    print("\n🎉 测试完成！")
    print("请检查浏览器中的JSON驱动Gallery效果")

if __name__ == "__main__":
    main() 