#!/usr/bin/env python3
"""
Test script for the equal-width column layout
"""

import requests
import json
import webbrowser

def test_gallery_api():
    """Test the gallery API and display layout info"""
    base_url = "http://192.168.95.192:8000"
    
    try:
        response = requests.get(f"{base_url}/v1/gallery")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 图片走廊API正常")
            print(f"📊 图片总数: {data['total_count']}")
            
            # 显示图片尺寸分布
            images = data['images']
            size_distribution = {}
            for img in images:
                size = img['size']
                if size not in size_distribution:
                    size_distribution[size] = 0
                size_distribution[size] += 1
            
            print(f"\n📏 图片尺寸分布:")
            for size, count in size_distribution.items():
                print(f"  {size}: {count} 张图片")
            
            # 显示4列布局的预期分布
            print(f"\n🎯 4列等宽布局分布:")
            for i in range(4):
                column_images = [j for j in range(len(images)) if j % 4 == i]
                print(f"  第{i+1}列: {len(column_images)} 张图片 (宽度: 25%)")
                if column_images:
                    sizes_in_column = [images[j]['size'] for j in column_images]
                    print(f"    包含图片: {[j+1 for j in column_images]}")
                    print(f"    尺寸类型: {list(set(sizes_in_column))}")
            
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
        print("\n📱 等宽布局测试说明:")
        print("1. 在大屏幕上应该看到4列等宽布局")
        print("2. 每列宽度应该完全相等 (25%)")
        print("3. 图片应该按照原始比例显示")
        print("4. 正方形图片(512x512, 1024x1024)保持1:1比例")
        print("5. 宽屏图片(912x512, 1280x720)保持16:9比例")
        print("6. 竖屏图片(512x912, 720x1280)保持9:16比例")
        print("7. 调整浏览器窗口大小测试响应式布局")
        
    except Exception as e:
        print(f"❌ 无法打开浏览器: {e}")

def main():
    print("🎨 图片走廊等宽布局测试")
    print("=" * 50)
    
    # 测试API
    if not test_gallery_api():
        print("❌ API测试失败，请确保服务器正在运行")
        return
    
    # 打开图片走廊
    open_gallery()
    
    print("\n🎉 测试完成！")
    print("请检查浏览器中的等宽布局效果")

if __name__ == "__main__":
    main() 