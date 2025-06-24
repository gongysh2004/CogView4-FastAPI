#!/usr/bin/env python3
"""
Test Client for CogView4 Image Generation API
Demonstrates streaming and non-streaming image generation requests
"""

import asyncio
import aiohttp
import json
import base64
import time
import argparse
import sys
from typing import Dict, Any, Optional
from pathlib import Path
import logging
import pytest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CogView4Client:
    """Client for CogView4 Image Generation API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = None
    
    async def __aenter__(self):
        # Configure connector with larger limits for handling large image data
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=30,
            keepalive_timeout=300,
            enable_cleanup_closed=True
        )
        
        # Configure timeout with longer values for image generation
        timeout = aiohttp.ClientTimeout(
            total=1800,  # 30 minutes total timeout
            sock_connect=30,
            sock_read=300  # 5 minutes read timeout
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check API health status"""
        url = f"{self.base_url}/health"
        async with self.session.get(url) as response:
            return await response.json()
    
    async def get_status(self) -> Dict[str, Any]:
        """Get detailed API status"""
        url = f"{self.base_url}/status"
        async with self.session.get(url) as response:
            return await response.json()
    
    async def list_models(self) -> Dict[str, Any]:
        """List available models"""
        url = f"{self.base_url}/v1/models"
        async with self.session.get(url) as response:
            return await response.json()
    
    async def generate_image_streaming(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        size: str = "1024x1024",
        guidance_scale: float = 5.0,
        num_inference_steps: int = 5,
        n: int = 1,
        save_intermediates: bool = False,
        output_dir: str = "output"
    ) -> Dict[str, Any]:
        """Generate image with streaming (SSE) support"""
        
        url = f"{self.base_url}/v1/images/generations"
        
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "size": size,
            "guidance_scale": guidance_scale,
            "num_inference_steps": num_inference_steps,
            "n": n,
            "stream": True,
            "response_format": "b64_json"
        }
        
        logger.info(f"Starting streaming generation: {prompt[:50]}...")
        logger.info(f"Parameters: size={size}, steps={num_inference_steps}, guidance={guidance_scale}")
        
        # Create output directory
        if save_intermediates:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
        
        # Track chunks for reassembly
        chunk_buffers = {}  # {chunk_id: {chunk_index: data}}
        final_images = []
        step_count = 0
        start_time = time.time()
        
        async with self.session.post(url, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"HTTP {response.status}: {error_text}")
            
            logger.info("Connected to streaming endpoint, receiving data...")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            # Verify content type
            content_type = response.headers.get('content-type', '')
            if 'text/event-stream' not in content_type:
                logger.warning(f"Unexpected content type: {content_type}")
            
            # Read response content in chunks to handle large data
            buffer = ""
            chunk_count = 0
            
            try:
                async for chunk in response.content.iter_chunked(8192):  # 8KB chunks
                    chunk_count += 1
                    if chunk_count % 100 == 0:  # Log every 100 chunks
                        logger.debug(f"Processed {chunk_count} chunks, buffer size: {len(buffer)}")
                    
                    try:
                        buffer += chunk.decode('utf-8', errors='ignore')
                    except UnicodeDecodeError as e:
                        logger.warning(f"Unicode decode error in chunk {chunk_count}: {e}")
                        continue
                    
                    # Process complete lines
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        
                        if line.startswith('data: '):
                            data_str = line[6:]  # Remove 'data: ' prefix
                            
                            if data_str == '[DONE]':
                                logger.info("Stream completed")
                                return {
                                    "images": final_images,
                                    "steps_processed": step_count + 1,
                                    "total_time": time.time() - start_time,
                                    "streaming": True
                                }
                            
                            try:
                                data = json.loads(data_str)
                                
                                if 'error' in data:
                                    logger.error(f"Stream error: {data['error']}")
                                    break
                                
                                step = data.get('step', 0)
                                progress = data.get('progress', 0.0)
                                is_final = data.get('is_final', False)
                                is_chunked = data.get('is_chunked', False)
                                
                                if step > step_count:
                                    step_count = step
                                    elapsed = time.time() - start_time
                                    logger.info(f"Step {step + 1}/{num_inference_steps} ({progress:.1%}) - {elapsed:.1f}s elapsed")
                                
                                if is_chunked:
                                    # Handle chunked data
                                    chunk_id = data.get('chunk_id')
                                    chunk_index = data.get('chunk_index')
                                    total_chunks = data.get('total_chunks')
                                    chunk_data = data.get('image', '')
                                    
                                    if chunk_id not in chunk_buffers:
                                        chunk_buffers[chunk_id] = {}
                                    
                                    chunk_buffers[chunk_id][chunk_index] = chunk_data
                                    
                                    # Check if we have all chunks for this step
                                    if len(chunk_buffers[chunk_id]) == total_chunks:
                                        # Reassemble the image
                                        complete_image_b64 = ''.join(
                                            chunk_buffers[chunk_id][i] for i in range(total_chunks)
                                        )
                                        
                                        # Save intermediate or final image
                                        await self._save_image(
                                            complete_image_b64, 
                                            step, 
                                            is_final, 
                                            output_dir if save_intermediates else None,
                                            final_images if is_final else None
                                        )
                                        
                                        # Clean up chunk buffer
                                        del chunk_buffers[chunk_id]
                                
                                else:
                                    # Handle single-piece data
                                    image_b64 = data.get('image', '')
                                    if image_b64:
                                        await self._save_image(
                                            image_b64, 
                                            step, 
                                            is_final, 
                                            output_dir if save_intermediates else None,
                                            final_images if is_final else None
                                        )
                            
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse JSON: {e}")
                                continue
                            except Exception as e:
                                logger.error(f"Error processing stream data: {e}")
                                continue
            
            except Exception as e:
                logger.error(f"Error reading stream: {e}")
                return {
                    "images": [],
                    "steps_processed": 0,
                    "total_time": 0,
                    "streaming": True
                }
        
        # Fallback return if stream ends without [DONE] signal
        total_time = time.time() - start_time
        logger.info(f"Streaming generation completed in {total_time:.2f}s")
        logger.info(f"Generated {len(final_images)} final images")
        
        return {
            "images": final_images,
            "steps_processed": step_count + 1,
            "total_time": total_time,
            "streaming": True
        }
    
    async def generate_image_non_streaming(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        size: str = "1024x1024",
        guidance_scale: float = 5.0,
        num_inference_steps: int = 5,
        n: int = 1,
        output_dir: str = "output"
    ) -> Dict[str, Any]:
        """Generate image without streaming"""
        
        url = f"{self.base_url}/v1/images/generations"
        
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "size": size,
            "guidance_scale": guidance_scale,
            "num_inference_steps": num_inference_steps,
            "n": n,
            "stream": False,
            "response_format": "b64_json"
        }
        
        logger.info(f"Starting non-streaming generation: {prompt[:50]}...")
        logger.info(f"Parameters: size={size}, steps={num_inference_steps}, guidance={guidance_scale}")
        
        start_time = time.time()
        
        async with self.session.post(url, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"HTTP {response.status}: {error_text}")
            
            result = await response.json()
        
        total_time = time.time() - start_time
        logger.info(f"Non-streaming generation completed in {total_time:.2f}s")
        
        # Save final images
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        saved_images = []
        for i, image_data in enumerate(result['data']):
            if 'b64_json' in image_data:
                filename = f"final_image_{int(time.time())}_{i}.png"
                filepath = output_path / filename
                
                # Decode and save image
                image_bytes = base64.b64decode(image_data['b64_json'])
                filepath.write_bytes(image_bytes)
                
                saved_images.append(str(filepath))
                logger.info(f"Saved final image: {filepath}")
        
        return {
            "images": saved_images,
            "total_time": total_time,
            "streaming": False,
            "response": result
        }
    
    async def _save_image(
        self, 
        image_b64: str, 
        step: int, 
        is_final: bool, 
        output_dir: Optional[str] = None,
        final_images_list: Optional[list] = None
    ):
        """Save image from base64 data with improved error handling"""
        if not image_b64:
            return
        
        try:
            # Log image data size for debugging
            logger.debug(f"Saving image: step={step}, is_final={is_final}, data_size={len(image_b64)} chars")
            
            # Decode base64 data
            try:
                image_bytes = base64.b64decode(image_b64)
                logger.debug(f"Decoded image size: {len(image_bytes)} bytes")
            except Exception as decode_error:
                logger.error(f"Failed to decode base64 image data: {decode_error}")
                return
            
            if output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(exist_ok=True)
                
                if is_final:
                    filename = f"final_image_{int(time.time())}.png"
                else:
                    filename = f"step_{step:03d}_{int(time.time())}.jpg"
                
                filepath = output_path / filename
                
                # Write file with error handling
                try:
                    filepath.write_bytes(image_bytes)
                    logger.debug(f"Successfully wrote {len(image_bytes)} bytes to {filepath}")
                except Exception as write_error:
                    logger.error(f"Failed to write image file {filepath}: {write_error}")
                    return
                
                if is_final and final_images_list is not None:
                    final_images_list.append(str(filepath))
                
                if is_final:
                    logger.info(f"Saved final image: {filepath} ({len(image_bytes)} bytes)")
                else:
                    logger.debug(f"Saved intermediate image: {filepath} ({len(image_bytes)} bytes)")
        
        except Exception as e:
            logger.error(f"Failed to save image (step={step}, is_final={is_final}): {e}")
            logger.debug(f"Image data preview: {image_b64[:100]}..." if len(image_b64) > 100 else image_b64)


