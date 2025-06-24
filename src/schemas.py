from dataclasses import dataclass
from typing import Any, List, Optional
from pydantic import BaseModel, Field


@dataclass
class GenerationRequest:
    """Request data structure for worker processes"""
    request_id: str
    prompt: str
    negative_prompt: Optional[str]
    width: int
    height: int
    guidance_scale: float
    num_inference_steps: int
    num_images: int
    stream: bool
    seed: Optional[int] = None


@dataclass
class BatchedGenerationRequest:
    """Batched request data structure for worker processes"""
    batch_id: str
    prompts: List[str]
    negative_prompts: List[Optional[str]]
    request_ids: List[str]  # Maps to individual requests
    num_images: int  # Images per prompt (same for all requests in batch)
    width: int
    height: int
    guidance_scale: float
    num_inference_steps: int
    stream: bool
    seeds: List[Optional[int]] = None


@dataclass
class GenerationResult:
    """Result data structure from worker processes"""
    request_id: str
    result_type: str  # 'streaming_step', 'completed', 'error'
    data: Any = None


class ImageGenerationRequest(BaseModel):
    """OpenAI-compatible image generation request"""
    prompt: str = Field(..., description="Text prompt for image generation")
    negative_prompt: Optional[str] = Field(None, description="Negative prompt to avoid certain elements")
    n: int = Field(1, description="Number of images to generate", ge=1, le=4)
    size: str = Field("1024x1024", description="Image size (width x height)")
    quality: str = Field("standard", description="Image quality")
    style: str = Field("natural", description="Image style")
    response_format: str = Field("b64_json", description="Response format")
    user: Optional[str] = Field(None, description="User identifier")
    stream: bool = Field(False, description="Whether to stream intermediate results")
    guidance_scale: float = Field(5.0, description="Guidance scale for generation", ge=1.0, le=20.0)
    num_inference_steps: int = Field(50, description="Number of inference steps", ge=10, le=150)
    seed: Optional[int] = Field(None, description="Random seed for reproducible generation")


class ImageData(BaseModel):
    """Image data response"""
    b64_json: Optional[str] = None
    url: Optional[str] = None
    revised_prompt: Optional[str] = None
    seed: Optional[int] = None


class ImageGenerationResponse(BaseModel):
    """OpenAI-compatible image generation response"""
    created: int
    data: List[ImageData]


class StreamingImageData(BaseModel):
    """Streaming image data for SSE"""
    step: int
    total_steps: int
    progress: float
    image: Optional[str] = None  # base64 encoded image
    timestamp: float
    is_final: bool = False
    is_chunked: bool = False
    chunk_id: Optional[str] = None
    chunk_index: Optional[int] = None
    total_chunks: Optional[int] = None
    image_index: Optional[int] = None
    total_images: Optional[int] = None
    seed: Optional[int] = None


class PromptOptimizationRequest(BaseModel):
    """Request for prompt optimization"""
    prompt: str = Field(..., description="Original prompt to be optimized")
    retry_times: int = Field(5, description="Number of retry attempts for optimization", ge=1, le=10)


class PromptOptimizationResponse(BaseModel):
    """Response for prompt optimization"""
    original_prompt: str
    optimized_prompt: str
    success: bool
    message: str = "Prompt optimized successfully"


class GalleryImage(BaseModel):
    """Gallery image data structure"""
    id: int
    image_url: str
    prompt: str
    negative_prompt: Optional[str] = None
    size: str
    seed: Optional[int] = None
    timestamp: float
    guidance_scale: float = 5.0
    num_inference_steps: int = 20


class GalleryResponse(BaseModel):
    """Response for gallery data"""
    images: List[GalleryImage]
    total_count: int
    success: bool = True


class PromptTranslationRequest(BaseModel):
    """Request for prompt translation"""
    prompt: str = Field(..., description="Original prompt to be translated")
    retry_times: int = Field(5, description="Number of retry attempts for translation", ge=1, le=10)


class PromptTranslationResponse(BaseModel):
    """Response for prompt translation"""
    original_prompt: str
    translated_prompt: str
    success: bool
    message: str = "Prompt translated successfully" 