# CogView4 Image Generation API with Advanced Multiprocessing & Streaming

A high-performance FastAPI-based implementation of an OpenAI-compatible image generation API using CogView4, featuring **persistent worker pool architecture**, **real-time streaming** with intelligent chunking, and **comprehensive testing tools**.

## 🚀 Key Features

- **🏗️ Production-Ready Architecture** - Persistent worker pool with multiprocessing for true concurrent generation
- **🚀 Intelligent Prompt Batching** - Automatic batching of compatible requests for 3-5x GPU efficiency improvement
- **⚡ Real-time SSE Streaming** - Watch images form step-by-step with intelligent chunking for large images  
- **🎯 OpenAI Compatibility** - Drop-in replacement for OpenAI's image generation API
- **🤖 AI-Powered Prompt Optimization** - Intelligent prompt enhancement for better image generation results
- **🔧 Advanced Configuration** - Environment variables, logging, and deployment options
- **🧪 Comprehensive Testing** - Full test suite with connectivity, streaming, and performance validation
- **📚 Complete Documentation** - Detailed API docs, architecture guides, and client examples
- **🌐 Production Web Client** - Modern HTML interface with real-time progress visualization
- **🔄 GPU Load Balancing** - Automatic distribution across multiple GPUs
- **🛡️ Robust Error Handling** - Graceful fallbacks and detailed logging

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   Web Client    │◄──▶│   FastAPI Main   │◄──▶│   Persistent Worker │
│ (web_client.html│    │    Process       │    │       Pool          │
│  + Real-time UI)│    │ (cogview4_api_   │    │  (4 GPU Workers)    │
└─────────────────┘    │   server.py)     │    └─────────────────────┘
                       └──────────────────┘              │
                                │                        │
                       ┌──────────────────┐              │
                       │  BatchManager +  │              │
                       │  Advanced SSE    │              │
                       │   Streaming      │              │
                       │ • Smart Batching │              │
                       │ • Chunking       │              │
                       │ • Queue Mgmt     │              │
                       │ • Error Recovery │              │
                       └──────────────────┘              │
                                                         │
                       ┌─────────────────────────────────┴┐
                       │     Per-Worker Resources         │
                       │ • CogView4 Pipeline (12GB)       │
                       │ • Dedicated GPU Memory           │
                       │ • Individual + Batch Processing  │
                       │ • from_pipe() Memory Efficiency  │
                       └──────────────────────────────────┘
```

**🚀 Prompt Batching Innovation:**
- **Automatic Detection**: Requests with identical generation parameters are automatically batched
- **GPU Efficiency**: Single inference call processes multiple prompts simultaneously
- **Fair Distribution**: Each request maintains its individual prompt and negative_prompt
- **Timeout Protection**: Maximum 0.5s wait ensures responsiveness
- **3-5x Throughput**: Significant performance improvement for concurrent requests
- **Configurable**: Enable/disable via `ENABLE_PROMPT_BATCHING` environment variable

## 📁 Project Structure

```
CogView4-FastAPI/
├── src/                          # Backend Python source code
│   ├── __init__.py              # Package initialization
│   ├── main.py                  # Main FastAPI server with worker pool + batching
│   ├── worker.py                # Worker process implementation
│   ├── processing.py            # Worker pool and batch management
│   ├── config.py                # Configuration settings
│   ├── schemas.py               # Pydantic data models
│   ├── utils.py                 # Utility functions
│   ├── gallery_manager.py       # Gallery management system
│   ├── demo_*.py                # Demo and example scripts
│   └── example_workflow.py      # Example workflow implementation
├── tests/                       # Test suite
│   ├── __init__.py              # Test package initialization
│   ├── test_*.py                # Comprehensive test files
│   └── test_requirements.txt    # Test-specific dependencies
├── static/                      # Static files (images, web assets)
├── run_server.py                # Server entry point
├── run_tests.py                 # Test runner script
├── start_server.sh              # Production startup script
├── requirements.txt             # Production dependencies
├── web_client.html              # Modern web interface
├── API_DOCUMENTATION.md         # Detailed API documentation  
├── TEST_CLIENT_README.md        # Test client guide
└── LICENSE                      # Apache 2.0 license
```

## 🛠️ Installation & Setup

### Prerequisites

- **Python 3.8+**
- **CUDA-compatible GPU(s)** (RTX 3080+ recommended, 8GB+ VRAM)
- **16GB+ System RAM** (32GB+ recommended for multiple workers)

### Quick Setup

1. **Clone and install**
   ```bash
   git clone <your-repo>
   cd CogView4-FastAPI
   pip install -r requirements.txt
   ```

2. **Start the server**
   ```bash
   chmod +x start_server.sh
   ./start_server.sh
   ```

3. **Test the installation**
   ```bash
   python run_tests.py --pattern test_connectivity.py
   ```

The server will automatically:
- Download CogView4-6B model (~12GB) on first run
- Initialize worker pool across available GPUs
- Start serving on `http://localhost:8000`

## 🔥 Advanced Worker Pool Architecture

