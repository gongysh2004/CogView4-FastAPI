# 图片走廊JSON文件格式说明

## 文件位置
```
static/images/gallery.json
```

## JSON结构

### 根对象
```json
{
    "images": [
        // 图片对象数组
    ]
}
```

### 图片对象字段

| 字段名 | 类型 | 必需 | 说明 | 示例 |
|--------|------|------|------|------|
| `id` | integer | ✅ | 图片唯一标识符 | `1` |
| `url` | string | ✅ | 图片文件路径 | `"/static/images/image-1.png"` |
| `prompt` | string | ✅ | 生成图片的提示词 | `"A beautiful sunset over a calm ocean"` |
| `negative_prompt` | string | ❌ | 负面提示词 | `"no text, no watermark"` |
| `size` | string | ✅ | 图片尺寸 | `"512x912"` |
| `seed` | integer | ❌ | 随机种子 | `11111` |
| `timestamp` | number | ❌ | 生成时间戳 | `1750677262` |
| `guidance_scale` | number | ❌ | 引导比例 | `6.0` |
| `num_inference_steps` | integer | ❌ | 推理步数 | `25` |

## 完整示例

```json
{
    "images": [
        {
            "id": 1,
            "url": "/static/images/image-1.png",
            "prompt": "A beautiful sunset over a calm ocean",
            "negative_prompt": "no text, no watermark, no logo",
            "size": "512x912",
            "seed": 11111,
            "timestamp": 1750677262,
            "guidance_scale": 6.0,
            "num_inference_steps": 25
        },
        {
            "id": 2,
            "url": "/static/images/image-2.png",
            "prompt": "A futuristic cityscape with flying cars and neon lights",
            "negative_prompt": "blurry, low quality, distorted",
            "size": "912x512",
            "seed": 22222,
            "timestamp": 1750677262,
            "guidance_scale": 7.0,
            "num_inference_steps": 30
        }
    ]
}
```

## 支持的图片尺寸

| 尺寸 | 宽高比 | 说明 |
|------|--------|------|
| `512x512` | 1:1 | 正方形 |
| `1024x1024` | 1:1 | 大正方形 |
| `912x512` | 16:9 | 宽屏 |
| `1280x720` | 16:9 | 高清宽屏 |
| `512x912` | 9:16 | 竖屏 |
| `720x1280` | 9:16 | 高清竖屏 |

## 图片文件要求

### 文件位置
所有图片文件应放在 `static/images/` 目录下

### 支持的格式
- PNG (推荐)
- JPG/JPEG
- WebP

### 文件命名建议
- 使用有意义的名称：`image-1.png`, `sunset-ocean.png`
- 避免特殊字符和空格
- 使用小写字母和连字符

## 添加新图片

### 1. 上传图片文件
将图片文件上传到 `static/images/` 目录

### 2. 编辑JSON文件
在 `gellery.json` 中添加新的图片对象：

```json
{
    "id": 7,
    "url": "/static/images/your-new-image.png",
    "prompt": "Your image prompt here",
    "negative_prompt": "Optional negative prompt",
    "size": "512x512",
    "seed": 77777,
    "timestamp": 1750677262,
    "guidance_scale": 5.0,
    "num_inference_steps": 20
}
```

### 3. 验证格式
运行测试脚本验证JSON格式：
```bash
python test_json_gallery.py
```

## 错误处理

### 常见错误

1. **JSON格式错误**
   - 检查JSON语法
   - 确保所有括号和引号正确匹配

2. **缺少必需字段**
   - 确保每个图片对象都有 `id`, `url`, `prompt`, `size` 字段

3. **图片文件不存在**
   - 确保图片文件路径正确
   - 检查文件是否存在于指定位置

4. **ID重复**
   - 确保每个图片的ID是唯一的

### 调试方法

1. 使用在线JSON验证工具验证格式
2. 运行测试脚本检查数据完整性
3. 查看服务器日志获取详细错误信息

## 性能考虑

### 图片优化
- 压缩图片文件大小
- 使用适当的图片格式
- 考虑使用WebP格式提高加载速度

### JSON文件大小
- 避免在JSON中包含大量图片数据
- 考虑分页加载大量图片
- 定期清理不需要的图片数据

## 扩展功能

### 图片分类
可以在JSON中添加分类信息：
```json
{
    "id": 1,
    "url": "/static/images/image-1.png",
    "prompt": "A beautiful sunset over a calm ocean",
    "category": "landscape",
    "tags": ["sunset", "ocean", "nature"]
}
```

### 用户信息
可以添加生成者信息：
```json
{
    "id": 1,
    "url": "/static/images/image-1.png",
    "prompt": "A beautiful sunset over a calm ocean",
    "user": "artist123",
    "created_at": "2024-01-15T10:30:00Z"
}
```

### 评分系统
可以添加评分和评论：
```json
{
    "id": 1,
    "url": "/static/images/image-1.png",
    "prompt": "A beautiful sunset over a calm ocean",
    "rating": 4.5,
    "likes": 42,
    "comments": 8
}
``` 