@pytest.fixture
async def client():
    """Fixture to provide a CogView4Client instance"""
    async with CogView4Client("http://localhost:8000") as client:
        yield client

@pytest.mark.asyncio
async def test_api_endpoints(client):
    """Test all API endpoints"""
    logger.info("=== Testing API Endpoints ===")
    
    try:
        # Test health check
        logger.info("Testing health endpoint...")
        health = await client.health_check()
        logger.info(f"Health: {health}")
        
        # Test status
        logger.info("Testing status endpoint...")
        status = await client.get_status()
        logger.info(f"Status: {json.dumps(status, indent=2)}")
        
        # Test models
        logger.info("Testing models endpoint...")
        models = await client.list_models()
        logger.info(f"Models: {json.dumps(models, indent=2)}")
        
        assert True  # If we get here, all tests passed
        
    except Exception as e:
        logger.error(f"API endpoint test failed: {e}")
        assert False, f"API endpoint test failed: {e}"

@pytest.mark.asyncio
async def test_image_generation_streaming(client):
    """Test streaming image generation"""
    logger.info("=== Testing Streaming Image Generation ===")
    
    try:
        logger.info("Testing streaming generation...")
        streaming_result = await client.generate_image_streaming(
            prompt="A beautiful sunset over mountains",
            negative_prompt="blurry, low quality, distorted",
            size="512x512",  # Smaller size for faster testing
            guidance_scale=7.5,
            num_inference_steps=10,  # Minimum required by API
            n=1,
            save_intermediates=False
        )
        logger.info(f"Streaming test completed: {streaming_result['total_time']:.2f}s")
        assert 'total_time' in streaming_result
        assert streaming_result['streaming'] == True
        
    except Exception as e:
        logger.error(f"Streaming test failed: {e}")
        assert False, f"Streaming test failed: {e}"