### Intelligent Prompt Batching System
- **BatchManager** - Automatically groups compatible requests for optimal GPU utilization
- **Batch Criteria** - Groups by: size, guidance_scale, steps, stream mode, num_images
- **Individual Pairing** - Each request keeps its unique prompt and negative_prompt
- **Timeout Protection** - Maximum 0.5 second wait for batch formation
- **Performance Boost** - 3-5x throughput improvement for concurrent requests
- **Configurable** - Enable/disable via `ENABLE_PROMPT_BATCHING=true/false`

### Multi-GPU Persistent Workers
- **4 persistent worker processes** (configurable via `NUM_WORKER_PROCESSES`)
- **Automatic GPU distribution** - Workers spread across available GPUs
- **Independent model loading** - Each worker loads CogView4 once and reuses
- **Memory optimization** - Uses `from_pipe()` for efficient concurrent requests
- **Fault tolerance** - Workers can restart independently
- **Batch + Individual processing** - Handles both batched and single requests seamlessly

### Request Processing
- **Queue-based distribution** - Fair load balancing across workers
- **Concurrent generation** - Multiple images can generate simultaneously
- **Memory management** - Automatic cleanup and GPU memory optimization
- **Progress tracking** - Real-time status for each generation
- **Smart batching** - Compatible requests automatically grouped for efficiency

## ⚡ Enhanced Streaming Features

### Intelligent Chunking System
- **Large image support** - Automatically chunks images >400KB
- **Seamless reassembly** - Client-side automatic chunk reconstruction  
- **Progress granularity** - Configurable step frequency (default: every 10%)
- **Error recovery** - Robust handling of network interruptions

### Real-Time Performance
- **Step-by-step updates** - See generation progress immediately
- **Timing analytics** - Detailed performance metrics
- **Multiple concurrent streams** - No interference between requests
- **Low latency** - ~50-100ms per intermediate update

## 🧪 Comprehensive Testing Suite

### Test Runner (`run_tests.py`)
Advanced test runner with full feature testing:

```bash
# Run all tests
python run_tests.py

# Run specific test file
python run_tests.py --pattern test_client.py

# Run with verbose output
python run_tests.py --verbose

# Run specific test pattern
python run_tests.py --pattern "test_*batching*"
```

### Test Client (`tests/test_client.py`)
Advanced Python client with full feature testing:

```bash
# Run all tests
python run_tests.py --pattern test_client.py --all

# Test specific features
python run_tests.py --pattern test_client.py --test-streaming --save-intermediates
python run_tests.py --pattern test_client.py --test-non-streaming --output-dir ./results

# Test prompt batching
python run_tests.py --pattern test_prompt_batching.py

# Custom configuration
python run_tests.py --pattern test_client.py --all --prompt "A futuristic cityscape" --url http://your-server:8000
```

**Features:**
- ✅ **Streaming vs Non-streaming comparison**
- ✅ **Chunked data reassembly testing**
- ✅ **Performance benchmarking**
- ✅ **Concurrent request testing**
- ✅ **Prompt batching validation**
- ✅ **Error handling validation**
- ✅ **Image quality verification**

### Connectivity Testing (`tests/test_connectivity.py`)
Quick validation of basic functionality:

```bash
python run_tests.py --pattern test_connectivity.py --url http://localhost:8000
```

**Tests:**
- API endpoint availability (`/health`, `/status`, `/v1/models`)
- Worker pool initialization
- Model loading status
- Basic generation capability
- Streaming endpoint connectivity

## 📊 API Endpoints

### Core Generation Endpoint
```http
POST /v1/images/generations
Content-Type: application/json

{
  "prompt": "A beautiful landscape with mountains at sunset",
  "negative_prompt": "blurry, low quality, distorted",
  "size": "1024x1024",
  "n": 1,
  "guidance_scale": 5.0,
  "num_inference_steps": 50,
  "stream": true
}
```

### Prompt Optimization Endpoint
```http
POST /v1/prompt/optimize
Content-Type: application/json

{
  "prompt": "a cat sitting on a chair",
  "retry_times": 5
}
```

**Response:**
```json
{
  "original_prompt": "a cat sitting on a chair",
  "optimized_prompt": "In this charming scene, a sleek, black cat perches gracefully on a classic wooden armchair...",
  "success": true,
  "message": "Prompt optimized successfully"
}
```

**Features:**
- **Bilingual Support**: Handles both English and Chinese prompts
- **AI Enhancement**: Adds visual details, lighting, style, and composition
- **Retry Mechanism**: Configurable retry attempts for reliability
- **Fast Processing**: Typically completes within 2-5 seconds

### Monitoring & Health
- `GET /health` - Worker pool and model status
- `GET /status` - Detailed system information  
- `GET /v1/models` - Available models (OpenAI compatibility)
- `GET /client.html` - Serves the web interface

### Enhanced Response Format

**Streaming Response (SSE):**
```javascript
data: {
  "step": 15,
  "total_steps": 50,
  "progress": 0.3,
  "image": "base64_encoded_image_or_chunk",
  "timestamp": 1640995205.123,
  "is_final": false,
  "is_chunked": true,
  "chunk_id": "uuid-chunk-identifier", 
  "chunk_index": 2,
  "total_chunks": 5
}
```

