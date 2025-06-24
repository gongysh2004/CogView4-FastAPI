import logging
# Handle both relative and absolute imports
try:
    from .config import NUM_WORKER_PROCESSES, logger
except ImportError:
    from config import NUM_WORKER_PROCESSES, logger
import re

from openai import OpenAI


def display_ready_banner():
    """Display a prominent banner when all workers are ready"""
    banner_lines = [
        "=" * 80,
        "🚀 COGVIEW4 API SERVER READY! 🚀",
        "=" * 80,
        f"✅ All {NUM_WORKER_PROCESSES} worker processes have loaded models successfully",
        "✅ Server is ready to accept image generation requests",
        "✅ OpenAI-compatible API endpoints are active",
        "",
        "📋 Available Endpoints:",
        "   • POST /v1/images/generations  - Generate images",
        "   • POST /v1/prompt/optimize     - Optimize prompts",
        "   • POST /v1/prompt/translate    - Translate prompts",
        "   • GET  /v1/models             - List models",
        "   • GET  /health                - Health check",
        "   • GET  /status                - Detailed status",
        "   • GET  /client.html           - Web client",
        "",
        "🌐 Server running on: http://0.0.0.0:8000",
        "📚 Documentation: http://0.0.0.0:8000/docs",
        "=" * 80
    ]

    # Print banner to console
    print("\n")
    for line in banner_lines:
        print(line)
    print("\n")

    # Also log it
    logger.info("🚀 CogView4 API Server is fully ready - all workers loaded!")
    logger.info(f"✅ {NUM_WORKER_PROCESSES} workers ready to process requests")


def parse_size(size_str: str) -> tuple:
    """Parse size string like '1024x1024' to (width, height)"""
    try:
        width, height = map(int, size_str.split('x'))
        return width, height
    except Exception:
        logger.warning(f"Invalid size string '{size_str}', defaulting to 1024x1024.")
        return 1024, 1024

def clean_string(s):
    s = s.replace("\n", " ")
    s = s.strip()
    s = re.sub(r"\s{2,}", " ", s)
    return s

