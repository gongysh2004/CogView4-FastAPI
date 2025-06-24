#!/usr/bin/env python3
"""
Test script for gallery publish functionality with seed handling
"""

import requests
import json
import base64

def test_gallery_publish_with_seed():
    """Test publishing an image to gallery with proper seed handling"""
    base_url = "http://192.168.95.192:8000"
    
    print("🖼️ 测试Gallery发布功能 (包含Seed处理)")
    print("=" * 60)
    
    # 第一步：生成一张图片
    print("\n📝 第一步：生成图片")
    generation_data = {
        "prompt": "A beautiful sunset over mountains with golden clouds",
        "negative_prompt": "blurry, low quality, distorted",
        "size": "512x512",
        "n": 1,
        "guidance_scale": 5.0,
        "num_inference_steps": 10,
        "stream": False,
        "response_format": "b64_json"
        # 不指定seed，让系统自动生成
    }
    
    try:
        response = requests.post(
            f"{base_url}/v1/images/generations",
            json=generation_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 图片生成成功")
            print(f"返回的seed: {result['data'][0].get('seed')}")
            
            image_b64 = result['data'][0]['b64_json']
            generated_seed = result['data'][0].get('seed')
            
            if generated_seed is None:
                print("❌ 生成的图片没有seed")
                return
            else:
                print(f"✅ 图片生成成功，seed: {generated_seed}")
        else:
            print(f"❌ 图片生成失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ 图片生成失败: {e}")
        return
    
    # 第二步：发布到gallery
    print(f"\n📤 第二步：发布到Gallery")
    publish_data = {
        "image_data": image_b64,
        "prompt": generation_data["prompt"],
        "negative_prompt": generation_data["negative_prompt"],
        "size": generation_data["size"],
        "seed": generated_seed,  # 使用生成的seed
        "guidance_scale": generation_data["guidance_scale"],
        "num_inference_steps": generation_data["num_inference_steps"]
    }
    
    try:
        response = requests.post(
            f"{base_url}/v1/gallery/save",
            json=publish_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 发布成功")
            print(f"图片ID: {result['image_id']}")
            print(f"文件名: {result['filename']}")
            print(f"URL: {result['url']}")
        else:
            print(f"❌ 发布失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ 发布失败: {e}")
        return
    
    # 第三步：验证gallery中的seed
    print(f"\n🔍 第三步：验证Gallery中的Seed")
    try:
        response = requests.get(f"{base_url}/v1/gallery")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Gallery中有 {result['total_count']} 张图片")
            
            # 找到最新添加的图片
            latest_image = None
            for image in result['images']:
                if image['id'] == result['total_count']:  # 假设ID是连续的
                    latest_image = image
                    break
            
            if latest_image:
                print(f"最新图片: ID={latest_image['id']}")
                print(f"Seed: {latest_image['seed']}")
                print(f"Prompt: {latest_image['prompt'][:50]}...")
                
                if latest_image['seed'] == generated_seed:
                    print("✅ Seed验证成功！Gallery中保存的seed与生成的seed一致")
                elif latest_image['seed'] is None:
                    print("❌ Seed验证失败：Gallery中保存的seed为null")
                else:
                    print(f"❌ Seed验证失败：期望{generated_seed}，实际{latest_image['seed']}")
            else:
                print("❌ 未找到最新添加的图片")
        else:
            print(f"❌ 获取gallery失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 验证失败: {e}")

def test_gallery_publish_without_seed():
    """Test publishing an image to gallery without seed (should generate random seed)"""
    base_url = "http://192.168.95.192:8000"
    
    print(f"\n🖼️ 测试Gallery发布功能 (无Seed，应该生成随机Seed)")
    print("=" * 60)
    
    # 第一步：生成一张图片
    print("\n📝 第一步：生成图片")
    generation_data = {
        "prompt": "A magical forest with glowing mushrooms and fairy lights",
        "negative_prompt": "blurry, low quality, distorted",
        "size": "512x512",
        "n": 1,
        "guidance_scale": 5.0,
        "num_inference_steps": 10,
        "stream": False,
        "response_format": "b64_json"
    }
    
    try:
        response = requests.post(
            f"{base_url}/v1/images/generations",
            json=generation_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 图片生成成功")
            print(f"返回的seed: {result['data'][0].get('seed')}")
            
            image_b64 = result['data'][0]['b64_json']
            generated_seed = result['data'][0].get('seed')
            
            if generated_seed is None:
                print("❌ 生成的图片没有seed")
                return
            else:
                print(f"✅ 图片生成成功，seed: {generated_seed}")
        else:
            print(f"❌ 图片生成失败: {response.status_code}")
            return
            
    except Exception as e:
        print(f"❌ 图片生成失败: {e}")
        return
    
    # 第二步：发布到gallery（不传递seed，测试前端随机seed生成）
    print(f"\n📤 第二步：发布到Gallery (不传递seed)")
    publish_data = {
        "image_data": image_b64,
        "prompt": generation_data["prompt"],
        "negative_prompt": generation_data["negative_prompt"],
        "size": generation_data["size"],
        # 故意不传递seed，测试前端处理
        "guidance_scale": generation_data["guidance_scale"],
        "num_inference_steps": generation_data["num_inference_steps"]
    }
    
    try:
        response = requests.post(
            f"{base_url}/v1/gallery/save",
            json=publish_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 发布成功")
            print(f"图片ID: {result['image_id']}")
        else:
            print(f"❌ 发布失败: {response.status_code}")
            return
            
    except Exception as e:
        print(f"❌ 发布失败: {e}")
        return
    
    # 第三步：验证gallery中的seed
    print(f"\n🔍 第三步：验证Gallery中的Seed")
    try:
        response = requests.get(f"{base_url}/v1/gallery")
        
        if response.status_code == 200:
            result = response.json()
            
            # 找到最新添加的图片
            latest_image = None
            for image in result['images']:
                if image['id'] == result['total_count']:
                    latest_image = image
                    break
            
            if latest_image:
                print(f"最新图片: ID={latest_image['id']}")
                print(f"Gallery中的Seed: {latest_image['seed']}")
                print(f"原始生成的Seed: {generated_seed}")
                
                if latest_image['seed'] is None:
                    print("❌ Gallery中的seed为null")
                elif latest_image['seed'] == generated_seed:
                    print("✅ Gallery中的seed与生成的seed一致")
                else:
                    print(f"✅ Gallery中有seed: {latest_image['seed']} (可能被前端随机生成覆盖)")
            else:
                print("❌ 未找到最新添加的图片")
        else:
            print(f"❌ 获取gallery失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 验证失败: {e}")

def main():
    print("🎨 Gallery发布功能测试")
    print("=" * 80)
    
    # 测试1：有seed的发布
    test_gallery_publish_with_seed()
    
    # 测试2：无seed的发布
    test_gallery_publish_without_seed()
    
    print(f"\n📋 测试总结:")
    print(f"1. 测试了有seed的图片发布")
    print(f"2. 测试了无seed的图片发布")
    print(f"3. 验证了seed在gallery中的保存情况")
    print(f"4. 检查了前端随机seed生成功能")

if __name__ == "__main__":
    main() 