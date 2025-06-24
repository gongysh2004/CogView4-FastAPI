#!/usr/bin/env python3
"""
Test script for prompt translation API
"""

import requests
import json

def test_translation_api():
    """Test the prompt translation API"""
    base_url = "http://192.168.95.192:8000"
    
    # 测试用例
    test_cases = [
        {
            "name": "English to Chinese",
            "prompt": "A beautiful sunset over a calm ocean with golden waves",
            "expected": "中文翻译"
        },
        {
            "name": "Chinese to English", 
            "prompt": "一只可爱的小猫坐在花园里，周围是五颜六色的花朵",
            "expected": "English translation"
        },
        {
            "name": "Complex English prompt",
            "prompt": "A futuristic cityscape with flying cars, neon lights, and towering skyscrapers reflecting in a cyberpunk aesthetic",
            "expected": "中文翻译"
        },
        {
            "name": "Complex Chinese prompt",
            "prompt": "一幅水墨画风格的山水画，远处有云雾缭绕的山峰，近处有清澈的溪流和古老的松树",
            "expected": "English translation"
        }
    ]
    
    print("🌐 测试Prompt翻译API")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 测试 {i}: {test_case['name']}")
        print(f"原始prompt: {test_case['prompt']}")
        
        try:
            # 发送翻译请求
            response = requests.post(
                f"{base_url}/v1/prompt/translate",
                json={
                    "prompt": test_case['prompt'],
                    "retry_times": 3
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result['success']:
                    print(f"✅ 翻译成功")
                    print(f"翻译结果: {result['translated_prompt']}")
                    print(f"响应时间: {response.elapsed.total_seconds():.2f}s")
                else:
                    print(f"❌ 翻译失败: {result['message']}")
                    
            else:
                print(f"❌ HTTP错误: {response.status_code}")
                print(f"错误信息: {response.text}")
                
        except Exception as e:
            print(f"❌ 请求失败: {e}")
    
    print(f"\n🎉 翻译API测试完成！")

def test_translation_with_optimization():
    """Test translation followed by optimization"""
    base_url = "http://192.168.95.192:8000"
    
    print(f"\n🔄 测试翻译+优化流程")
    print("=" * 50)
    
    original_prompt = "A beautiful anime girl with blue hair in a magical forest"
    print(f"原始prompt: {original_prompt}")
    
    try:
        # 第一步：翻译
        print(f"\n📝 第一步：翻译prompt...")
        translate_response = requests.post(
            f"{base_url}/v1/prompt/translate",
            json={
                "prompt": original_prompt,
                "retry_times": 3
            },
            headers={"Content-Type": "application/json"}
        )
        
        if translate_response.status_code == 200:
            translate_result = translate_response.json()
            
            if translate_result['success']:
                translated_prompt = translate_result['translated_prompt']
                print(f"✅ 翻译成功: {translated_prompt}")
                
                # 第二步：优化翻译后的prompt
                print(f"\n🤖 第二步：优化翻译后的prompt...")
                optimize_response = requests.post(
                    f"{base_url}/v1/prompt/optimize",
                    json={
                        "prompt": translated_prompt,
                        "retry_times": 3
                    },
                    headers={"Content-Type": "application/json"}
                )
                
                if optimize_response.status_code == 200:
                    optimize_result = optimize_response.json()
                    
                    if optimize_result['success']:
                        optimized_prompt = optimize_result['optimized_prompt']
                        print(f"✅ 优化成功: {optimized_prompt}")
                        
                        print(f"\n📊 流程总结:")
                        print(f"  原始: {original_prompt}")
                        print(f"  翻译: {translated_prompt}")
                        print(f"  优化: {optimized_prompt}")
                        
                    else:
                        print(f"❌ 优化失败: {optimize_result['message']}")
                else:
                    print(f"❌ 优化API错误: {optimize_response.status_code}")
                    
            else:
                print(f"❌ 翻译失败: {translate_result['message']}")
        else:
            print(f"❌ 翻译API错误: {translate_response.status_code}")
            
    except Exception as e:
        print(f"❌ 流程测试失败: {e}")

def main():
    print("🎨 Prompt翻译API测试套件")
    print("=" * 60)
    
    # 基础翻译测试
    test_translation_api()
    
    # 翻译+优化流程测试
    test_translation_with_optimization()
    
    print(f"\n📋 API端点信息:")
    print(f"  • POST /v1/prompt/translate - 翻译prompt")
    print(f"  • POST /v1/prompt/optimize - 优化prompt")
    print(f"  • 支持中英文互译")
    print(f"  • 自动语言检测")
    print(f"  • 可配置重试次数")

if __name__ == "__main__":
    main() 