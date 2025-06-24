#!/usr/bin/env python3
"""
Gallery Manager - 图片走廊管理工具
用于管理 static/images/gellery.json 文件中的图片数据
"""

import json
import os
import time
from typing import List, Dict, Optional

class GalleryManager:
    def __init__(self, json_file_path: str = "static/images/gallery.json"):
        self.json_file_path = json_file_path
        self.ensure_file_exists()
    
    def ensure_file_exists(self):
        """确保JSON文件存在，如果不存在则创建"""
        if not os.path.exists(self.json_file_path):
            os.makedirs(os.path.dirname(self.json_file_path), exist_ok=True)
            self.save_gallery({"images": []})
            print(f"✅ 创建新的图片走廊文件: {self.json_file_path}")
    
    def load_gallery(self) -> Dict:
        """加载图片走廊数据"""
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载图片走廊文件失败: {e}")
            return {"images": []}
    
    def save_gallery(self, data: Dict):
        """保存图片走廊数据"""
        try:
            with open(self.json_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"✅ 保存图片走廊数据成功")
        except Exception as e:
            print(f"❌ 保存图片走廊文件失败: {e}")
    
    def get_next_id(self) -> int:
        """获取下一个可用的ID"""
        data = self.load_gallery()
        if not data.get('images'):
            return 1
        return max(img['id'] for img in data['images']) + 1
    
    def add_image(self, image_data: Dict) -> bool:
        """添加新图片"""
        try:
            data = self.load_gallery()
            
            # 验证必需字段
            required_fields = ['url', 'prompt', 'size']
            for field in required_fields:
                if field not in image_data:
                    print(f"❌ 缺少必需字段: {field}")
                    return False
            
            # 设置默认值
            new_image = {
                'id': self.get_next_id(),
                'url': image_data['url'],
                'prompt': image_data['prompt'],
                'negative_prompt': image_data.get('negative_prompt', ''),
                'size': image_data['size'],
                'seed': image_data.get('seed', 12345),
                'timestamp': image_data.get('timestamp', time.time()),
                'guidance_scale': image_data.get('guidance_scale', 5.0),
                'num_inference_steps': image_data.get('num_inference_steps', 20)
            }
            
            data['images'].append(new_image)
            self.save_gallery(data)
            
            print(f"✅ 添加图片成功: ID {new_image['id']}")
            return True
            
        except Exception as e:
            print(f"❌ 添加图片失败: {e}")
            return False
    
    def remove_image(self, image_id: int) -> bool:
        """删除图片"""
        try:
            data = self.load_gallery()
            
            # 查找并删除图片
            original_count = len(data['images'])
            data['images'] = [img for img in data['images'] if img['id'] != image_id]
            
            if len(data['images']) == original_count:
                print(f"❌ 未找到ID为 {image_id} 的图片")
                return False
            
            self.save_gallery(data)
            print(f"✅ 删除图片成功: ID {image_id}")
            return True
            
        except Exception as e:
            print(f"❌ 删除图片失败: {e}")
            return False
    
    def update_image(self, image_id: int, updates: Dict) -> bool:
        """更新图片信息"""
        try:
            data = self.load_gallery()
            
            # 查找图片
            for img in data['images']:
                if img['id'] == image_id:
                    # 更新字段
                    for key, value in updates.items():
                        if key in img:
                            img[key] = value
                    
                    self.save_gallery(data)
                    print(f"✅ 更新图片成功: ID {image_id}")
                    return True
            
            print(f"❌ 未找到ID为 {image_id} 的图片")
            return False
            
        except Exception as e:
            print(f"❌ 更新图片失败: {e}")
            return False
    
    def list_images(self) -> List[Dict]:
        """列出所有图片"""
        data = self.load_gallery()
        return data.get('images', [])
    
    def get_image(self, image_id: int) -> Optional[Dict]:
        """获取指定图片"""
        data = self.load_gallery()
        for img in data['images']:
            if img['id'] == image_id:
                return img
        return None
    
    def search_images(self, keyword: str) -> List[Dict]:
        """搜索图片"""
        data = self.load_gallery()
        results = []
        keyword_lower = keyword.lower()
        
        for img in data['images']:
            if (keyword_lower in img['prompt'].lower() or 
                keyword_lower in img.get('negative_prompt', '').lower()):
                results.append(img)
        
        return results
    
    def validate_image_files(self) -> List[str]:
        """验证图片文件是否存在"""
        data = self.load_gallery()
        missing_files = []
        
        for img in data['images']:
            file_path = img['url'].lstrip('/')
            if not os.path.exists(file_path):
                missing_files.append(f"ID {img['id']}: {img['url']}")
        
        return missing_files