@pytest.mark.asyncio
async def test_image_generation_non_streaming(client):
    """Test non-streaming image generation"""
    logger.info("=== Testing Non-Streaming Image Generation ===")
    
    try:
        logger.info("Testing non-streaming generation...")
        non_streaming_result = await client.generate_image_non_streaming(
            prompt="A beautiful sunset over mountains",
            negative_prompt="blurry, low quality, distorted",
            size="512x512",  # Smaller size for faster testing
            guidance_scale=7.5,
            num_inference_steps=10,  # Minimum required by API
            n=1
        )
        logger.info(f"Non-streaming test completed: {non_streaming_result['total_time']:.2f}s")
        assert 'total_time' in non_streaming_result
        assert non_streaming_result['streaming'] == False
        
    except Exception as e:
        logger.error(f"Non-streaming test failed: {e}")
        assert False, f"Non-streaming test failed: {e}"


async def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description="Test client for CogView4 API")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--prompt", default="A beautiful sunset over mountains", help="Text prompt for image generation")
    parser.add_argument("--test-endpoints", action="store_true", help="Test API endpoints")
    parser.add_argument("--test-streaming", action="store_true", help="Test streaming generation")
    parser.add_argument("--test-non-streaming", action="store_true", help="Test non-streaming generation")
    parser.add_argument("--save-intermediates", action="store_true", help="Save intermediate images during streaming")
    parser.add_argument("--output-dir", default="output", help="Output directory for images")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    # If no specific tests selected, default to endpoint testing
    if not any([args.test_endpoints, args.test_streaming, args.test_non_streaming, args.all]):
        args.test_endpoints = True
    
    if args.all:
        args.test_endpoints = True
        args.test_streaming = True
        args.test_non_streaming = True
    
    logger.info(f"Testing CogView4 API at: {args.url}")
    logger.info(f"Output directory: {args.output_dir}")
    
    async with CogView4Client(args.url) as client:
        success = True
        
        # Test API endpoints
        if args.test_endpoints:
            endpoint_success = await test_api_endpoints(client)
            success = success and endpoint_success
        
        # Test image generation
        if args.test_streaming or args.test_non_streaming:
            try:
                generation_results = await test_image_generation(
                    client=client,
                    prompt=args.prompt,
                    test_streaming=args.test_streaming,
                    test_non_streaming=args.test_non_streaming,
                    save_intermediates=args.save_intermediates
                )
                
                logger.info("=== Generation Results Summary ===")
                for method, result in generation_results.items():
                    if 'error' in result:
                        logger.error(f"{method}: Failed - {result['error']}")
                        success = False
                    else:
                        logger.info(f"{method}: Success - {result['total_time']:.2f}s, {len(result.get('images', []))} images")
                
            except Exception as e:
                logger.error(f"Image generation test failed: {e}")
                success = False
        
        if success:
            logger.info("✅ All tests completed successfully!")
            return 0
        else:
            logger.error("❌ Some tests failed!")
            return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed with unexpected error: {e}")
        sys.exit(1) 