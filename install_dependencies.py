#!/usr/bin/env python3
"""
Install dependencies for the CogView4 FastAPI project
"""

import subprocess
import sys
import os

def install_package(package):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ Successfully installed {package}")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Failed to install {package}")
        return False

def check_package(package):
    """Check if a package is installed"""
    try:
        __import__(package)
        print(f"✅ {package} is already installed")
        return True
    except ImportError:
        print(f"❌ {package} is not installed")
        return False

def main():
    print("🔧 Installing dependencies for CogView4 FastAPI")
    print("=" * 50)
    
    # 检查并安装PIL (Pillow)
    if not check_package("PIL"):
        print("\n📦 Installing Pillow for image processing...")
        if not install_package("Pillow==10.1.0"):
            print("⚠️ Warning: Pillow installation failed. Image resizing will be disabled.")
    
    # 检查并安装其他依赖
    dependencies = [
        "fastapi==0.104.1",
        "uvicorn==0.24.0", 
        "pydantic==2.5.0",
        "requests==2.31.0"
    ]
    
    print("\n📦 Installing other dependencies...")
    for dep in dependencies:
        package_name = dep.split("==")[0]
        if not check_package(package_name.lower()):
            install_package(dep)
    
    # 测试PIL功能
    print("\n🧪 Testing PIL functionality...")
    try:
        from PIL import Image
        print("✅ PIL is working correctly")
        
        # 创建一个测试图片
        test_img = Image.new('RGB', (100, 100), color='red')
        test_img.save('test_resize.png')
        
        # 测试缩放功能
        resized_img = test_img.resize((10, 10), Image.Resampling.LANCZOS)
        resized_img.save('test_resize_small.png')
        
        print("✅ Image resizing test passed")
        
        # 清理测试文件
        if os.path.exists('test_resize.png'):
            os.remove('test_resize.png')
        if os.path.exists('test_resize_small.png'):
            os.remove('test_resize_small.png')
            
    except ImportError:
        print("❌ PIL is not available")
    except Exception as e:
        print(f"❌ PIL test failed: {e}")
    
    print("\n🎉 Dependency installation completed!")
    print("\n📋 Summary:")
    print("- Pillow: For image resizing (10% scale)")
    print("- FastAPI: Web framework")
    print("- Uvicorn: ASGI server")
    print("- Pydantic: Data validation")
    print("- Requests: HTTP client")

if __name__ == "__main__":
    main() 