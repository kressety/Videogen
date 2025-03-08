import logging
from http import HTTPStatus

from dashscope import VideoSynthesis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_MAPPING = {
    "通义万相-图生视频2.1-Turbo": "wanx2.1-i2v-turbo",
    "通义万相-图生视频2.1-Plus": "wanx2.1-i2v-plus",
    "通义万相-文生视频2.1-Turbo": "wanx2.1-t2v-turbo",
    "通义万相-文生视频2.1-Plus": "wanx2.1-t2v-plus"
}


def generate_aliyun(prompt, image_url=None, model_name="通义万相-文生视频2.1-Turbo", size="1280*720"):
    try:
        model = MODEL_MAPPING.get(model_name, "wanx2.1-t2v-turbo")
        rsp = VideoSynthesis.call(
            model=model,
            prompt=prompt,
            img_url=image_url if image_url else None,
            size=size  # 分辨率
        )
        if rsp.status_code == HTTPStatus.OK:
            return rsp.output.video_url, "任务完成"
        else:
            logger.error(f"阿里云生成失败: {rsp.message}")
            return None, f"阿里云生成失败: {rsp.message}"
    except Exception as e:
        if isinstance(e, ConnectionResetError):
            logger.debug("忽略远程主机关闭连接的异常")
            return rsp.output.video_url, "任务完成"
        logger.error(f"阿里云生成失败: {str(e)}")
        return None, f"阿里云生成失败: {str(e)}"
