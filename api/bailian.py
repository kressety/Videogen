import logging
import os
from http import HTTPStatus

from dashscope import VideoSynthesis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check environment variables
dashscope_api_key = os.getenv('DASHSCOPE_API_KEY')
if not dashscope_api_key:
    logger.warning("Missing Aliyun Bailian API KEY (DASHSCOPE_API_KEY). Related features will be disabled.")

MODEL_MAPPING = {
    "通义万相-图生视频2.1-Turbo": "wanx2.1-i2v-turbo",
    "通义万相-图生视频2.1-Plus": "wanx2.1-i2v-plus",
    "通义万相-文生视频2.1-Turbo": "wanx2.1-t2v-turbo",
    "通义万相-文生视频2.1-Plus": "wanx2.1-t2v-plus"
}


def generate_aliyun(prompt, image_url=None, model_name="通义万相-文生视频2.1-Turbo", size="1280*720"):
    # Check if API KEY is configured
    if not dashscope_api_key:
        return None, "Aliyun Bailian API KEY not configured"
        
    try:
        model = MODEL_MAPPING.get(model_name, "wanx2.1-t2v-turbo")
        rsp = VideoSynthesis.call(
            model=model,
            prompt=prompt,
            img_url=image_url if image_url else None,
            size=size  # Resolution
        )
        if rsp.status_code == HTTPStatus.OK:
            return rsp.output.video_url, "Task completed"
        else:
            logger.error(f"Aliyun generation failed: {rsp.message}")
            return None, f"Aliyun generation failed: {rsp.message}"
    except Exception as e:
        if isinstance(e, ConnectionResetError):
            logger.debug("Ignoring remote host connection closed exception")
            return rsp.output.video_url, "Task completed"
        logger.error(f"Aliyun generation failed: {str(e)}")
        return None, f"Aliyun generation failed: {str(e)}"
