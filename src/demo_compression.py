#!/usr/bin/env python3
"""
演示客户端图片压缩效果
"""

import base64
import os
from PIL import Image
import io

def create_demo_image():
    """创建一个演示图片"""
    # 创建一个渐变图片
    width, height = 512, 512
    img = Image.new('RGB', (width, height))
    
    # 创建渐变效果
    for x in range(width):
        for y in range(height):
            r = int((x / width) * 255)
            g = int((y / height) * 255)
            b = int(((x + y) / (width + height)) * 255)
            img.putpixel((x, y), (r, g, b))
    
    return img

def save_image_formats(img, base_name):
    """保存不同格式的图片"""
    results = {}
    
    # 保存为PNG（原始格式）
    png_path = f"{base_name}.png"
    img.save(png_path, 'PNG', optimize=True)
    png_size = os.path.getsize(png_path)
    results['PNG'] = png_size
    
    # 保存为不同质量的JPEG
    for quality in [90, 70, 50]:
        jpeg_path = f"{base_name}_q{quality}.jpg"
        img.save(jpeg_path, 'JPEG', quality=quality, optimize=True)
        jpeg_size = os.path.getsize(jpeg_path)
        results[f'JPEG Q{quality}'] = jpeg_size
    
    return results

def simulate_client_compression(img, max_width=400, quality=0.7):
    """模拟客户端压缩"""
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
    
    # 转换为JPEG
    buffer = io.BytesIO()
    compressed_img.save(buffer, format='JPEG', quality=int(quality * 100), optimize=True)
    compressed_data = buffer.getvalue()
    
    return compressed_img, len(compressed_data)

def simulate_server_resize(img, scale_factor=0.1):
    """模拟服务器端缩放"""
    width, height = img.size
    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)
    
    resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # 保存为JPEG
    buffer = io.BytesIO()
    resized_img.save(buffer, format='JPEG', quality=85, optimize=True)
    resized_data = buffer.getvalue()
    
    return resized_img, len(resized_data)

def main():
    print("🎨 客户端图片压缩效果演示")
    print("=" * 50)
    
    # 创建演示图片
    print("📸 创建演示图片...")
    demo_img = create_demo_image()
    original_size = demo_img.size
    
    # 保存不同格式
    print("\n📊 不同格式文件大小对比:")
    format_results = save_image_formats(demo_img, "demo_original")
    
    for format_name, size in format_results.items():
        print(f"  {format_name:<12}: {size:>8} bytes")
    
    # 模拟客户端压缩
    print(f"\n🔄 模拟客户端压缩 (最大宽度: 400px, 质量: 70%):")
    compressed_img, compressed_size = simulate_client_compression(demo_img)
    print(f"  原始尺寸: {original_size}")
    print(f"  压缩后尺寸: {compressed_img.size}")
    print(f"  压缩后大小: {compressed_size} bytes")
    
    # 计算压缩比
    original_png_size = format_results['PNG']
    client_compression_ratio = compressed_size / original_png_size * 100
    client_space_saved = (1 - compressed_size / original_png_size) * 100
    print(f"  客户端压缩比: {client_compression_ratio:.1f}%")
    print(f"  客户端节省空间: {client_space_saved:.1f}%")
    
    # 模拟服务器端缩放
    print(f"\n🖥️ 模拟服务器端缩放 (10%):")
    final_img, final_size = simulate_server_resize(compressed_img)
    print(f"  最终尺寸: {final_img.size}")
    print(f"  最终大小: {final_size} bytes")
    
    # 计算总压缩比
    total_compression_ratio = final_size / original_png_size * 100
    total_space_saved = (1 - final_size / original_png_size) * 100
    print(f"  总压缩比: {total_compression_ratio:.1f}%")
    print(f"  总节省空间: {total_space_saved:.1f}%")
    
    # 保存最终图片
    final_path = "demo_final.jpg"
    final_img.save(final_path, 'JPEG', quality=85, optimize=True)
    print(f"\n💾 最终图片已保存: {final_path}")
    
    # 显示文件大小对比
    print(f"\n📋 完整压缩流程对比:")
    print(f"  原始PNG:     {original_png_size:>8} bytes")
    print(f"  客户端压缩:  {compressed_size:>8} bytes (节省 {client_space_saved:.1f}%)")
    print(f"  服务器缩放:  {final_size:>8} bytes (节省 {total_space_saved:.1f}%)")
    
    # 清理临时文件
    print(f"\n🧹 清理临时文件...")
    try:
        if os.path.exists("demo_original.png"):
            os.remove("demo_original.png")
        for quality in [90, 70, 50]:
            jpeg_path = f"demo_original_q{quality}.jpg"
            if os.path.exists(jpeg_path):
                os.remove(jpeg_path)
    except Exception as e:
        print(f"  清理文件时出错: {e}")
    
    print(f"\n🎉 演示完成！")
    print(f"📊 总结:")
    print(f"  - 客户端压缩减少 {client_space_saved:.1f}% 传输数据")
    print(f"  - 服务器端缩放进一步减少存储空间")
    print(f"  - 双重压缩总共节省 {total_space_saved:.1f}% 空间")
    print(f"  - 最终图片质量仍然适合图片走廊展示")

if __name__ == "__main__":
    main() 