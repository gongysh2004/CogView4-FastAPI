#!/usr/bin/env python3
"""
Simple connectivity test for CogView4 API
Tests basic endpoints without streaming to isolate issues
"""

import asyncio
import aiohttp
import json
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_connectivity(base_url: str = "http://localhost:8000"):
    """Test basic API connectivity"""
    
    # Configure client with large limits
    connector = aiohttp.TCPConnector(
        limit=100,
        limit_per_host=30,
        keepalive_timeout=300,
        enable_cleanup_closed=True
    )
    
    timeout = aiohttp.ClientTimeout(
        total=300,  # 5 minutes
        sock_connect=30,
        sock_read=60
    )
    
    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        connector_kwargs={
            'max_line_size': 1024 * 1024 * 10,  # 10MB
            'max_field_size': 1024 * 1024 * 10   # 10MB
        }
    ) as session:
        
        # Test health endpoint
        try:
            logger.info("Testing /health endpoint...")
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    logger.info(f"✅ Health check passed: {health_data}")
                else:
                    logger.error(f"❌ Health check failed: HTTP {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return False
        
        # Test status endpoint
        try:
            logger.info("Testing /status endpoint...")
            async with session.get(f"{base_url}/status") as response:
                if response.status == 200:
                    status_data = await response.json()
                    logger.info(f"✅ Status check passed")
                    logger.info(f"Worker pool initialized: {status_data.get('worker_pool', {}).get('initialized', False)}")
                    logger.info(f"Active workers: {status_data.get('worker_pool', {}).get('num_workers', 0)}")
                else:
                    logger.error(f"❌ Status check failed: HTTP {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Status check failed: {e}")
            return False
        
        # Test models endpoint
        try:
            logger.info("Testing /v1/models endpoint...")
            async with session.get(f"{base_url}/v1/models") as response:
                if response.status == 200:
                    models_data = await response.json()
                    logger.info(f"✅ Models endpoint passed: {len(models_data.get('data', []))} models available")
                else:
                    logger.error(f"❌ Models check failed: HTTP {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Models check failed: {e}")
            return False
        
        # Test a simple non-streaming image generation request
        try:
            logger.info("Testing simple non-streaming generation...")
            payload = {
                "prompt": "A simple test image",
                "size": "512x512",
                "guidance_scale": 5.0,
                "num_inference_steps": 10,  # Very few steps for quick test
                "n": 1,
                "stream": False,
                "response_format": "b64_json"
            }
            
            async with session.post(f"{base_url}/v1/images/generations", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ Non-streaming generation passed: {len(result.get('data', []))} images generated")
                    
                    # Check if we got valid base64 data
                    if result.get('data') and result['data'][0].get('b64_json'):
                        b64_len = len(result['data'][0]['b64_json'])
                        logger.info(f"   Image data size: {b64_len} characters")
                        if b64_len > 1000:  # Should be substantial for a real image
                            logger.info("   ✅ Image data appears valid")
                        else:
                            logger.warning(f"   ⚠️ Image data seems small: {b64_len} chars")
                    
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Non-streaming generation failed: HTTP {response.status}")
                    logger.error(f"   Error: {error_text}")
                    return False
        except Exception as e:
            logger.error(f"❌ Non-streaming generation failed: {e}")
            return False
        
        # Test streaming connectivity (without processing all data)
        try:
            logger.info("Testing streaming endpoint connectivity...")
            payload = {
                "prompt": "A simple test image",
                "size": "512x512",
                "guidance_scale": 5.0,
                "num_inference_steps": 5,  # Very few steps
                "n": 1,
                "stream": True,
                "response_format": "b64_json"
            }
            
            async with session.post(f"{base_url}/v1/images/generations", json=payload) as response:
                if response.status == 200:
                    logger.info("✅ Streaming endpoint connected successfully")
                    
                    # Check content type
                    content_type = response.headers.get('content-type', '')
                    logger.info(f"   Content-Type: {content_type}")
                    
                    if 'text/event-stream' in content_type:
                        logger.info("   ✅ Correct SSE content type")
                    else:
                        logger.warning(f"   ⚠️ Unexpected content type: {content_type}")
                    
                    # Read just a few chunks to test
                    chunk_count = 0
                    try:
                        async for chunk in response.content.iter_chunked(8192):
                            chunk_count += 1
                            logger.info(f"   Received chunk {chunk_count}, size: {len(chunk)} bytes")
                            
                            # Stop after a few chunks to avoid full generation
                            if chunk_count >= 3:
                                logger.info("   ✅ Streaming data reception works")
                                break
                                
                    except Exception as stream_error:
                        logger.error(f"   ❌ Error reading stream: {stream_error}")
                        return False
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Streaming endpoint failed: HTTP {response.status}")
                    logger.error(f"   Error: {error_text}")
                    return False
        except Exception as e:
            logger.error(f"❌ Streaming connectivity test failed: {e}")
            return False
        
        logger.info("🎉 All connectivity tests passed!")
        return True


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test CogView4 API connectivity")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()
    
    logger.info(f"Testing connectivity to: {args.url}")
    
    success = await test_connectivity(args.url)
    
    if success:
        logger.info("✅ All tests passed! API is working correctly.")
        return 0
    else:
        logger.error("❌ Some tests failed. Check server logs for details.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1) 