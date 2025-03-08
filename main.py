import logging
import os

import gradio as gr
from PIL import Image

from api.ark import generate_volcengine
from api.bailian import generate_aliyun, MODEL_MAPPING
from api.tebi import upload_file_to_tebi

# 设置全局日志级别为 WARNING，减少详细输出
logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


# 检查图片是否符合火山引擎要求
def validate_image(file_path):
    try:
        # 文件大小检查（小于 10MB）
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:  # 10MB = 10,485,760 字节
            return False, "图片文件大小超过 10MB"

        # 打开图片并检查格式、尺寸
        with Image.open(file_path) as img:
            # 格式检查
            valid_formats = {"JPEG", "PNG", "WEBP", "BMP", "TIFF"}
            if img.format not in valid_formats:
                return False, f"图片格式不支持，仅支持 {', '.join(valid_formats)}"

            # 宽高检查
            width, height = img.size
            aspect_ratio = width / height
            min_side = min(width, height)
            max_side = max(width, height)

            if not (0.4 <= aspect_ratio <= 2.5):
                return False, "图片宽高比需在 2:5 到 5:2 之间 (0.4 - 2.5)"
            if min_side < 300:
                return False, "图片短边像素需大于等于 300px"
            if max_side > 6000:
                return False, "图片长边像素需小于等于 6000px"

        return True, "图片验证通过"
    except Exception as e:
        return False, f"图片验证失败: {str(e)}"


# 判断是否需要图片上传
def is_image_required(platform, aliyun_model, ark_duration):
    if platform == "火山引擎":
        return ark_duration == 5  # 仅 5 秒支持文图生视频
    elif platform == "阿里云百炼":
        return aliyun_model in ["通义万相-图生视频2.1-Turbo", "通义万相-图生视频2.1-Plus"]
    return False


# 生成视频逻辑
def generate_video(platform, prompt, image_file, aliyun_model, ark_ratio, ark_duration, bailian_size):
    image_url = None
    if is_image_required(platform, aliyun_model, ark_duration) and image_file:
        # 验证图片
        is_valid, message = validate_image(image_file)
        if not is_valid:
            return None, message

        # 上传到 Tebi
        image_url = upload_file_to_tebi(image_file)
        if not image_url:
            return None, "图片上传到 Tebi 失败"

    if platform == "火山引擎":
        video_url, status = generate_volcengine(prompt, image_url, ark_ratio, ark_duration)
    elif platform == "阿里云百炼":
        video_url, status = generate_aliyun(prompt, image_url, aliyun_model, bailian_size)
    else:
        return None, "请选择有效平台"

    return video_url, status


# 更新图片上传区域可见性
def update_image_visibility(platform, aliyun_model, ark_duration):
    return gr.update(visible=is_image_required(platform, aliyun_model, ark_duration))


# Gradio 界面
with gr.Blocks(title="Videogen Project") as demo:
    gr.Markdown("# Videogen Project")
    gr.Markdown("输入提示词并选择平台生成视频，支持上传图片用于文图生视频。")

    with gr.Row():
        # 左侧输入区
        with gr.Column(scale=1):
            platform = gr.Dropdown(
                choices=["火山引擎", "阿里云百炼"],
                label="选择平台",
                value="火山引擎"
            )
            aliyun_model = gr.Dropdown(
                choices=list(MODEL_MAPPING.keys()),
                label="阿里云模型（仅阿里云生效）",
                value="通义万相-文生视频2.1-Turbo",
                visible=False
            )
            prompt = gr.Textbox(label="提示词", placeholder="请输入生成视频的描述，例如：一只猫在草地上奔跑")
            image_file = gr.File(label="上传图片（用于文图生视频）", type="filepath")

            # 火山引擎参数
            with gr.Group(visible=True) as ark_params:
                ark_ratio = gr.Dropdown(
                    choices=["16:9", "4:3", "1:1", "3:4", "9:16", "21:9"],
                    label="宽高比例",
                    value="16:9"
                )
                ark_duration = gr.Dropdown(
                    choices=[5, 10],
                    label="视频时长（秒）",
                    value=5
                )

            # 阿里云参数
            with gr.Group(visible=False) as bailian_params:
                bailian_size = gr.Dropdown(
                    choices=["1280*720", "960*960", "720*1280", "1088*832", "832*1088"],
                    label="分辨率",
                    value="1280*720"
                )

            with gr.Row():
                submit_btn = gr.Button("生成视频")
                clear_btn = gr.Button("清除")

        # 右侧输出区
        with gr.Column(scale=1):
            video_output = gr.Video(label="生成结果")
            status_output = gr.Textbox(label="状态")


    # 动态显示逻辑
    def update_visibility(platform):
        return (
            gr.update(visible=platform == "阿里云百炼"),  # aliyun_model
            gr.update(visible=platform == "火山引擎"),  # ark_params
            gr.update(visible=platform == "阿里云百炼")  # bailian_params
        )


    platform.change(
        fn=update_visibility,
        inputs=platform,
        outputs=[aliyun_model, ark_params, bailian_params]
    )
    platform.change(
        fn=update_image_visibility,
        inputs=[platform, aliyun_model, ark_duration],
        outputs=image_file
    )
    aliyun_model.change(
        fn=update_image_visibility,
        inputs=[platform, aliyun_model, ark_duration],
        outputs=image_file
    )
    ark_duration.change(
        fn=update_image_visibility,
        inputs=[platform, aliyun_model, ark_duration],
        outputs=image_file
    )

    # 提交生成
    submit_btn.click(
        fn=generate_video,
        inputs=[platform, prompt, image_file, aliyun_model, ark_ratio, ark_duration, bailian_size],
        outputs=[video_output, status_output]
    )

    # 清除输入和输出
    clear_btn.click(
        fn=lambda: (None, "", None, ""),
        inputs=[],
        outputs=[video_output, status_output, image_file, prompt]
    )

demo.launch(quiet=True)