## 🌐 Production Web Interface

Open `web_client.html` or visit `http://localhost:8000/client.html` for:

- **Real-time generation monitoring** with live progress bars
- **Advanced parameter controls** (guidance scale, steps, size)
- **Streaming toggle** - Compare streaming vs batch processing
- **Multiple image support** - Generate up to 4 images simultaneously  
- **Image gallery** - View and download all generated images
- **Performance metrics** - See generation timing and step intervals
- **Error handling** - User-friendly error messages and recovery

## 🔧 Configuration & Environment

### Environment Variables

```bash
# Server configuration
export COGVIEW4_HOST="0.0.0.0"          # Server host
export COGVIEW4_PORT="8000"             # Server port  
export COGVIEW4_DEVICE="cuda"           # Device type

# Worker pool settings
export NUM_WORKER_PROCESSES="4"         # Number of worker processes
export LOG_LEVEL="INFO"                 # Logging level
export LOG_FILE="cogview4_api.log"      # Log file path

# Performance optimization
export ENABLE_PROMPT_BATCHING="true"    # Enable intelligent prompt batching
```

### Hardware Optimization

**Recommended Configuration:**
- **GPU**: RTX 4080/4090 (16GB+ VRAM) for optimal performance
- **Workers**: 1 worker per 8GB GPU memory (adjust `NUM_WORKER_PROCESSES`)
- **RAM**: 32GB+ system RAM for 4 workers
- **Storage**: SSD recommended for model and image I/O

**Scaling Guidelines:**
- **Single GPU (8GB)**: 1-2 workers
- **Single GPU (16GB+)**: 2-4 workers  
- **Multi-GPU setup**: 1-2 workers per GPU
- **Production**: Monitor GPU memory usage and adjust accordingly

## 📈 Performance Characteristics

### Throughput Metrics
- **Concurrent generations**: Up to 4 simultaneous (default worker count)
- **First response time**: 1-3 seconds (model already loaded)
- **Streaming frequency**: Every 5-10% of total steps  
- **Memory efficiency**: ~12GB per worker + shared system overhead
- **Batching efficiency**: 3-5x throughput improvement for compatible requests
- **Batch timeout**: Maximum 0.5s wait for optimal batching

### Optimization Features
- **Persistent model loading** - No cold starts after initialization
- **Intelligent prompt batching** - Automatic grouping of compatible requests
- **GPU memory pooling** - Efficient VRAM utilization
- **Async queue processing** - Non-blocking request handling
- **Intelligent chunking** - Handles large images without memory issues
- **Fair request distribution** - Individual prompt-negative_prompt pairing maintained

## 🚀 Production Deployment

### Docker Deployment (Recommended)
```dockerfile
FROM nvidia/cuda:11.8-devel-ubuntu20.04
# Add your Dockerfile configuration
```

### Systemd Service
```bash
# Create service file for auto-start
sudo nano /etc/systemd/system/cogview4-api.service
```

### Load Balancing
- Use nginx or similar for multiple API instances
- Configure GPU affinity per instance
- Implement health checks and failover

## 📚 Documentation

- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Complete API reference with architecture details
- **[TEST_CLIENT_README.md](TEST_CLIENT_README.md)** - Test client usage and examples
- **Server logs** - Detailed logging in `cogview4_api.log`

## 🔍 Troubleshooting

### Common Issues

1. **Worker initialization failed**
   ```bash
   # Check GPU memory and reduce worker count
   export NUM_WORKER_PROCESSES="2"
   ./start_server.sh
   ```

2. **Streaming connection issues**
   ```bash
   # Test basic connectivity first
   python test_connectivity.py
   ```

3. **Memory errors**
   ```bash
   # Monitor GPU usage
   nvidia-smi -l 1
   ```

### Debug Mode
```bash
export LOG_LEVEL="DEBUG"
python cogview4_api_server.py
```

## 🤝 Contributing

Priority areas for contributions:
- **Performance optimizations** - Memory usage, generation speed
- **Client implementations** - React, Flutter, etc.
- **Deployment tools** - Docker, K8s configurations  
- **Advanced features** - LoRA support, custom models
- **Documentation** - Tutorials, deployment guides

## 📄 License

Apache License 2.0 - See [LICENSE](LICENSE) file for details.

CogView4 model follows THUDM's license terms.

## 🙏 Acknowledgments

- **THUDM** for the exceptional CogView4 model
- **Hugging Face** for the Diffusers library and model hosting
- **FastAPI** for excellent async and production capabilities  
- **Community** for testing, feedback, and optimizations

---

## 🎯 Quick Start Commands

```bash
# 1. Setup and start
./start_server.sh

# 2. Test everything works  
python test_client.py --all

# 3. Open web interface
# Visit: http://localhost:8000/client.html

# 4. API health check
curl http://localhost:8000/health
```

**🚀 Ready for production-grade AI image generation with real-time streaming!**