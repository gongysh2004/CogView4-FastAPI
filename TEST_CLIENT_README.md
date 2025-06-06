# CogView4 API Test Client

A comprehensive test client for the CogView4 Image Generation API server that demonstrates both streaming and non-streaming functionality.

## Installation

Install the required dependencies:

```bash
pip install -r test_requirements.txt
```

## Usage

### Basic Usage

Test API endpoints only (default):
```bash
python test_client.py
```

Test with custom API URL:
```bash
python test_client.py --url http://your-server:8000
```

### Comprehensive Testing

Run all tests:
```bash
python test_client.py --all
```

### Specific Tests

Test only API endpoints:
```bash
python test_client.py --test-endpoints
```

Test only streaming generation:
```bash
python test_client.py --test-streaming
```

Test only non-streaming generation:
```bash
python test_client.py --test-non-streaming
```

### Advanced Options

Custom prompt and save intermediate images:
```bash
python test_client.py --all --prompt "A futuristic cityscape at night" --save-intermediates
```

Custom output directory:
```bash
python test_client.py --test-streaming --output-dir ./my_images
```

## Command Line Arguments

- `--url`: API base URL (default: http://localhost:8000)
- `--prompt`: Text prompt for image generation (default: "A beautiful sunset over mountains")
- `--test-endpoints`: Test API endpoints (/health, /status, /v1/models)
- `--test-streaming`: Test streaming image generation with SSE
- `--test-non-streaming`: Test standard image generation
- `--save-intermediates`: Save intermediate images during streaming (shows generation progress)
- `--output-dir`: Output directory for generated images (default: "output")
- `--all`: Run all tests

## Features

### API Endpoint Testing
- Health check (`/health`)
- Status information (`/status`)
- Available models (`/v1/models`)

### Streaming Generation Testing
- Server-Sent Events (SSE) streaming
- Real-time progress updates
- Chunked data reassembly for large images
- Intermediate image saving (optional)
- Step-by-step generation visualization

### Non-Streaming Generation Testing
- Standard HTTP POST request
- Final image generation
- Response time measurement

### Image Handling
- Base64 decoding and saving
- PNG format for final images
- JPEG format for intermediate images
- Automatic output directory creation
- Unique filename generation with timestamps

## Example Output

```
2024-01-15 10:30:00,123 - INFO - Testing CogView4 API at: http://localhost:8000
2024-01-15 10:30:00,124 - INFO - Output directory: output
2024-01-15 10:30:00,125 - INFO - === Testing API Endpoints ===
2024-01-15 10:30:00,126 - INFO - Testing health endpoint...
2024-01-15 10:30:00,130 - INFO - Health: {'status': 'healthy', 'worker_pool_initialized': True, 'active_workers': 4, 'model_loaded': True}
2024-01-15 10:30:00,131 - INFO - === Testing Image Generation ===
2024-01-15 10:30:00,132 - INFO - Testing streaming generation...
2024-01-15 10:30:00,133 - INFO - Starting streaming generation: A beautiful sunset over mountains...
2024-01-15 10:30:00,134 - INFO - Connected to streaming endpoint, receiving data...
2024-01-15 10:30:02,456 - INFO - Step 1/20 (5.0%) - 2.3s elapsed
2024-01-15 10:30:04,789 - INFO - Step 5/20 (25.0%) - 4.7s elapsed
...
2024-01-15 10:30:25,123 - INFO - Saved final image: output/final_image_1705320625.png
2024-01-15 10:30:25,124 - INFO - ✅ All tests completed successfully!
```

## Integration Example

You can also use the `CogView4Client` class in your own code:

```python
import asyncio
from test_client import CogView4Client

async def generate_image():
    async with CogView4Client("http://localhost:8000") as client:
        # Check API health
        health = await client.health_check()
        print(f"API Health: {health}")
        
        # Generate image with streaming
        result = await client.generate_image_streaming(
            prompt="A serene mountain landscape",
            negative_prompt="blurry, low quality",
            size="1024x1024",
            guidance_scale=7.5,
            num_inference_steps=50,
            save_intermediates=True
        )
        
        print(f"Generated {len(result['images'])} images in {result['total_time']:.2f}s")

# Run the example
asyncio.run(generate_image())
```

## Troubleshooting

### Common Issues

1. **Connection refused**: Make sure the API server is running on the specified URL
2. **Module not found**: Install dependencies with `pip install -r test_requirements.txt`
3. **Permission errors**: Ensure write permissions for the output directory
4. **Timeout errors**: The server might be busy or model loading; check server logs

### Server Requirements

- The API server should be running and healthy
- At least one worker process should have loaded the model successfully
- Sufficient GPU memory for image generation

### Performance Notes

- Streaming tests show real-time generation progress
- Use smaller image sizes (512x512) and fewer steps (20) for faster testing
- Intermediate image saving increases disk I/O but provides valuable debugging information 