def convert_prompt(
    prompt: str,
    retry_times: int = 5,
) -> str:
    client = OpenAI(api_key='gpustack_8849135304d0780f_f475edbd6f118d95c27a90ab639d89cb',
                    base_url='https://models.dev.ai-links.com/v1')
    prompt = clean_string(prompt)
    for i in range(retry_times):
        try:
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": 'You are a bilingual image description assistant that works with an image generation bot.  You work with an assistant bot that will draw anything you say . \n    For example ,For example, outputting "a beautiful morning in the woods with the sun peaking through the trees" or "阳光透过树林的美丽清晨" will trigger your partner bot to output an image of a forest morning, as described . \n    You will be prompted by people looking to create detailed , amazing images . The way to accomplish this is to take their short prompts and make them extremely detailed and descriptive . \n    There are a few rules to follow : \n    - Input can be in Chinese or English. If input is in English, prompt should be written in English. If input is in Chinese, prompt should be written in Chinese.\n    - You will only ever output a single image description per user request .\n    - Image descriptions must be detailed and specific, including keyword categories such as subject, medium, style, additional details, color, and lighting. \n    - When generating descriptions, focus on portraying the visual elements rather than delving into abstract psychological and emotional aspects. Provide clear and concise details that vividly depict the scene and its composition, capturing the tangible elements that make up the setting.\n    - Do not provide the process and explanation, just return the modified description . \n    ',
                    },
                    {
                        "role": "user",
                        "content": 'Create an imaginative image descriptive caption for the user input : "An anime girl stands amidst a dense flower bush."',
                    },
                    {
                        "role": "assistant",
                        "content": "This image is a beautifully crafted digital illustration in an anime style. It features Suzuran, a character from the video game Arknights. She stands gracefully amidst a picturesque meadow with lush green grass and scattered wildflowers that gently sway in the breeze. Her attire includes a detailed outfit with layered ruffles and intricate fastenings, reflecting both elegance and functionality typical of the game's aesthetic. Suzuran holds a small bouquet of flowers delicately in her hands, adding to the serene atmosphere.\n\nProminent fox ears extend from her head, signifying her animal spirit form or persona within the game. The background showcases rolling hills covered in dense foliage under a brilliant blue sky dotted with fluffy white clouds. Golden leaves float whimsically through the air, enhancing the magical quality of the scene. A distant building partially obscured by vegetation hints at human presence without detracting from the natural beauty surrounding Suzuran. Overall, this artwork captures a moment of tranquility and charm, embodying the essence of the character and the enchanting world she inhabits.",
                    },
                    {
                        "role": "user",
                        "content": 'Create an imaginative image descriptive caption for the user input : "Draw a bright convertible car with a sense of artistic design."',
                    },
                    {
                        "role": "assistant",
                        "content": 'The image showcases a meticulously crafted Delahaye 135 M.S. Special Roadster from 1937 in a highly polished and realistic rendering style that highlights its luxurious design and impeccable details. The car\'s body is an elegant deep brown with a glossy finish, exuding sophistication and timeless beauty. Its aerodynamic, streamlined shape features smooth curves accentuated by chrome detailing on the fenders and running boards. The front grille has three prominent circular headlights, adding to its classic charm while the dual exhaust pipes are tastefully integrated into the rear fenders.\n\nThe open cockpit area reveals sumptuous tan leather seats, emphasizing both comfort and elegance for the driver and passenger. The vehicle\'s number plate reads "MB 175". Photographed against a dark gradient background, the focus remains solely on this automotive masterpiece, allowing viewers to appreciate every intricate detail without distraction. This image captures not just a car but a piece of art, reflecting the luxury and craftsmanship emblematic of pre-war European automobiles.',
                    },
                    {
                        "role": "user",
                        "content": 'Create an imaginative image descriptive caption for the user input : "画一个白发、神情忧郁的动漫女孩，手里拿着一支香烟"',
                    },
                    {
                        "role": "assistant",
                        "content": "这幅图像是一幅动漫风格的插画，画中描绘了一位长发飘逸的白发女孩。她神情忧郁，双眼低垂，脸上带着微微的愁容。女孩穿着浅色外套，里面搭配深色衬衫和领带，增添了她沉静却时尚的外表。她的手靠近嘴边，似乎在拿着一支香烟，画作的说明也表示她在吸烟。背景描绘了一个冬季的城市场景，地面和建筑物上覆盖着积雪。几株稀疏的植物从雪地中探出，街边停着一辆车，似乎是空荡荡的街道，增强了场景的荒凉氛围。这幅作品整体风格细致精美，典型的现代动漫插画风格，既捕捉了角色的情感表达，也呈现了周围环境的静谧氛围",
                    },
                    {
                        "role": "user",
                        "content": 'Create an imaginative image descriptive caption for the user input : "一张红色的海报，中间写有"开门大吉" "',
                    },
                    {
                        "role": "assistant",
                        "content": '这张图片采用了海报风格，色彩鲜艳，主要以红色和金色为主，寓意吉祥如意。在画面的正中间是一块红色的大匾，上面用白色大字写着"开门大吉"，四角点缀着金色的装饰图案，显得格外喜庆。匾额上方悬挂着一对红色的灯笼，增添了节日的气氛。背景左右两侧是传统的绿色中式建筑，屋顶呈现出典型的飞檐翘角设计。底部有祥云朵朵和可爱的卡通福袋，象征着好运福气满满。整张海报传达出浓厚的节日氛围。',
                    },
                    {
                        "role": "user",
                        "content": f"Create an imaginative image descriptive caption for the user input : {prompt}",
                    },
                ],
                model="glm-4-9b-chat",
                temperature=0.01,
                top_p=0.7,
                stream=False,
                max_tokens=1000,
            )
            prompt = response.choices[0].message.content
            if prompt:
                prompt = clean_string(prompt)
                break
        except Exception:
            pass

    return prompt

def translate_prompt(
    prompt: str,
    retry_times: int = 5,
) -> str:
    client = OpenAI(api_key='gpustack_8849135304d0780f_f475edbd6f118d95c27a90ab639d89cb',
                    base_url='https://models.dev.ai-links.com/v1')
    prompt = clean_string(prompt)
    for i in range(retry_times):
        try:
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": '你是一个翻译助手.  请把用户的文本翻译成中文或英文。'
                    },
                    {
                        "role": "user",
                        "content": f"{prompt}",
                    },
                ],
                model="glm-4-9b-chat",
                temperature=0.01,
                top_p=0.7,
                stream=False,
                max_tokens=1000,
            )
            prompt = response.choices[0].message.content
            if prompt:
                prompt = clean_string(prompt)
                break
        except Exception:
            pass

    return prompt