import os
import re
import time
import logging

from volcenginesdkarkruntime import Ark

# Set up logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Initialize Volcengine client and check environment variables
volc_client = None
try:
    api_key = os.getenv('ARK_API_KEY')
    endpoint = os.getenv('ARK_ENDPOINT')
    if api_key and endpoint:
        volc_client = Ark()
except Exception as e:
    logger.error(f"Failed to initialize Volcengine client: {str(e)}")


def generate_volcengine(prompt, image_url=None, ratio="16:9", duration=5):
    # If client initialization failed, return error
    if not volc_client:
        return None, "Volcengine API not configured or initialization failed"
        
    content = [{"type": "text", "text": f"{prompt} --ratio {ratio} --dur {str(duration)}"}]
    if image_url:
        content.append({"type": "image_url", "image_url": {"url": image_url}})

    try:
        # Create task with additional parameters
        create_result = volc_client.content_generation.tasks.create(
            model=os.getenv('ARK_ENDPOINT'),
            content=content
        )
        logger.info(f"Task created successfully: {create_result.id}")

        # Poll task status
        while True:
            get_result = volc_client.content_generation.tasks.get(task_id=create_result.id)
            logger.info(f"Task status: {get_result.status}")
            if get_result.status in ["succeeded", "failed"]:
                break
            time.sleep(2)

        # Extract video_url
        if get_result.status == "succeeded":
            content_str = str(get_result.content)
            video_url_match = re.search(r"video_url='(.*?)'", content_str)
            if video_url_match:
                return video_url_match.group(1), "Task completed"
            return None, "Task successful but video URL not found"
        else:
            return None, f"Task failed: {get_result.status}"
    except Exception as e:
        return None, f"Volcengine generation failed: {str(e)}"
