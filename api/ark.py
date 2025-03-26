import os
import re
import time

from volcenginesdkarkruntime import Ark

# 初始化火山引擎客户端
volc_client = Ark()


def generate_volcengine(prompt, image_url=None, ratio="16:9", duration=5):
    content = [{"type": "text", "text": f"{prompt} --ratio {ratio} --dur {str(duration)}"}]
    if image_url:
        content.append({"type": "image_url", "image_url": {"url": image_url}})

    try:
        # 创建任务，传入额外参数
        create_result = volc_client.content_generation.tasks.create(
            model=os.getenv('ARK_ENDPOINT'),
            content=content
        )
        print(f"任务创建成功: {create_result.id}")

        # 轮询任务状态
        while True:
            get_result = volc_client.content_generation.tasks.get(task_id=create_result.id)
            print(f"任务状态: {get_result.status}")
            if get_result.status in ["succeeded", "failed"]:
                break
            time.sleep(2)

        # 提取 video_url
        if get_result.status == "succeeded":
            content_str = str(get_result.content)
            video_url_match = re.search(r"video_url='(.*?)'", content_str)
            if video_url_match:
                return video_url_match.group(1), "任务完成"
            return None, "任务成功但未找到视频 URL"
        else:
            return None, f"任务失败: {get_result.status}"
    except Exception as e:
        return None, f"火山引擎生成失败: {str(e)}"
