#!/usr/bin/env python3
"""
CogView4 Image Generation API Server with SSE Streaming
Implements OpenAI-compatible image generation API with streaming intermediate results
"""

import asyncio
import json
import logging
import time
import os
import base64
from contextlib import asynccontextmanager
from datetime import datetime
from io import BytesIO
import random

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

# Handle both relative and absolute imports
try:
    from . import config
    from .processing import WorkerPool
    from .schemas import (ImageData, ImageGenerationRequest,
                         ImageGenerationResponse, StreamingImageData,
                         PromptOptimizationRequest, PromptOptimizationResponse,
                         PromptTranslationRequest, PromptTranslationResponse,
                         GalleryImage, GalleryResponse)
    from .utils import parse_size, convert_prompt, translate_prompt
except ImportError:
    import config
    from processing import WorkerPool
    from schemas import (ImageData, ImageGenerationRequest,
                         ImageGenerationResponse, StreamingImageData,
                         PromptOptimizationRequest, PromptOptimizationResponse,
                         PromptTranslationRequest, PromptTranslationResponse,
                         GalleryImage, GalleryResponse)
    from utils import parse_size, convert_prompt, translate_prompt

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL not available, image resizing will be disabled")

# Initialize logging and config by importing
logger = logging.getLogger(__name__)

# Global worker pool
worker_pool: WorkerPool | None = None


