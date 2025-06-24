#!/usr/bin/env python3
"""
Test script for client-side image compression feature
"""

import requests
import json
import webbrowser
import os
import base64
from PIL import Image
import io

def create_test_image(width=512, height=512):
    """Create a test image for compression testing"""
    # 创建一个彩色测试图片
    img = Image.new('RGB', (width, height), color='red')
    
    # 添加一些图案
    for i in range(0, width, 50):
        for j in range(0, height, 50):
            color = (i % 255, j % 255, (i + j) % 255)
            img.putpixel((i, j), color)
    
    # 转换为base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_data = buffer.getvalue()
    base64_data = base64.b64encode(img_data).decode('utf-8')
    
    return base64_data, len(img_data)

def test_client_compression_simulation():
    """Simulate client-side compression"""
    print("🧪 测试客户端图片压缩功能...")
    
    # 创建原始测试图片
    original_base64, original_size = create_test_image(512, 512)
    print(f"📊 原始图片大小: {original_size} bytes")
    
    # 模拟客户端压缩（这里用Python模拟，实际是在浏览器中）
    try:
        # 解码base64
        img_data = base64.b64decode(original_base64)
        img = Image.open(io.BytesIO(img_data))
        
        # 模拟客户端压缩：调整尺寸和质量
        max_width = 400  # 客户端最大宽度
        quality = 0.7    # JPEG质量
        
        # 计算新尺寸
        width, height = img.size
        if width > max_width:
            ratio = max_width / width
            new_width = max_width
            new_height = int(height * ratio)
        else:
            new_width, new_height = width, height
        
        # 压缩图片
        compressed_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 转换为JPEG并压缩
        buffer = io.BytesIO()
        compressed_img.save(buffer, format='JPEG', quality=int(quality * 100), optimize=True)
        compressed_data = buffer.getvalue()
        compressed_base64 = base64.b64encode(compressed_data).decode('utf-8')
        
        print(f"📊 压缩后尺寸: {new_width}x{new_height}")
        print(f"📊 压缩后大小: {len(compressed_data)} bytes")
        print(f"📊 压缩比例: {len(compressed_data) / original_size * 100:.1f}%")
        print(f"📊 节省空间: {(1 - len(compressed_data) / original_size) * 100:.1f}%")
        
        return compressed_base64, len(compressed_data)
        
    except Exception as e:
        print(f"❌ 压缩测试失败: {e}")
        return None, 0

def test_publish_with_compression():
    """Test publishing with compressed image"""
    base_url = "http://192.168.95.192:8000"
    
    # 获取压缩后的图片数据
    compressed_base64, compressed_size = test_client_compression_simulation()
    
    if not compressed_base64:
        print("❌ 无法获取压缩图片数据")
        return False
    
    # 测试数据
    test_data = {
        "image_data": compressed_base64,
        "prompt": "Client compressed test image",
        "negative_prompt": "test, compression",
        "size": "512x512",
        "seed": 12345,
        "guidance_scale": 5.0,
        "num_inference_steps": 5
    }
    
    try:
        print("\n📤 测试发布压缩图片...")
        response = requests.post(f"{base_url}/v1/gallery/save", json=test_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 发布成功")
            print(f"📊 返回结果: {result}")
            
            # 检查文件是否创建
            file_path = f"static/images/{result.get('filename')}"
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"✅ 文件已创建: {file_path}")
                print(f"📊 文件大小: {file_size} bytes")
                
                # 检查图片信息
                try:
                    with Image.open(file_path) as img:
                        print(f"📊 最终尺寸: {img.size}")
                        print(f"📊 最终格式: {img.format}")
                        
                        # 验证是否进一步缩放到10%
                        expected_width = int(400 * 0.1)  # 客户端压缩后的宽度再缩放到10%
                        expected_height = int(400 * 0.1)
                        
                        if img.size[0] == expected_width and img.size[1] == expected_height:
                            print(f"✅ 图片已正确缩放到10%: {img.size}")
                        else:
                            print(f"⚠️ 图片尺寸不符合预期: 期望 {expected_width}x{expected_height}, 实际 {img.size}")
                            
                except Exception as e:
                    print(f"⚠️ 无法读取图片信息: {e}")
                
                return True
            else:
                print(f"❌ 文件未找到: {file_path}")
                return False
        else:
            print(f"❌ 发布失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 发布测试失败: {e}")
        return False

def compare_compression_methods():
    """Compare different compression methods"""
    print("\n📊 压缩方法对比...")
    
    # 创建测试图片
    original_base64, original_size = create_test_image(512, 512)
    
    methods = [
        ("无压缩", original_base64, original_size),
    ]
    
    # 模拟不同压缩设置
    compression_settings = [
        (400, 0.9, "高质量压缩"),
        (400, 0.7, "中等质量压缩"),
        (400, 0.5, "低质量压缩"),
        (300, 0.7, "小尺寸压缩"),
    ]
    
    for max_width, quality, name in compression_settings:
        try:
            img_data = base64.b64encode(base64.b64decode(original_base64)).decode('utf-8')
            img = Image.open(io.BytesIO(base64.b64decode(img_data)))
            
            # 压缩
            width, height = img.size
            if width > max_width:
                ratio = max_width / width
                new_width = max_width
                new_height = int(height * ratio)
            else:
                new_width, new_height = width, height
            
            compressed_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            buffer = io.BytesIO()
            compressed_img.save(buffer, format='JPEG', quality=int(quality * 100), optimize=True)
            compressed_data = buffer.getvalue()
            compressed_base64 = base64.b64encode(compressed_data).decode('utf-8')
            
            methods.append((name, compressed_base64, len(compressed_data)))
            
        except Exception as e:
            print(f"❌ {name} 压缩失败: {e}")
    
    # 显示对比结果
    print(f"{'方法':<15} {'大小(bytes)':<12} {'压缩比':<10} {'节省空间':<10}")
    print("-" * 50)
    
    for name, base64_data, size in methods:
        compression_ratio = size / original_size * 100
        space_saved = (1 - size / original_size) * 100
        print(f"{name:<15} {size:<12} {compression_ratio:<10.1f}% {space_saved:<10.1f}%")

def main():
    print("🎨 客户端图片压缩功能测试")
    print("=" * 50)
    
    # 对比不同压缩方法
    compare_compression_methods()
    
    # 测试客户端压缩
    if test_client_compression_simulation():
        # 测试发布功能
        if test_publish_with_compression():
            print("\n🎉 客户端压缩功能测试完成！")
            print("\n📋 功能特点:")
            print("1. 客户端自动压缩图片到JPEG格式")
            print("2. 可配置压缩质量和最大尺寸")
            print("3. 大幅减少网络传输数据量")
            print("4. 服务器端进一步缩放到10%")
            print("5. 双重压缩显著节省存储空间")
        else:
            print("❌ 发布测试失败")
    else:
        print("❌ 客户端压缩测试失败")

if __name__ == "__main__":
    main() 