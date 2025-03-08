import logging
import time

from zhipuai import ZhipuAI

# 设置日志
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# 初始化客户端（API Key 通过环境变量传入）
client = ZhipuAI()


def generate_zhipu(prompt, image_url=None, model="cogvideox-2", quality="speed", with_audio=False, size="1920x1080",
                   fps=30):
    try:
        # 根据是否有图片选择文生视频或图生视频
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

        # 发起生成请求
        response = client.videos.generations(**params)
        task_id = response.id
        logger.debug(f"智谱AI任务创建成功: {task_id}")

        # 轮询任务状态
        while True:
            result = client.videos.retrieve_videos_result(id=task_id)
            logger.debug(f"任务状态: {result.task_status}")
            if result.task_status in ["SUCCESS", "FAILED"]:
                break
            time.sleep(2)

        # 打印完整结果以调试
        logger.debug(f"任务结果完整内容: {vars(result)}")

        if result.task_status == "SUCCESS":
            # 处理 video_result
            video_result = result.video_result
            if isinstance(video_result, list) and video_result:
                # 如果是列表，取第一个视频 URL
                video_url = video_result[0].url
            elif hasattr(video_result, "url"):
                # 如果是单一对象，直接取 url 属性
                video_url = video_result.url
            else:
                return None, "任务成功但未找到视频 URL"

            if video_url:
                return video_url, "任务完成"
            return None, "任务成功但未找到视频 URL"
        else:
            return None, f"任务失败: {result.task_status}"
    except Exception as e:
        logger.error(f"智谱AI生成失败: {str(e)}")
        return None, f"智谱AI生成失败: {str(e)}"
