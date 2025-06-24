#!/usr/bin/env python3
"""
Test script for the publish to gallery feature
"""

import requests
import json
import webbrowser
import os
import base64

def test_publish_api():
    """Test the publish to gallery API"""
    base_url = "http://192.168.95.192:8000"
    
    # 创建一个简单的测试图片（1x1像素的PNG）
    test_image_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    
    # 测试数据
    test_data = {
        "image_data": test_image_data,
        "prompt": "Test image for gallery publishing",
        "negative_prompt": "test, sample",
        "size": "512x512",
        "seed": 12345,
        "guidance_scale": 5.0,
        "num_inference_steps": 5
    }
    
    try:
        print("🧪 测试发布到图片走廊API...")
        response = requests.post(f"{base_url}/v1/gallery/save", json=test_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 发布API测试成功")
            print(f"📊 返回结果: {result}")
            
            # 验证返回的数据
            if result.get('success'):
                print(f"✅ 图片ID: {result.get('image_id')}")
                print(f"✅ 文件名: {result.get('filename')}")
                print(f"✅ 文件URL: {result.get('url')}")
                
                # 检查文件是否真的被创建
                file_path = f"static/images/{result.get('filename')}"
                if os.path.exists(file_path):
                    print(f"✅ 图片文件已创建: {file_path}")
                    
                    # 检查图片尺寸（如果PIL可用）
                    try:
                        from PIL import Image
                        with Image.open(file_path) as img:
                            width, height = img.size
                            print(f"✅ 图片尺寸: {width}x{height}")
                            
                            # 验证是否缩放到10%
                            expected_width = int(512 * 0.1)  # 51
                            expected_height = int(512 * 0.1)  # 51
                            
                            if width == expected_width and height == expected_height:
                                print(f"✅ 图片已正确缩放到10%: {width}x{height}")
                            else:
                                print(f"⚠️ 图片尺寸不符合预期: 期望 {expected_width}x{expected_height}, 实际 {width}x{height}")
                                
                    except ImportError:
                        print("⚠️ PIL不可用，无法验证图片尺寸")
                    except Exception as e:
                        print(f"⚠️ 无法读取图片尺寸: {e}")
                        
                else:
                    print(f"❌ 图片文件未找到: {file_path}")
                
                return True
            else:
                print(f"❌ API返回失败: {result}")
                return False
        else:
            print(f"❌ API响应异常: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 发布API测试失败: {e}")
        return False

def test_gallery_after_publish():
    """Test if the published image appears in gallery"""
    base_url = "http://192.168.95.192:8000"
    
    try:
        print("\n🔍 检查图片走廊中的新图片...")
        response = requests.get(f"{base_url}/v1/gallery")
        
        if response.status_code == 200:
            data = response.json()
            images = data['images']
            
            # 查找测试图片
            test_images = [img for img in images if "Test image for gallery publishing" in img['prompt']]
            
            if test_images:
                print(f"✅ 在图片走廊中找到 {len(test_images)} 张测试图片")
                for img in test_images:
                    print(f"  ID: {img['id']}")
                    print(f"  URL: {img['image_url']}")
                    print(f"  Prompt: {img['prompt']}")
                    print(f"  Size: {img['size']}")
                    print(f"  Seed: {img['seed']}")
                return True
            else:
                print("❌ 在图片走廊中未找到测试图片")
                return False
        else:
            print(f"❌ 获取图片走廊失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 检查图片走廊失败: {e}")
        return False

def check_json_file():
    """Check the gallery JSON file"""
    json_file_path = "static/images/gallery.json"
    
    print(f"\n📁 检查图片走廊JSON文件: {json_file_path}")
    
    if not os.path.exists(json_file_path):
        print(f"❌ JSON文件不存在: {json_file_path}")
        return False
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ JSON文件格式正确")
        print(f"📊 包含 {len(data.get('images', []))} 张图片")
        
        # 显示最新的几张图片
        images = data.get('images', [])
        if images:
            print(f"\n📋 最新图片:")
            for img in images[-3:]:  # 显示最后3张
                print(f"  ID {img['id']}: {img['prompt'][:50]}... ({img['size']})")
        
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
        print("\n📱 发布功能测试说明:")
        print("1. 在图片生成页面生成图片")
        print("2. 点击图片下方的'📤 发布到图片走廊'按钮")
        print("3. 图片会自动保存到 static/images/ 目录")
        print("4. 图片信息会自动添加到 gallery.json 文件")
        print("5. 在图片走廊中可以看到新发布的图片")
        
    except Exception as e:
        print(f"❌ 无法打开浏览器: {e}")

def main():
    print("🎨 发布到图片走廊功能测试")
    print("=" * 50)
    
    # 检查JSON文件
    if not check_json_file():
        print("❌ JSON文件检查失败")
        return
    
    # 测试发布API
    if not test_publish_api():
        print("❌ 发布API测试失败")
        return
    
    # 测试图片走廊更新
    if not test_gallery_after_publish():
        print("❌ 图片走廊更新测试失败")
        return
    
    # 打开图片走廊
    open_gallery()
    
    print("\n🎉 发布功能测试完成！")
    print("现在可以在图片生成页面测试发布功能了")

if __name__ == "__main__":
    main() 