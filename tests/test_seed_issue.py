#!/usr/bin/env python3
"""
Test script to investigate the seed issue in image generation
"""

import requests
import json

def test_seed_generation():
    """Test seed generation and tracking"""
    base_url = "http://192.168.95.192:8000"
    
    print("🔍 测试Seed生成和跟踪问题")
    print("=" * 50)
    
    # 测试用例1：不指定seed
    print("\n📝 测试1: 不指定seed (应该自动生成)")
    test_data_1 = {
        "prompt": "A beautiful sunset over mountains",
        "negative_prompt": "blurry, low quality",
        "size": "512x512",
        "n": 1,
        "guidance_scale": 5.0,
        "num_inference_steps": 20,
        "stream": False,
        "response_format": "b64_json"
        # 注意：没有指定seed
    }
    
    try:
        response = requests.post(
            f"{base_url}/v1/images/generations",
            json=test_data_1,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 生成成功")
            print(f"返回的seed: {result['data'][0].get('seed')}")
            
            # 检查seed是否为null
            if result['data'][0].get('seed') is None:
                print("❌ 问题发现: seed为null")
            else:
                print(f"✅ seed正常: {result['data'][0]['seed']}")
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    # 测试用例2：指定seed
    print(f"\n📝 测试2: 指定seed")
    test_data_2 = {
        "prompt": "在这个迷人的梦幻般幻想场景中，一个来自ArtStation的超级可爱、流行的生物成为了焦点。这个生物以其蓬松可爱的外观散发出一种超凡脱俗的魅力，吸引了观众的目光。它在一种超现实的景观中嬉戏，这种景观模糊了现实与想象之间的界限，色彩鲜艳，形状奇异，唤起了人们的惊奇感。这个生物的眼睛闪烁着快乐，它柔软蓬松的毛发捕捉到光线，创造了一种发光的效果，增添了魔幻的氛围。这幅图像是可爱与超现实完美结合的产物，有望在艺术界成为病毒式热门。",
        "negative_prompt": "blurry, low quality",
        "size": "512x912",
        "n": 1,
        "guidance_scale": 5.0,
        "num_inference_steps": 20,
        "stream": False,
        "response_format": "b64_json",
        "seed": 12345  # 指定seed
    }
    
    try:
        response = requests.post(
            f"{base_url}/v1/images/generations",
            json=test_data_2,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 生成成功")
            print(f"返回的seed: {result['data'][0].get('seed')}")
            
            if result['data'][0].get('seed') == 12345:
                print("✅ seed正确返回: 12345")
            else:
                print(f"❌ seed不匹配: 期望12345, 实际{result['data'][0].get('seed')}")
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    # 测试用例3：流式生成
    print(f"\n📝 测试3: 流式生成 (不指定seed)")
    test_data_3 = {
        "prompt": "在这个迷人的梦幻般幻想场景中，一个来自ArtStation的超级可爱、流行的生物成为了焦点。这个生物以其蓬松可爱的外观散发出一种超凡脱俗的魅力，吸引了观众的目光。它在一种超现实的景观中嬉戏，这种景观模糊了现实与想象之间的界限，色彩鲜艳，形状奇异，唤起了人们的惊奇感。这个生物的眼睛闪烁着快乐，它柔软蓬松的毛发捕捉到光线，创造了一种发光的效果，增添了魔幻的氛围。这幅图像是可爱与超现实完美结合的产物，有望在艺术界成为病毒式热门。",
        "negative_prompt": "blurry, low quality",
        "size": "512x912",
        "n": 1,
        "guidance_scale": 5.0,
        "num_inference_steps": 20,
        "stream": True,
        "response_format": "b64_json"
        # 注意：没有指定seed
    }
    
    try:
        response = requests.post(
            f"{base_url}/v1/images/generations",
            json=test_data_3,
            headers={"Content-Type": "application/json"},
            stream=True
        )
        
        if response.status_code == 200:
            print(f"✅ 流式请求成功")
            print("正在接收流式数据...")
            
            seeds_found = []
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data = line_str[6:].strip()
                        if data == '[DONE]':
                            break
                        try:
                            result = json.loads(data)
                            if 'seed' in result and result['seed'] is not None:
                                seeds_found.append(result['seed'])
                                print(f"发现seed: {result['seed']}")
                        except json.JSONDecodeError:
                            continue
            
            if seeds_found:
                print(f"✅ 流式生成中发现 {len(seeds_found)} 个seed")
                print(f"Seed列表: {seeds_found}")
            else:
                print("❌ 流式生成中未发现seed")
        else:
            print(f"❌ 流式请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except Exception as e:
        print(f"❌ 流式测试失败: {e}")

def test_gallery_seed():
    """Test gallery seed saving"""
    base_url = "http://192.168.95.192:8000"
    
    print(f"\n🖼️ 测试Gallery Seed保存")
    print("=" * 50)
    
    # 检查当前gallery中的seed情况
    try:
        response = requests.get(f"{base_url}/v1/gallery")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Gallery中有 {result['total_count']} 张图片")
            
            for i, image in enumerate(result['images'], 1):
                print(f"图片 {i}: ID={image['id']}, Seed={image['seed']}")
                
                if image['seed'] is None:
                    print(f"  ❌ 图片 {image['id']} 的seed为null")
                else:
                    print(f"  ✅ 图片 {image['id']} 的seed正常: {image['seed']}")
        else:
            print(f"❌ 获取gallery失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Gallery测试失败: {e}")

def main():
    print("🎨 Seed问题调查测试")
    print("=" * 60)
    
    # 测试seed生成
    test_seed_generation()
    
    # 测试gallery seed保存
    test_gallery_seed()
    
    print(f"\n📋 问题分析:")
    print(f"1. 检查非流式生成是否正确返回seed")
    print(f"2. 检查流式生成是否正确传递seed")
    print(f"3. 检查gallery保存是否正确记录seed")
    print(f"4. 如果seed为null，可能是后端生成但未正确传递")

if __name__ == "__main__":
    main() 