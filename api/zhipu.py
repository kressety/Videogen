import logging
import os
import time

from zhipuai import ZhipuAI

# Set up logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Check environment variables and initialize client
client = None
zhipuai_api_key = os.getenv('ZHIPUAI_API_KEY')
if zhipuai_api_key:
    try:
        client = ZhipuAI()
    except Exception as e:
        logger.error(f"Failed to initialize Zhipu AI client: {str(e)}")
else:
    logger.warning("Missing Zhipu AI API KEY (ZHIPUAI_API_KEY). Related features will be disabled.")


def generate_zhipu(prompt, image_url=None, model="cogvideox-2", quality="speed", with_audio=False, size="1920x1080",
                   fps=30):
    # Check if client is initialized successfully
    if not client:
        return None, "Zhipu AI API KEY not configured or client initialization failed"
        
    try:
        # Choose parameters based on whether image is provided
        params = {
            "model": model,
            "prompt": prompt,
            "quality": quality,
            "with_audio": with_audio,
        }
        if model != "cogvideox-flash":
            params["size"] = size
            params["fps"] = fps
        if image_url:
            params["image_url"] = image_url

        # Start generation request
        response = client.videos.generations(**params)
        task_id = response.id
        logger.debug(f"Zhipu AI task created successfully: {task_id}")

        # Poll task status
        while True:
            result = client.videos.retrieve_videos_result(id=task_id)
            logger.debug(f"Task status: {result.task_status}")
            if result.task_status in ["SUCCESS", "FAILED"]:
                break
            time.sleep(2)

        # Print full result for debugging
        logger.debug(f"Full task result content: {vars(result)}")

        if result.task_status == "SUCCESS":
            # Process video_result
            video_result = result.video_result
            if isinstance(video_result, list) and video_result:
                # If it's a list, get the first video URL
                video_url = video_result[0].url
            elif hasattr(video_result, "url"):
                # If it's a single object, get the url attribute directly
                video_url = video_result.url
            else:
                return None, "Task successful but video URL not found"

            if video_url:
                return video_url, "Task completed"
            return None, "Task successful but video URL not found"
        else:
            return None, f"Task failed: {result.task_status}"
    except Exception as e:
        logger.error(f"Zhipu AI generation failed: {str(e)}")
        return None, f"Zhipu AI generation failed: {str(e)}"