def main():
    """主函数 - 提供交互式管理界面"""
    manager = GalleryManager()
    
    print("🎨 图片走廊管理工具")
    print("=" * 50)
    
    while True:
        print("\n请选择操作:")
        print("1. 查看所有图片")
        print("2. 添加新图片")
        print("3. 删除图片")
        print("4. 更新图片")
        print("5. 搜索图片")
        print("6. 验证图片文件")
        print("0. 退出")
        
        choice = input("\n请输入选择 (0-6): ").strip()
        
        if choice == '0':
            print("👋 再见！")
            break
        
        elif choice == '1':
            images = manager.list_images()
            if not images:
                print("📭 暂无图片")
            else:
                print(f"\n📋 共 {len(images)} 张图片:")
                for img in images:
                    print(f"  ID {img['id']}: {img['prompt'][:50]}... ({img['size']})")
        
        elif choice == '2':
            print("\n📝 添加新图片:")
            url = input("图片URL (如: /static/images/image-7.png): ").strip()
            prompt = input("提示词: ").strip()
            size = input("尺寸 (如: 512x512): ").strip()
            negative_prompt = input("负面提示词 (可选): ").strip()
            seed = input("种子 (可选，默认12345): ").strip()
            
            image_data = {
                'url': url,
                'prompt': prompt,
                'size': size,
                'negative_prompt': negative_prompt if negative_prompt else ''
            }
            
            if seed:
                try:
                    image_data['seed'] = int(seed)
                except ValueError:
                    print("❌ 种子必须是数字")
                    continue
            
            manager.add_image(image_data)
        
        elif choice == '3':
            image_id = input("请输入要删除的图片ID: ").strip()
            try:
                manager.remove_image(int(image_id))
            except ValueError:
                print("❌ ID必须是数字")
        
        elif choice == '4':
            image_id = input("请输入要更新的图片ID: ").strip()
            try:
                img = manager.get_image(int(image_id))
                if img:
                    print(f"\n当前图片信息:")
                    print(f"  Prompt: {img['prompt']}")
                    print(f"  Size: {img['size']}")
                    print(f"  Seed: {img['seed']}")
                    
                    new_prompt = input("新提示词 (回车跳过): ").strip()
                    new_size = input("新尺寸 (回车跳过): ").strip()
                    new_seed = input("新种子 (回车跳过): ").strip()
                    
                    updates = {}
                    if new_prompt:
                        updates['prompt'] = new_prompt
                    if new_size:
                        updates['size'] = new_size
                    if new_seed:
                        try:
                            updates['seed'] = int(new_seed)
                        except ValueError:
                            print("❌ 种子必须是数字")
                            continue
                    
                    if updates:
                        manager.update_image(int(image_id), updates)
                    else:
                        print("⚠️ 没有输入任何更新内容")
                else:
                    print(f"❌ 未找到ID为 {image_id} 的图片")
            except ValueError:
                print("❌ ID必须是数字")
        
        elif choice == '5':
            keyword = input("请输入搜索关键词: ").strip()
            results = manager.search_images(keyword)
            if not results:
                print("🔍 未找到匹配的图片")
            else:
                print(f"\n🔍 找到 {len(results)} 张匹配的图片:")
                for img in results:
                    print(f"  ID {img['id']}: {img['prompt'][:50]}...")
        
        elif choice == '6':
            missing_files = manager.validate_image_files()
            if not missing_files:
                print("✅ 所有图片文件都存在")
            else:
                print(f"❌ 发现 {len(missing_files)} 个缺失的图片文件:")
                for file in missing_files:
                    print(f"  {file}")
        
        else:
            print("❌ 无效选择，请重新输入")

if __name__ == "__main__":
    main() 