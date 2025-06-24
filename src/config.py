import logging
import os

# Configure logging at module level
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
log_file = os.getenv('LOG_FILE', 'cogview4_api.log')

logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file)
    ],
    force=True
)

logger = logging.getLogger(__name__)

# Application configuration
NUM_WORKER_PROCESSES = int(os.getenv('NUM_WORKER_PROCESSES', '1'))
MAX_TOTAL_PIXELS = int(os.getenv('MAX_TOTAL_PIXELS', str(1024 * 1024 * 4)))  # 4 megapixels default
MODEL_PATH = os.getenv('MODEL_PATH', "/gm-models/CogView4-6B")
ENABLE_PROMPT_BATCHING = os.getenv('ENABLE_PROMPT_BATCHING', 'true').lower() == 'true'
BATCH_TIMEOUT = float(os.getenv('BATCH_TIMEOUT', '0.5'))
MAX_BATCH_SIZE = int(os.getenv('MAX_BATCH_SIZE', '8'))

logger.info(f"Log level: {log_level}")
logger.info(f"Log file: {log_file}")
logger.info(f"Model path: {MODEL_PATH}")
logger.info(f"Number of worker processes: {NUM_WORKER_PROCESSES}")
logger.info(f"VRAM protection: Maximum total pixels per request: {MAX_TOTAL_PIXELS:,}")
logger.info(f"Prompt batching enabled: {ENABLE_PROMPT_BATCHING}")
if ENABLE_PROMPT_BATCHING:
    logger.info(f"Batch timeout: {BATCH_TIMEOUT}s")
    logger.info(f"Max batch size: {MAX_BATCH_SIZE}") 