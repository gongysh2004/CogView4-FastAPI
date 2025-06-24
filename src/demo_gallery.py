#!/usr/bin/env python3
"""
Demo script for the gallery functionality
"""

import webbrowser
import time
import requests

def check_server_status():
    """Check if the server is running"""
    try:
        response = requests.get("http://192.168.95.192:8000/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"✅ 服务器状态: {health['status']}")
            print(f"✅ 工作池状态: {'就绪' if health['workers_ready'] else '加载中'}")
            return True
        else:
            print(f"❌ 服务器响应异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接到服务器: {e}")
        return False

def test_gallery_api():
    """Test the gallery API"""
    try:
        response = requests.get("http://192.168.95.192:8000/v1/gallery")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 图片走廊API正常，包含 {data['total_count']} 张图片")
            return True
        else:
            print(f"❌ 图片走廊API异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 图片走廊API测试失败: {e}")
        return False

def open_gallery():
    """Open the gallery in browser"""
    try:
        print("🌐 正在打开图片走廊...")
        webbrowser.open("http://192.168.95.192:8000/gallery")
        print("✅ 图片走廊已在浏览器中打开")
    except Exception as e:
        print(f"❌ 无法打开浏览器: {e}")

def main():
    print("🎨 CogView4 图片走廊功能演示")
    print("=" * 50)
    
    # 检查服务器状态
    print("1. 检查服务器状态...")
    if not check_server_status():
        print("❌ 服务器未运行，请先启动服务器")
        print("   运行命令: python main.py")
        return
    
    # 测试图片走廊API
    print("\n2. 测试图片走廊API...")
    if not test_gallery_api():
        print("❌ 图片走廊API测试失败")
        return
    
    # 打开图片走廊
    print("\n3. 打开图片走廊...")
    open_gallery()
    
    print("\n🎉 演示完成！")
    print("\n使用说明:")
    print("- 在图片走廊中浏览图片")
    print("- 鼠标悬停查看详细信息")
    print("- 点击'生成同款'跳转到生成页面")
    print("- 参数会自动填充到生成表单中")

if __name__ == "__main__":
    main() 