def get_worker_pool() -> WorkerPool:
    """Initialize and return the global worker pool"""
    global worker_pool
    if worker_pool is None:
        logger.info(f"Initializing worker pool with model: {config.MODEL_PATH}")
        worker_pool = WorkerPool(
            model_path=config.MODEL_PATH,
            num_workers=config.NUM_WORKER_PROCESSES
        )
    return worker_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifespan events"""
    logger.info("Starting CogView4 API server...")
    try:
        get_worker_pool()
        logger.info("Worker pool initialization process started.")
    except Exception as e:
        logger.error(f"Failed to initialize worker pool: {e}")

    yield  # Application is running

    logger.info("Shutting down CogView4 API server...")
    pool = get_worker_pool()
    if pool:
        pool.shutdown()
        logger.info("Worker pool shut down successfully")


# FastAPI app
app = FastAPI(
    title="CogView4 Image Generation API",
    description="OpenAI-compatible image generation API with persistent worker pool using CogView4",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("Static files mounted successfully")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")


async def generate_sse_stream(request_data: ImageGenerationRequest):
    """Generate SSE stream of images using worker pool"""
    pool = get_worker_pool()
    request_start_time = time.time()
    logger.info("Starting SSE stream generation")

    try:
        width, height = parse_size(request_data.size)
        request_params = {
            "prompt": request_data.prompt,
            "negative_prompt": request_data.negative_prompt,
            "width": width, "height": height,
            "guidance_scale": request_data.guidance_scale,
            "num_inference_steps": request_data.num_inference_steps,
            "num_images": request_data.n,
            "seed": request_data.seed
        }

        async for result in pool.submit_request(stream=True, **request_params):
            stream_data = StreamingImageData(
                step=result['step'],
                total_steps=request_data.num_inference_steps,
                progress=result['progress'],
                image=result['image'],
                timestamp=result['timestamp'],
                is_final=result['is_final'],
                is_chunked=result.get('is_chunked', False),
                chunk_id=result.get('chunk_id'),
                chunk_index=result.get('chunk_index'),
                total_chunks=result.get('total_chunks'),
                image_index=result.get('image_index'),
                total_images=result.get('total_images'),
                seed=result.get('seed')
            )
            json_data = stream_data.model_dump_json()
            yield f"data: {json_data}\n\n"
            await asyncio.sleep(0.01)

        logger.info(f"SSE streaming completed in {time.time() - request_start_time:.2f}s")
        yield "data: [DONE]\n\n"

    except Exception as e:
        logger.error(f"SSE stream error: {e}", exc_info=True)
        error_data = {"error": str(e), "timestamp": time.time()}
        yield f"data: {json.dumps(error_data)}\n\n"
        yield "data: [DONE]\n\n"


@app.post("/v1/images/generations")
async def create_image(request: ImageGenerationRequest):
    """Create image(s) from text prompt using worker pool"""
    start_time = time.time()
    logger.info(f"Received image generation request: prompt='{request.prompt[:50]}...', stream={request.stream}, seed={request.seed}")

    width, height = parse_size(request.size)
    if width * height * request.n >= config.MAX_TOTAL_PIXELS:
        raise HTTPException(status_code=400, detail="Request exceeds VRAM limits.")

    if request.stream:
        return StreamingResponse(
            generate_sse_stream(request),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
    else:
        pool = get_worker_pool()
        try:
            request_params = {
                "prompt": request.prompt, "negative_prompt": request.negative_prompt,
                "width": width, "height": height,
                "guidance_scale": request.guidance_scale,
                "num_inference_steps": request.num_inference_steps,
                "num_images": request.n,
                "seed": request.seed
            }
            result = await pool.submit_non_streaming_request(**request_params)
            
            # Extract images and seed from result
            images_b64 = result.get('images', [])
            seed = result.get('seed')
            
            image_data = [ImageData(b64_json=b64, seed=seed) for b64 in images_b64]
            logger.info(f"Non-streaming request completed in {time.time() - start_time:.2f}s with seed {seed}")
            return ImageGenerationResponse(created=int(time.time()), data=image_data)

        except Exception as e:
            logger.error(f"Request failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI compatibility)"""
    return {
        "object": "list",
        "data": [{
            "id": "cogview4-6b", "object": "model", "created": int(time.time()),
            "owned_by": "thudm", "permission": [], "root": "cogview4-6b", "parent": None
        }]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    pool = get_worker_pool()
    return {
        "status": "healthy" if pool and pool.is_ready() else "unhealthy",
        "worker_pool_initialized": pool is not None,
        "workers_ready": pool.all_models_loaded() if pool else False,
        "total_workers": pool.num_workers if pool else 0,
    }


@app.get("/status")
async def status_check():
    """Detailed status endpoint"""
    pool = get_worker_pool()
    return {
        "server_version": "1.0.0",
        "worker_pool": {
            "initialized": pool is not None,
            "num_workers": pool.num_workers if pool else 0,
            "active_requests": len(pool.active_requests) if pool else 0,
        },
    }


@app.post("/v1/prompt/optimize")
async def optimize_prompt(request: PromptOptimizationRequest):
    """Optimize a prompt using the convert_prompt function"""
    start_time = time.time()
    logger.info(f"Received prompt optimization request: prompt='{request.prompt[:50]}...'")
    
    try:
        # Call the convert_prompt function
        optimized_prompt = convert_prompt(
            prompt=request.prompt,
            retry_times=request.retry_times
        )
        
        # Check if optimization was successful
        if optimized_prompt and optimized_prompt.strip():
            success = True
            message = "Prompt optimized successfully"
        else:
            success = False
            message = "Failed to optimize prompt - empty result"
            optimized_prompt = request.prompt  # Return original if optimization failed
        
        logger.info(f"Prompt optimization completed in {time.time() - start_time:.2f}s")
        
        return PromptOptimizationResponse(
            original_prompt=request.prompt,
            optimized_prompt=optimized_prompt,
            success=success,
            message=message
        )
        
    except Exception as e:
        logger.error(f"Prompt optimization failed: {e}", exc_info=True)
        return PromptOptimizationResponse(
            original_prompt=request.prompt,
            optimized_prompt=request.prompt,  # Return original on error
            success=False,
            message=f"Optimization failed: {str(e)}"
        )


@app.post("/v1/prompt/translate")
async def translate_prompt_api(request: PromptTranslationRequest):
    """Translate a prompt using the translate_prompt function"""
    start_time = time.time()
    logger.info(f"Received prompt translation request: prompt='{request.prompt[:50]}...'")
    
    try:
        # Call the translate_prompt function
        translated_prompt = translate_prompt(
            prompt=request.prompt,
            retry_times=request.retry_times
        )
        
        # Check if translation was successful
        if translated_prompt and translated_prompt.strip():
            success = True
            message = "Prompt translated successfully"
        else:
            success = False
            message = "Failed to translate prompt - empty result"
            translated_prompt = request.prompt  # Return original if translation failed
        
        logger.info(f"Prompt translation completed in {time.time() - start_time:.2f}s")
        
        return PromptTranslationResponse(
            original_prompt=request.prompt,
            translated_prompt=translated_prompt,
            success=success,
            message=message
        )
        
    except Exception as e:
        logger.error(f"Prompt translation failed: {e}", exc_info=True)
        return PromptTranslationResponse(
            original_prompt=request.prompt,
            translated_prompt=request.prompt,  # Return original on error
            success=False,
            message=f"Translation failed: {str(e)}"
        )


@app.get("/v1/gallery")
async def get_gallery():
    """Get gallery images from local JSON file"""
    logger.info("Received gallery request")
    
    try:
        # 读取本地JSON文件
        json_file_path = "static/images/gallery.json"
        
        if not os.path.exists(json_file_path):
            logger.warning(f"Gallery JSON file not found: {json_file_path}")
            # 返回空数据而不是错误
            return GalleryResponse(
                images=[],
                total_count=0
            )
        
        with open(json_file_path, 'r', encoding='utf-8') as f:
            gallery_data = json.load(f)
        
        # 验证JSON结构
        if 'images' not in gallery_data:
            logger.error("Invalid gallery JSON structure: missing 'images' key")
            raise HTTPException(status_code=500, detail="Invalid gallery data structure")
        
        # 转换数据格式
        gallery_images = []
        for img_data in gallery_data['images']:
            # 验证必要字段
            required_fields = ['id', 'url', 'prompt', 'size', 'seed', 'guidance_scale', 'num_inference_steps']
            for field in required_fields:
                if field not in img_data:
                    logger.warning(f"Image {img_data.get('id', 'unknown')} missing required field: {field}")
                    continue
            
            # 创建GalleryImage对象
            gallery_image = GalleryImage(
                id=img_data['id'],
                image_url=img_data['url'],
                prompt=img_data['prompt'],
                negative_prompt=img_data.get('negative_prompt'),
                size=img_data['size'],
                seed=img_data.get('seed'),
                timestamp=img_data.get('timestamp', time.time()),
                guidance_scale=img_data.get('guidance_scale', 5.0),
                num_inference_steps=img_data.get('num_inference_steps', 20)
            )
            gallery_images.append(gallery_image)
        
        logger.info(f"Loaded {len(gallery_images)} images from gallery JSON")
        
        return GalleryResponse(
            images=gallery_images,
            total_count=len(gallery_images)
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse gallery JSON: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid JSON format: {str(e)}")
    except Exception as e:
        logger.error(f"Gallery request failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Gallery request failed: {str(e)}")


@app.get("/gallery", include_in_schema=False)
async def gallery_page():
    """Redirect to the gallery page"""
    return RedirectResponse(url="/static/gallery.html")


@app.post("/v1/gallery/save")
async def save_to_gallery(request: dict):
    """Save generated image to gallery"""
    logger.info("Received save to gallery request")
    
    try:
        # 验证必需字段
        required_fields = ['image_data', 'prompt', 'size']
        for field in required_fields:
            if field not in request:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # 获取参数
        image_data = request['image_data']  # base64编码的图片数据
        prompt = request['prompt']
        size = request['size']
        negative_prompt = request.get('negative_prompt', '')
        seed = request.get('seed')
        guidance_scale = request.get('guidance_scale', 5.0)
        num_inference_steps = request.get('num_inference_steps', 20)
        
        # 如果seed为null或未提供，生成一个随机seed
        if seed is None:
            seed = random.randint(0, 2147483647)
            logger.info(f"Generated random seed for gallery: {seed}")
        
        # 确保images目录存在
        images_dir = "static/images"
        os.makedirs(images_dir, exist_ok=True)
        
        # 生成唯一的文件名
        timestamp = int(time.time())
        filename = f"image-{timestamp}.png"  # 默认扩展名
        file_path = os.path.join(images_dir, filename)
        
        # 保存图片文件
        try:
            # 解码base64数据
            image_bytes = base64.b64decode(image_data)
            
            # 如果PIL可用，检查图片格式并直接保存
            if PIL_AVAILABLE:
                # 从内存中加载图片
                img = Image.open(BytesIO(image_bytes))
                
                # 检查图片格式
                original_format = img.format
                logger.info(f"Original image format: {original_format}, size: {img.size}")
                
                # 根据格式更新文件名
                if original_format == 'JPEG':
                    filename = f"image-{timestamp}.jpg"
                    file_path = os.path.join(images_dir, filename)
                
                # 直接保存图片，不进行缩放
                save_format = 'JPEG' if original_format == 'JPEG' else 'PNG'
                save_kwargs = {'optimize': True}
                if save_format == 'JPEG':
                    save_kwargs['quality'] = 85  # JPEG质量设置
                
                with open(file_path, 'wb') as f:
                    img.save(f, save_format, **save_kwargs)
                
                logger.info(f"Image saved as {save_format} to: {file_path}")
            else:
                # 如果PIL不可用，直接保存原图
                with open(file_path, 'wb') as f:
                    f.write(image_bytes)
                logger.info(f"Image saved without processing to: {file_path}")
                
        except Exception as e:
            logger.error(f"Failed to save image file: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save image file: {str(e)}")
        
        # 读取现有的gallery.json文件
        json_file_path = "static/images/gallery.json"
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r', encoding='utf-8') as f:
                gallery_data = json.load(f)
        else:
            gallery_data = {"images": []}
        
        # 生成新的ID
        next_id = 1
        if gallery_data['images']:
            next_id = max(img['id'] for img in gallery_data['images']) + 1
        
        # 创建新的图片记录
        new_image = {
            'id': next_id,
            'url': f"/static/images/{filename}",
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'size': size,
            'seed': seed,
            'timestamp': timestamp,
            'guidance_scale': guidance_scale,
            'num_inference_steps': num_inference_steps
        }
        
        # 添加到gallery数据
        gallery_data['images'].append(new_image)
        
        # 保存更新后的JSON文件
        try:
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(gallery_data, f, ensure_ascii=False, indent=4)
            logger.info(f"Gallery JSON updated with new image ID: {next_id}")
        except Exception as e:
            logger.error(f"Failed to update gallery JSON: {e}")
            # 如果JSON更新失败，删除已保存的图片文件
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=500, detail=f"Failed to update gallery data: {str(e)}")
        
        return {
            "success": True,
            "message": "Image saved to gallery successfully",
            "image_id": next_id,
            "filename": filename,
            "url": f"/static/images/{filename}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Save to gallery failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Save to gallery failed: {str(e)}")


@app.delete("/v1/gallery/delete/{image_id}")
async def delete_from_gallery(image_id: int):
    """Delete an image from the gallery"""
    logger.info(f"Received delete request for image ID: {image_id}")
    
    try:
        # 读取现有的gallery.json文件
        json_file_path = "static/images/gallery.json"
        
        if not os.path.exists(json_file_path):
            logger.warning(f"Gallery JSON file not found: {json_file_path}")
            raise HTTPException(status_code=404, detail="Gallery data not found")
        
        with open(json_file_path, 'r', encoding='utf-8') as f:
            gallery_data = json.load(f)
        
        # 查找要删除的图片
        image_to_delete = None
        for img in gallery_data['images']:
            if img['id'] == image_id:
                image_to_delete = img
                break
        
        if not image_to_delete:
            logger.warning(f"Image with ID {image_id} not found")
            raise HTTPException(status_code=404, detail=f"Image with ID {image_id} not found")
        
        # 删除图片文件
        image_file_path = image_to_delete['url'].lstrip('/')
        if os.path.exists(image_file_path):
            try:
                os.remove(image_file_path)
                logger.info(f"Image file deleted: {image_file_path}")
            except Exception as e:
                logger.error(f"Failed to delete image file: {e}")
                # 继续删除JSON记录，即使文件删除失败
        else:
            logger.warning(f"Image file not found: {image_file_path}")
        
        # 从gallery数据中删除图片记录
        gallery_data['images'] = [img for img in gallery_data['images'] if img['id'] != image_id]
        
        # 保存更新后的JSON文件
        try:
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(gallery_data, f, ensure_ascii=False, indent=4)
            logger.info(f"Gallery JSON updated, removed image ID: {image_id}")
        except Exception as e:
            logger.error(f"Failed to update gallery JSON: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to update gallery data: {str(e)}")
        
        return {
            "success": True,
            "message": f"Image {image_id} deleted successfully",
            "deleted_image_id": image_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete from gallery failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Delete from gallery failed: {str(e)}")


@app.get("/", include_in_schema=False)
async def root():
    """Redirect to the web client"""
    return RedirectResponse(url="/static/index.html")


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server for CogView4 API...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=1
    ) 