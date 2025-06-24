import base64
import io
import logging
import multiprocessing as mp
import os
import queue
import time
from typing import Dict

import torch
from PIL import Image
from diffusers import CogView4Pipeline, CogView4Transformer2DModel
# Handle both relative and absolute imports
try:
    from .schemas import (BatchedGenerationRequest, GenerationRequest,
                         GenerationResult)
except ImportError:
    from schemas import (BatchedGenerationRequest, GenerationRequest,
                         GenerationResult)
from torchao.quantization import int8_weight_only, quantize_
from transformers import GlmModel


def worker_process(worker_id: int, model_path: str, request_queue: mp.Queue, result_queue: mp.Queue, shutdown_event: mp.Event, worker_model_loaded: Dict[int, bool]):
    """
    Persistent worker process that loads the model once and handles multiple requests.
    Each worker can handle one request at a time but can use from_pipe for concurrent sub-requests.
    """
    # Set up logging for this worker
    worker_logger = logging.getLogger(f"worker_{worker_id}")

    # Set up logging for this worker process (spawn doesn't inherit main process logging)
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_file = os.getenv('LOG_FILE', 'cogview4_api.log')

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=f'%(asctime)s - Worker{worker_id} - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file)
        ],
        force=True  # Override any existing configuration
    )

    worker_logger.info(f"Worker {worker_id} starting up with proper logging configured...")

    # Add delay between worker startups to avoid CUDA initialization conflicts
    time.sleep(worker_id * 3.0)

    # Set CUDA environment variables for this process
    os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
    os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'

    if not torch.cuda.is_available():
        worker_logger.error(f"Worker {worker_id}: CUDA not available. This worker will exit.")
        return

    try:
        try:
            torch.cuda.init()
            num_gpus = torch.cuda.device_count()
            gpu_id = worker_id % num_gpus
            device = f"cuda:{gpu_id}"
            worker_logger.info(f"Worker {worker_id}: Using {device} (GPU {gpu_id} of {num_gpus} available)")
            torch.cuda.set_device(gpu_id)
            torch.cuda.empty_cache()

            with torch.cuda.device(gpu_id):
                test_tensor = torch.tensor([1.0], device=device)
                test_result = test_tensor + 1
                del test_tensor, test_result
                torch.cuda.empty_cache()
            worker_logger.info(f"Worker {worker_id}: CUDA device {gpu_id} initialized successfully")

        except Exception as cuda_error:
            worker_logger.error(f"Worker {worker_id}: CUDA initialization failed: {cuda_error}")
            return

        try:
            worker_logger.info(f"Worker {worker_id}: Loading model on {device}...")
            text_encoder = GlmModel.from_pretrained(model_path, subfolder="text_encoder", torch_dtype=torch.bfloat16)
            transformer = CogView4Transformer2DModel.from_pretrained(model_path, subfolder="transformer", torch_dtype=torch.bfloat16)
            quantize_(text_encoder, int8_weight_only())
            quantize_(transformer, int8_weight_only())
            base_pipeline = CogView4Pipeline.from_pretrained(
                model_path,
                text_encoder=text_encoder,
                transformer=transformer,
                torch_dtype=torch.bfloat16,
                low_cpu_mem_usage=True
            )
            base_pipeline.to(device)
            worker_logger.info(f"Worker {worker_id}: Successfully loaded base pipeline on {device}")
            worker_model_loaded[worker_id] = True
            worker_logger.info(f"Worker {worker_id}: Model loading status updated to True")

        except Exception as model_error:
            worker_logger.error(f"Worker {worker_id}: Failed to load model on {device}: {model_error}")
            worker_model_loaded[worker_id] = False
            return

        active_pipelines = {}

        def get_pipeline_for_request(request_id: str) -> CogView4Pipeline:
            if request_id not in active_pipelines:
                try:
                    with torch.cuda.device(gpu_id):
                        pipeline: CogView4Pipeline = CogView4Pipeline.from_pipe(base_pipeline)
                        pipeline.set_progress_bar_config(disable=False, desc=f"Worker {worker_id}")
                        base_scheduler = base_pipeline.scheduler
                        scheduler_class = base_scheduler.__class__
                        scheduler_config = base_scheduler.config
                        new_scheduler = scheduler_class.from_config(scheduler_config)
                        pipeline.scheduler = new_scheduler
                        active_pipelines[request_id] = pipeline
                        worker_logger.debug(f"Worker {worker_id}: Created pipeline instance for request {request_id} on {device}")
                except Exception as pipe_error:
                    worker_logger.error(f"Worker {worker_id}: Failed to create pipeline for request {request_id}: {pipe_error}")
                    raise
            return active_pipelines[request_id]

        def cleanup_pipeline(request_id: str):
            if request_id in active_pipelines:
                try:
                    with torch.cuda.device(gpu_id):
                        del active_pipelines[request_id]
                        torch.cuda.empty_cache()
                    worker_logger.debug(f"Worker {worker_id}: Cleaned up pipeline for request {request_id}")
                except Exception as cleanup_error:
                    worker_logger.warning(f"Worker {worker_id}: Error during cleanup: {cleanup_error}")

        def create_step_callback(request_info):
            def step_callback(pipeline_instance, step_index, timestep, callback_kwargs):
                try:
                    latents = callback_kwargs.get("latents")
                    if latents is not None:
                        with torch.no_grad():
                            try:
                                with torch.cuda.device(gpu_id):
                                    latents_for_decode = latents.to(pipeline_instance.vae.dtype) / pipeline_instance.vae.config.scaling_factor
                                    decoded_image = pipeline_instance.vae.decode(latents_for_decode, return_dict=False)[0]
                                    decoded_image = pipeline_instance.image_processor.postprocess(decoded_image, output_type="pil")

                                    if isinstance(decoded_image, list) and len(decoded_image) > 0:
                                        is_final_step = step_index == request_info['num_inference_steps'] - 1
                                        for image_idx, image in enumerate(decoded_image):
                                            buffer = io.BytesIO()
                                            if is_final_step:
                                                image.save(buffer, format='PNG', optimize=True)
                                            else:
                                                if image.mode in ('RGBA', 'LA', 'P'):
                                                    rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                                                    if image.mode == 'P':
                                                        image = image.convert('RGBA')
                                                    rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                                                    image = rgb_image
                                                image.save(buffer, format='JPEG', quality=90, optimize=True)
                                            buffer.seek(0)
                                            image_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                                            send_chunked_image(image_b64, step_index, is_final_step, image_idx, request_info)
                            except Exception as decode_error:
                                worker_logger.warning(f"Worker {worker_id}: Error decoding step {step_index}: {decode_error}")
                except Exception as e:
                    worker_logger.error(f"Worker {worker_id}: Error in step callback: {e}")
                    if 'request_ids' in request_info:
                        for request_id in request_info['request_ids']:
                            result_queue.put(GenerationResult(request_id=request_id, result_type='error', data={'error': str(e)}))
                    else:
                        result_queue.put(GenerationResult(request_id=request_info['request_id'], result_type='error', data={'error': str(e)}))
                return callback_kwargs
            return step_callback

        def send_chunked_image(image_b64: str, step_index: int, is_final_step: bool, image_idx: int, request_info: dict, max_chunk_size: int = 400 * 1024):
            target_request_ids = request_info.get('request_ids', [request_info.get('request_id')])
            seed = request_info.get('seed')
            for request_id in target_request_ids:
                if not request_id: continue
                if len(image_b64) <= max_chunk_size:
                    result = GenerationResult(
                        request_id=request_id, result_type='streaming_step',
                        data={'step': step_index, 'progress': (step_index + 1) / request_info['num_inference_steps'], 'image': image_b64, 'is_final': is_final_step, 'timestamp': time.time(), 'is_chunked': False, 'image_index': image_idx, 'total_images': request_info['num_images'], 'seed': seed}
                    )
                    result_queue.put(result)
                else:
                    chunk_id = f"{request_id}_step_{step_index}_img_{image_idx}_{int(time.time() * 1000)}"
                    total_chunks = (len(image_b64) + max_chunk_size - 1) // max_chunk_size
                    for chunk_index in range(total_chunks):
                        start_pos, end_pos = chunk_index * max_chunk_size, min((chunk_index + 1) * max_chunk_size, len(image_b64))
                        chunk_data = image_b64[start_pos:end_pos]
                        result = GenerationResult(
                            request_id=request_id, result_type='streaming_step',
                            data={'step': step_index, 'progress': (step_index + 1) / request_info['num_inference_steps'], 'image': chunk_data, 'is_final': is_final_step, 'timestamp': time.time(), 'is_chunked': True, 'chunk_id': chunk_id, 'chunk_index': chunk_index, 'total_chunks': total_chunks, 'image_index': image_idx, 'total_images': request_info['num_images'], 'seed': seed}
                        )
                        result_queue.put(result)
            worker_logger.debug(f"Worker {worker_id}: Sent image for step {step_index}, image {image_idx + 1}/{request_info['num_images']} to {len(target_request_ids)} request(s)")

        def process_streaming_request(gen_request: GenerationRequest):
            try:
                pipeline: CogView4Pipeline = get_pipeline_for_request(gen_request.request_id)
                with torch.cuda.device(gpu_id):
                    # Use provided seed or generate a random one
                    seed = gen_request.seed if gen_request.seed is not None else int(time.time() * 1000) % (2**32)
                    generator = torch.Generator(device=device).manual_seed(seed)
                    request_info = {'request_id': gen_request.request_id, 'num_inference_steps': gen_request.num_inference_steps, 'num_images': gen_request.num_images, 'seed': seed}
                    pipeline(
                        prompt=gen_request.prompt, negative_prompt=gen_request.negative_prompt, width=gen_request.width, height=gen_request.height,
                        guidance_scale=gen_request.guidance_scale, num_inference_steps=gen_request.num_inference_steps, num_images_per_prompt=gen_request.num_images,
                        generator=generator, callback_on_step_end=create_step_callback(request_info), callback_on_step_end_tensor_inputs=["latents"]
                    )
                result_queue.put(GenerationResult(request_id=gen_request.request_id, result_type='completed', data=None))
                worker_logger.debug(f"Worker {worker_id}: Streaming request {gen_request.request_id} completed with seed {seed}")
            except Exception as e:
                worker_logger.error(f"Worker {worker_id}: Error in streaming request: {e}")
                result_queue.put(GenerationResult(request_id=gen_request.request_id, result_type='error', data={'error': str(e)}))
            finally:
                cleanup_pipeline(gen_request.request_id)

        def process_batched_streaming_request(batch_request: BatchedGenerationRequest):
            pipeline_id = batch_request.batch_id
            try:
                pipeline = get_pipeline_for_request(pipeline_id)
                with torch.cuda.device(gpu_id):
                    # Use provided seeds or generate random ones
                    if batch_request.seeds is None:
                        seeds = [int(time.time() * 1000 + i) % (2**32) for i in range(len(batch_request.prompts))]
                    else:
                        seeds = [seed if seed is not None else int(time.time() * 1000 + i) % (2**32) for i, seed in enumerate(batch_request.seeds)]
                    
                    # For batched requests, we'll use the first seed for the generator
                    # In a more sophisticated implementation, you might want to handle multiple seeds differently
                    generator = torch.Generator(device=device).manual_seed(seeds[0])
                    request_info = {'request_ids': batch_request.request_ids, 'num_inference_steps': batch_request.num_inference_steps, 'num_images': batch_request.num_images, 'seed': seeds[0]}
                    processed_negative_prompts = [p if p is not None else "" for p in batch_request.negative_prompts]
                    pipeline(
                        prompt=batch_request.prompts, negative_prompt=processed_negative_prompts, width=batch_request.width, height=batch_request.height,
                        guidance_scale=batch_request.guidance_scale, num_inference_steps=batch_request.num_inference_steps, num_images_per_prompt=batch_request.num_images,
                        generator=generator, callback_on_step_end=create_step_callback(request_info), callback_on_step_end_tensor_inputs=["latents"]
                    )
                for request_id in batch_request.request_ids:
                    result_queue.put(GenerationResult(request_id=request_id, result_type='completed', data=None))
                worker_logger.debug(f"Worker {worker_id}: Batched streaming request {pipeline_id} completed for {len(batch_request.request_ids)} requests with seed {seeds[0]}")
            except Exception as e:
                worker_logger.exception(f"Worker {worker_id}: Error in batched streaming request: {e}")
                for request_id in batch_request.request_ids:
                    result_queue.put(GenerationResult(request_id=request_id, result_type='error', data={'error': str(e)}))
            finally:
                cleanup_pipeline(pipeline_id)

        def process_non_streaming_request(gen_request: GenerationRequest):
            try:
                pipeline = get_pipeline_for_request(gen_request.request_id)
                with torch.cuda.device(gpu_id):
                    # Use provided seed or generate a random one
                    seed = gen_request.seed if gen_request.seed is not None else int(time.time() * 1000) % (2**32)
                    generator = torch.Generator(device=device).manual_seed(seed)
                    result = pipeline(
                        prompt=gen_request.prompt, negative_prompt=gen_request.negative_prompt, width=gen_request.width, height=gen_request.height,
                        guidance_scale=gen_request.guidance_scale, num_inference_steps=gen_request.num_inference_steps, num_images_per_prompt=gen_request.num_images,
                        generator=generator
                    )
                image_data = []
                for image in result.images:
                    buffer = io.BytesIO()
                    image.save(buffer, format='PNG', optimize=True)
                    b64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    image_data.append(b64_image)
                result_queue.put(GenerationResult(request_id=gen_request.request_id, result_type='completed', data={'images': image_data, 'seed': seed}))
                worker_logger.debug(f"Worker {worker_id}: Non-streaming request {gen_request.request_id} completed with seed {seed}")
            except Exception as e:
                worker_logger.error(f"Worker {worker_id}: Error in non-streaming request: {e}")
                result_queue.put(GenerationResult(request_id=gen_request.request_id, result_type='error', data={'error': str(e)}))
            finally:
                cleanup_pipeline(gen_request.request_id)

        def process_batched_non_streaming_request(batch_request: BatchedGenerationRequest):
            pipeline_id = batch_request.batch_id
            try:
                pipeline = get_pipeline_for_request(pipeline_id)
                with torch.cuda.device(gpu_id):
                    # Use provided seeds or generate random ones
                    if batch_request.seeds is None:
                        seeds = [int(time.time() * 1000 + i) % (2**32) for i in range(len(batch_request.prompts))]
                    else:
                        seeds = [seed if seed is not None else int(time.time() * 1000 + i) % (2**32) for i, seed in enumerate(batch_request.seeds)]
                    
                    # For batched requests, we'll use the first seed for the generator
                    generator = torch.Generator(device=device).manual_seed(seeds[0])
                    processed_negative_prompts = [p if p is not None else "" for p in batch_request.negative_prompts]
                    result = pipeline(
                        prompt=batch_request.prompts, negative_prompt=processed_negative_prompts, width=batch_request.width, height=batch_request.height,
                        guidance_scale=batch_request.guidance_scale, num_inference_steps=batch_request.num_inference_steps, num_images_per_prompt=batch_request.num_images,
                        generator=generator
                    )
                image_index = 0
                for i, request_id in enumerate(batch_request.request_ids):
                    request_images = result.images[image_index:image_index + batch_request.num_images]
                    image_data = []
                    for image in request_images:
                        buffer = io.BytesIO()
                        image.save(buffer, format='PNG', optimize=True)
                        b64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
                        image_data.append(b64_image)
                    result_queue.put(GenerationResult(request_id=request_id, result_type='completed', data={'images': image_data, 'seed': seeds[0]}))
                    image_index += batch_request.num_images
                worker_logger.debug(f"Worker {worker_id}: Batched non-streaming request {pipeline_id} completed for {len(batch_request.request_ids)} requests with seed {seeds[0]}")
            except Exception as e:
                worker_logger.error(f"Worker {worker_id}: Error in batched non-streaming request: {e}")
                for request_id in batch_request.request_ids:
                    result_queue.put(GenerationResult(request_id=request_id, result_type='error', data={'error': str(e)}))
            finally:
                cleanup_pipeline(pipeline_id)

        worker_logger.info(f"Worker {worker_id} ready to process requests on {device}")
        while not shutdown_event.is_set():
            try:
                request_or_batch = request_queue.get(timeout=1.0)
                if isinstance(request_or_batch, BatchedGenerationRequest):
                    batch_request = request_or_batch
                    worker_logger.info(f"Worker {worker_id}: Processing batched request {batch_request.batch_id} with {len(batch_request.prompts)} prompts, stream={batch_request.stream}")
                    if batch_request.stream:
                        process_batched_streaming_request(batch_request)
                    else:
                        process_batched_non_streaming_request(batch_request)
                else:
                    gen_request = request_or_batch
                    worker_logger.info(f"Worker {worker_id}: Processing individual request {gen_request.request_id}, stream={gen_request.stream}")
                    if gen_request.stream:
                        process_streaming_request(gen_request)
                    else:
                        process_non_streaming_request(gen_request)
            except queue.Empty:
                continue
            except Exception as e:
                worker_logger.error(f"Worker {worker_id}: Unexpected error in main loop: {e}")

    except Exception as e:
        worker_logger.error(f"Worker {worker_id}: Failed to initialize: {e}")
        return
    worker_logger.info(f"Worker {worker_id} shutting down") 