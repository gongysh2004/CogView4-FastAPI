- [1. CogView4 Image Generation API Server Documentation](#1-cogview4-image-generation-api-server-documentation)
  - [1.1. Overview](#11-overview)
  - [1.2. Architecture Overview](#12-architecture-overview)
  - [1.3. Core Components](#13-core-components)
    - [1.3.1. FastAPI Application Layer](#131-fastapi-application-layer)
    - [1.3.2. Prompt Batching System](#132-prompt-batching-system)
    - [1.3.3. WorkerPool Architecture](#133-workerpool-architecture)
    - [1.3.4. Worker Process Architecture](#134-worker-process-architecture)
  - [1.4. Request Flow Diagrams](#14-request-flow-diagrams)
    - [1.4.1. Prompt Batching Flow](#141-prompt-batching-flow)
    - [1.4.2. Streaming Request Flow](#142-streaming-request-flow)
    - [1.4.3. Non-Streaming Request Flow](#143-non-streaming-request-flow)
  - [1.5. Chunking System](#15-chunking-system)
    - [1.5.1. Server-Side Chunking](#151-server-side-chunking)
    - [1.5.2. Client-Side Assembly](#152-client-side-assembly)
  - [1.6. Data Models](#16-data-models)
    - [1.6.1. Request Models](#161-request-models)
    - [1.6.2. Streaming Data Models](#162-streaming-data-models)
  - [1.7. Performance Optimizations](#17-performance-optimizations)
    - [1.7.1. Intelligent Prompt Batching](#171-intelligent-prompt-batching)
    - [1.7.2. Model Loading Strategy](#172-model-loading-strategy)
    - [1.7.3. Memory Management](#173-memory-management)
    - [1.7.4. Concurrency Model](#174-concurrency-model)
  - [1.8. Health Monitoring](#18-health-monitoring)
    - [1.8.1. Model Loading Status](#181-model-loading-status)
    - [1.8.2. Health Endpoint Response](#182-health-endpoint-response)
  - [1.9. Error Handling](#19-error-handling)
    - [1.9.1. Worker-Level Error Handling](#191-worker-level-error-handling)
    - [1.9.2. Client Error Handling](#192-client-error-handling)
  - [1.10. API Endpoints](#110-api-endpoints)
    - [1.10.1. Image Generation](#1101-image-generation)
    - [1.10.2. Health Check](#1102-health-check)
    - [1.10.3. Status Information](#1103-status-information)
    - [1.10.4. Web Client](#1104-web-client)
  - [1.11. Deployment Considerations](#111-deployment-considerations)
    - [1.11.1. Hardware Requirements](#1111-hardware-requirements)
    - [1.11.2. Environment Variables](#1112-environment-variables)
    - [1.11.3. Scaling Strategies](#1113-scaling-strategies)
  - [1.12. Security Considerations](#112-security-considerations)

# 1. CogView4 Image Generation API Server Documentation

## 1.1. Overview

The CogView4 Image Generation API Server is a high-performance, OpenAI-compatible image generation service built with FastAPI. It implements a persistent worker pool architecture with multiprocessing for true concurrent image generation, **intelligent prompt batching for GPU efficiency**, streaming capabilities, and intelligent chunking for large images.

## 1.2. Architecture Overview

```mermaid
graph TB
    subgraph "Client Layer"
        WC[Web Client]
        API_CLIENT[API Clients]
    end
    
    subgraph "FastAPI Server"
        MAIN[Main Process]
        ROUTES[API Routes]
        HEALTH[Health Check]
        SSE[SSE Streaming]
        BM[BatchManager]
    end
    
    subgraph "Worker Pool"
        WP[WorkerPool Manager]
        RQ[Request Queue]
        ResQ[Result Queue]
        
        subgraph "Worker Processes"
            W1[Worker 1<br/>GPU 0]
            W2[Worker 2<br/>GPU 1]
            W3[Worker 3<br/>GPU 2]
            W4[Worker 4<br/>GPU 3]
        end
    end
    
    subgraph "Model Layer"
        M1[CogView4 Pipeline 1]
        M2[CogView4 Pipeline 2]
        M3[CogView4 Pipeline 3]
        M4[CogView4 Pipeline 4]
    end
    
    WC -->|HTTP Requests| MAIN
    API_CLIENT -->|HTTP Requests| MAIN
    MAIN --> ROUTES
    ROUTES --> BM
    BM --> WP
    WP --> RQ
    RQ --> W1
    RQ --> W2
    RQ --> W3
    RQ --> W4
    
    W1 --> M1
    W2 --> M2
    W3 --> M3
    W4 --> M4
    
    W1 --> ResQ
    W2 --> ResQ
    W3 --> ResQ
    W4 --> ResQ
    
    ResQ --> WP
    WP --> SSE
    SSE -->|Server-Sent Events| WC
    WP -->|JSON Response| API_CLIENT
    
    MAIN --> HEALTH
    HEALTH -->|Model Status| WC
```

## 1.3. Core Components

### 1.3.1. FastAPI Application Layer

- **Main Process**: Handles HTTP requests and routes
- **API Routes**: OpenAI-compatible endpoints (`/v1/images/generations`)
- **Health Monitoring**: Real-time status of worker pool and model loading
- **SSE Streaming**: Server-Sent Events for real-time progress updates
- **BatchManager**: Intelligent batching of compatible requests for GPU efficiency

### 1.3.2. Prompt Batching System

```mermaid
classDiagram
    class BatchManager {
        +batch_timeout: float
        +max_batch_size: int
        +pending_requests: Dict
        +batch_timers: Dict
        +add_request(request)
        +get_batch_key(request)
        +check_timeouts()
        +flush_pending_batches()
    }
    
    class BatchedGenerationRequest {
        +batch_id: str
        +prompts: List[str]
        +negative_prompts: List[Optional[str]]
        +request_ids: List[str]
        +num_images: int
        +width: int
        +height: int
        +guidance_scale: float
        +num_inference_steps: int
        +stream: bool
    }
    
    class GenerationRequest {
        +request_id: str
        +prompt: str
        +negative_prompt: Optional[str]
        +width: int
        +height: int
        +guidance_scale: float
        +num_inference_steps: int
        +num_images: int
        +stream: bool
    }
    
    BatchManager --> GenerationRequest : receives
    BatchManager --> BatchedGenerationRequest : creates
```

**Batching Logic:**
- Requests are grouped by compatible parameters: `(width, height, guidance_scale, num_inference_steps, stream, num_images)`
- Maximum batch size: 8 requests (configurable)
- Batch timeout: 0.5 seconds (configurable)
- Each request maintains its individual prompt and negative_prompt pairing
- Results are properly distributed back to individual requests

### 1.3.3. WorkerPool Architecture

```mermaid
classDiagram
    class WorkerPool {
        +model_path: str
        +num_workers: int
        +request_queue: Queue
        +result_queue: Queue
        +worker_model_loaded: Dict
        +batch_manager: BatchManager
        +batch_enabled: bool
        +submit_streaming_request()
        +submit_non_streaming_request()
        +all_models_loaded()
        +shutdown()
    }
    
    class GenerationRequest {
        +request_id: str
        +prompt: str
        +negative_prompt: str
        +width: int
        +height: int
        +guidance_scale: float
        +num_inference_steps: int
        +stream: bool
    }
    
    class GenerationResult {
        +request_id: str
        +result_type: str
        +data: Any
    }
    
    WorkerPool --> GenerationRequest : creates
    WorkerPool --> GenerationResult : receives
    WorkerPool --> BatchManager : uses
```

### 1.3.4. Worker Process Architecture

Each worker process:
- **Loads model once**: CogView4 pipeline with quantization
- **Handles multiple requests**: Uses `from_pipe()` for memory efficiency
- **GPU assignment**: Distributed across available GPUs
- **Independent operation**: No shared state between workers
- **Batch processing**: Can handle both individual and batched requests
- **Negative prompt handling**: Automatically converts `None` values to empty strings

## 1.4. Request Flow Diagrams

### 1.4.1. Prompt Batching Flow

```mermaid
sequenceDiagram
    participant C1 as Client 1
    participant C2 as Client 2
    participant C3 as Client 3
    participant F as FastAPI
    participant BM as BatchManager
    participant WP as WorkerPool
    participant W as Worker
    participant M as Model
    
    Note over C1,C3: Multiple clients send compatible requests
    C1->>F: POST prompt="sunset", size=1024x1024, steps=50
    C2->>F: POST prompt="forest", size=1024x1024, steps=50
    C3->>F: POST prompt="mountain", size=1024x1024, steps=50
    
    F->>BM: Add request 1 to batch
    F->>BM: Add request 2 to batch
    F->>BM: Add request 3 to batch
    
    Note over BM: Batch ready (size=3 or timeout=0.5s)
    BM->>WP: Submit BatchedGenerationRequest
    
    WP->>W: Send batch to worker
    W->>W: Preprocess negative_prompts (None -> "")
    W->>M: Generate with prompts=["sunset","forest","mountain"]
    
    activate M
    loop For each inference step
        M->>W: Step callback with all images
        W->>W: Distribute images to request IDs
        W->>WP: Send individual results
        WP->>F: Stream to respective clients
        F->>C1: SSE: sunset image step
        F->>C2: SSE: forest image step  
        F->>C3: SSE: mountain image step
    end
    deactivate M
    
    W->>WP: Batch completion
    WP->>F: Individual completions
    F->>C1: Complete
    F->>C2: Complete
    F->>C3: Complete
```

### 1.4.2. Streaming Request Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant F as FastAPI
    participant WP as WorkerPool
    participant W as Worker
    participant M as Model
    
    C->>F: POST /v1/images/generations (stream=true)
    F->>WP: submit_streaming_request()
    WP->>W: Put request in queue
    
    activate W
    W->>M: Generate with step callback
    
    loop For each inference step
        M->>W: Step callback triggered
        W->>W: Decode latents to image
        W->>W: Check image size
        
        alt Image > 400KB
            W->>W: Split into chunks
            loop For each chunk
                W->>WP: Send chunk via result queue
                WP->>F: Stream chunk via SSE
                F->>C: data: {chunk_data}
            end
        else Image <= 400KB
            W->>WP: Send complete image
            WP->>F: Stream image via SSE
            F->>C: data: {image_data}
        end
    end
    
    W->>WP: Send completion signal
    WP->>F: Stream [DONE]
    F->>C: data: [DONE]
    deactivate W
```

### 1.4.3. Non-Streaming Request Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant F as FastAPI
    participant WP as WorkerPool
    participant W as Worker
    participant M as Model
    
    C->>F: POST /v1/images/generations (stream=false)
    F->>WP: submit_non_streaming_request()
    WP->>W: Put request in queue
    
    activate W
    W->>M: Generate images
    M->>W: Return final images
    W->>W: Convert to base64
    W->>WP: Send results via queue
    WP->>F: Return image data
    F->>C: JSON response with images
    deactivate W
```

## 1.5. Chunking System

### 1.5.1. Server-Side Chunking

```mermaid
flowchart TD
    IMG[Generated Image] --> SIZE{Size > 400KB?}
    
    SIZE -->|No| SINGLE[Send as single chunk]
    SIZE -->|Yes| CHUNK[Split into 400KB chunks]
    
    CHUNK --> LOOP[For each chunk]
    LOOP --> META[Add chunk metadata]
    META --> SEND[Send via SSE]
    SEND --> MORE{More chunks?}
    MORE -->|Yes| LOOP
    MORE -->|No| DONE[Complete]
    
    SINGLE --> SEND
    SEND --> DONE
```

### 1.5.2. Client-Side Assembly

```mermaid
flowchart TD
    SSE[Receive SSE Data] --> CHUNKED{is_chunked?}
    
    CHUNKED -->|No| DISPLAY[Display image directly]
    CHUNKED -->|Yes| STORE[Store in chunkStorage]
    
    STORE --> CHECK{All chunks received?}
    CHECK -->|No| WAIT[Wait for more chunks]
    CHECK -->|Yes| ASSEMBLE[Concatenate chunks]
    
    ASSEMBLE --> DISPLAY
    WAIT --> SSE
    DISPLAY --> CLEANUP[Cleanup storage]
```

## 1.6. Data Models

### 1.6.1. Request Models

```python
class ImageGenerationRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = None
    n: int = 1  # Number of images
    size: str = "1024x1024"
    stream: bool = False
    guidance_scale: float = 5.0
    num_inference_steps: int = 50
    response_format: str = "b64_json"
```

### 1.6.2. Streaming Data Models

```python
class StreamingImageData(BaseModel):
    step: int
    total_steps: int
    progress: float
    image: Optional[str] = None
    timestamp: float
    is_final: bool = False
    # Chunking support
    is_chunked: bool = False
    chunk_id: Optional[str] = None
    chunk_index: Optional[int] = None
    total_chunks: Optional[int] = None
```

## 1.7. Performance Optimizations

### 1.7.1. Intelligent Prompt Batching

```mermaid
graph TD
    REQ1[Request 1: "sunset"] --> BM[BatchManager]
    REQ2[Request 2: "forest"] --> BM
    REQ3[Request 3: "mountain"] --> BM
    
    BM --> CHECK{Compatible?}
    CHECK -->|Yes| BATCH[Create Batch]
    CHECK -->|No| SEPARATE[Separate Processing]
    
    BATCH --> SINGLE[Single GPU Inference]
    SINGLE --> DISTRIBUTE[Distribute Results]
    
    DISTRIBUTE --> OUT1[Client 1: sunset images]
    DISTRIBUTE --> OUT2[Client 2: forest images]
    DISTRIBUTE --> OUT3[Client 3: mountain images]
    
    SEPARATE --> IND1[Individual Processing]
    SEPARATE --> IND2[Individual Processing]
```

**Batching Benefits:**
- **GPU Efficiency**: Single inference call for multiple prompts reduces GPU overhead
- **Memory Optimization**: Shared model execution for compatible requests
- **Throughput Increase**: Up to 3-5x improvement for batched requests
- **Fair Processing**: Individual prompt-negative_prompt pairing maintained
- **Timeout Protection**: 0.5s maximum wait ensures responsiveness

**Batch Compatibility Criteria:**
- Same image dimensions (width × height)
- Same guidance scale
- Same number of inference steps
- Same streaming preference
- Same number of images per prompt

### 1.7.2. Model Loading Strategy

```mermaid
graph TD
    START[Worker Startup] --> CUDA[Initialize CUDA Device]
    CUDA --> LOAD[Load Base Pipeline Once]
    LOAD --> QUANT[Apply INT8 Quantization]
    QUANT --> READY[Worker Ready]
    
    READY --> REQ[Receive Request/Batch]
    REQ --> PIPE[Create from_pipe instance]
    PIPE --> GEN[Generate Images]
    GEN --> CLEANUP[Cleanup Pipeline Instance]
    CLEANUP --> REQ
```

### 1.7.3. Memory Management

- **Quantization**: INT8 weight-only quantization for text encoder and transformer
- **from_pipe()**: Memory-efficient pipeline instances per request
- **GPU Distribution**: Workers distributed across available GPUs
- **Automatic Cleanup**: Pipeline instances cleaned after each request
- **Batch Processing**: Shared memory usage for compatible requests
- **Negative Prompt Handling**: Automatic None-to-empty-string conversion

### 1.7.4. Concurrency Model

```mermaid
graph LR
    subgraph "Process-Based Concurrency"
        MP[Main Process] --> W1[Worker 1]
        MP --> W2[Worker 2]
        MP --> W3[Worker 3]
        MP --> W4[Worker 4]
    end
    
    subgraph "Benefits"
        GIL[No GIL Limitations]
        CUDA[Isolated CUDA Contexts]
        FAULT[Fault Isolation]
        SCALE[True Parallelism]
    end
```

## 1.8. Health Monitoring

### 1.8.1. Model Loading Status

The API tracks model loading across all workers:

```python
def all_models_loaded(self) -> bool:
    """Returns True only when ALL workers have loaded their models"""
    loaded_workers = sum(1 for loaded in self.worker_model_loaded.values() if loaded)
    total_workers = len(self.workers)
    return loaded_workers == total_workers and total_workers > 0
```

### 1.8.2. Health Endpoint Response

```json
{
  "status": "healthy",
  "worker_pool_initialized": true,
  "active_workers": 4,
  "model_loaded": true,
  "concurrent_support": true,
  "architecture": "Persistent worker pool with from_pipe"
}
```

## 1.9. Error Handling

### 1.9.1. Worker-Level Error Handling

```mermaid
flowchart TD
    REQ[Process Request] --> TRY{Try}
    TRY -->|Success| RESULT[Send Result]
    TRY -->|Error| CATCH[Catch Exception]
    
    CATCH --> LOG[Log Error]
    LOG --> ERR_RESULT[Send Error Result]
    ERR_RESULT --> CLEANUP[Cleanup Resources]
    
    RESULT --> CLEANUP
    CLEANUP --> READY[Ready for Next Request]
```

### 1.9.2. Client Error Handling

- **Network Errors**: Retry logic and connection management
- **Parsing Errors**: Graceful handling of malformed SSE data
- **Chunk Assembly**: Missing chunk detection and recovery
- **Timeout Handling**: Request timeout and cleanup

## 1.10. API Endpoints

### 1.10.1. Image Generation
- **Endpoint**: `POST /v1/images/generations`
- **Compatible**: OpenAI Images API
- **Streaming**: Server-Sent Events support
- **Chunking**: Automatic for large images

### 1.10.2. Health Check
- **Endpoint**: `GET /health`
- **Purpose**: Monitor worker pool and model status
- **Real-time**: Updated as workers load models

### 1.10.3. Status Information
- **Endpoint**: `GET /status`
- **Purpose**: Detailed server information
- **Features**: Lists all capabilities and architecture

### 1.10.4. Web Client
- **Endpoint**: `GET /client.html`
- **Purpose**: Interactive web interface
- **Features**: Real-time streaming, chunk assembly, progress tracking

## 1.11. Deployment Considerations

### 1.11.1. Hardware Requirements

- **GPU Memory**: 12GB+ VRAM per worker recommended
- **System RAM**: 16GB+ for model loading and processing
- **CPU**: Multi-core for handling concurrent requests
- **Storage**: Fast SSD for model loading

### 1.11.2. Environment Variables

```bash
# Logging configuration
LOG_LEVEL=INFO
LOG_FILE=cogview4_api.log

# Worker configuration
NUM_WORKER_PROCESSES=4

# Prompt batching configuration
ENABLE_PROMPT_BATCHING=true

# CUDA configuration
CUDA_LAUNCH_BLOCKING=1
CUDA_DEVICE_ORDER=PCI_BUS_ID
```

**Configuration Details:**

- **`ENABLE_PROMPT_BATCHING`**: Enable/disable intelligent prompt batching (default: `true`)
  - `true`: Requests with compatible parameters are batched together
  - `false`: All requests processed individually
- **`NUM_WORKER_PROCESSES`**: Number of worker processes (default: `4`)
  - Recommend 1-2 workers per GPU
  - Each worker loads ~12GB model into VRAM
- **`LOG_LEVEL`**: Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`)
- **`LOG_FILE`**: Log file path for persistent logging

### 1.11.3. Scaling Strategies

1. **Vertical Scaling**: Increase GPU memory and add more GPUs
2. **Worker Tuning**: Adjust `NUM_WORKER_PROCESSES` based on GPU count
3. **Load Balancing**: Multiple server instances behind a load balancer
4. **Chunking Tuning**: Adjust chunk size based on network capacity

## 1.12. Security Considerations

- **Input Validation**: Pydantic models with constraints
- **Resource Limits**: Request timeouts and memory limits
- **CORS Configuration**: Configurable cross-origin policies
- **Error Sanitization**: Safe error message exposure

This architecture provides a robust, scalable, and efficient image generation service with true concurrent processing, intelligent resource management, and excellent user experience through streaming capabilities. 