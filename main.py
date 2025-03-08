import logging
import os

import gradio as gr
from PIL import Image

from api.ark import generate_volcengine
from api.bailian import generate_aliyun, MODEL_MAPPING
from api.tebi import upload_file_to_tebi
from api.zhipu import generate_zhipu

# 设置全局日志级别为 WARNING
logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


# 检查图片是否符合火山引擎要求
def validate_image(file_path):
    try:
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:
            return False, "图片文件大小超过 10MB"

        with Image.open(file_path) as img:
            valid_formats = {"JPEG", "PNG", "WEBP", "BMP", "TIFF"}
            if img.format not in valid_formats:
                return False, f"图片格式不支持，仅支持 {', '.join(valid_formats)}"
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
def is_image_required(platform, aliyun_model, ark_duration, zhipu_model):
    if platform == "火山引擎":
        return ark_duration == 5
    elif platform == "阿里云百炼":
        return aliyun_model in ["通义万相-图生视频2.1-Turbo", "通义万相-图生视频2.1-Plus"]
    elif platform == "智谱AI":
        return zhipu_model == "CogVideoX-2 (图生视频)"
    return False


# 生成视频逻辑
def generate_video(platform, prompt, image_file, aliyun_model, ark_ratio, ark_duration, bailian_size, zhipu_model,
                   zhipu_quality, zhipu_audio, zhipu_size, zhipu_fps):
    image_url = None
    if is_image_required(platform, aliyun_model, ark_duration, zhipu_model) and image_file:
        is_valid, message = validate_image(image_file)
        if not is_valid:
            return None, message
        image_url = upload_file_to_tebi(image_file)
        if not image_url:
            return None, "图片上传到 Tebi 失败"

    if platform == "火山引擎":
        video_url, status = generate_volcengine(prompt, image_url, ark_ratio, ark_duration)
    elif platform == "阿里云百炼":
        video_url, status = generate_aliyun(prompt, image_url, aliyun_model, bailian_size)
    elif platform == "智谱AI":
        model = "cogvideox-2" if "CogVideoX-2" in zhipu_model else "cogvideox-flash"
        video_url, status = generate_zhipu(prompt, image_url, model, zhipu_quality, zhipu_audio, zhipu_size, zhipu_fps)
    else:
        return None, "请选择有效平台"

    return video_url, status


# 更新图片上传区域可见性
def update_image_visibility(platform, aliyun_model, ark_duration, zhipu_model):
    return gr.update(visible=is_image_required(platform, aliyun_model, ark_duration, zhipu_model))


# Gradio 界面
with gr.Blocks(title="Videogen Project") as demo:
    gr.Markdown("# Videogen Project")
    gr.Markdown("输入提示词并选择平台生成视频，支持上传图片用于文图生视频。")

    with gr.Row():
        with gr.Column(scale=1):
            platform = gr.Dropdown(
                choices=["火山引擎", "阿里云百炼", "智谱AI"],
                label="选择平台",
                value="火山引擎"
            )
            aliyun_model = gr.Dropdown(
                choices=list(MODEL_MAPPING.keys()),
                label="阿里云模型（仅阿里云生效）",
                value="通义万相-文生视频2.1-Turbo",
                visible=False
            )
            zhipu_model = gr.Dropdown(
                choices=["CogVideoX-2 (文生视频)", "CogVideoX-2 (图生视频)", "CogVideoX-Flash"],
                label="智谱AI模型（仅智谱AI生效）",
                value="CogVideoX-2 (文生视频)",
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

            # 智谱AI参数
            with gr.Group(visible=False) as zhipu_params:
                zhipu_quality = gr.Dropdown(
                    choices=["speed", "quality"],
                    label="输出模式",
                    value="speed"
                )
                zhipu_audio = gr.Checkbox(label="生成AI音效", value=False)
                zhipu_size = gr.Dropdown(
                    choices=["720x480", "1024x1024", "1280x960", "960x1280", "1920x1080", "1080x1920", "2048x1080",
                             "3840x2160"],
                    label="分辨率",
                    value="1920x1080"
                )
                zhipu_fps = gr.Dropdown(
                    choices=[30, 60],
                    label="帧率 (FPS)",
                    value=30
                )

            with gr.Row():
                submit_btn = gr.Button("生成视频")
                clear_btn = gr.Button("清除")

        with gr.Column(scale=1):
            video_output = gr.Video(label="生成结果")
            status_output = gr.Textbox(label="状态")


    # 动态显示逻辑
    def update_visibility(platform):
        return (
            gr.update(visible=platform == "阿里云百炼"),  # aliyun_model
            gr.update(visible=platform == "智谱AI"),  # zhipu_model
            gr.update(visible=platform == "火山引擎"),  # ark_params
            gr.update(visible=platform == "阿里云百炼"),  # bailian_params
            gr.update(visible=platform == "智谱AI"),  # zhipu_params
            gr.update(visible=platform == "智谱AI" and "cogvideox-flash" not in zhipu_model.value),  # zhipu_quality
            gr.update(visible=platform == "智谱AI" and "cogvideox-flash" not in zhipu_model.value),  # zhipu_size
            gr.update(visible=platform == "智谱AI" and "cogvideox-flash" not in zhipu_model.value)  # zhipu_fps
        )


    platform.change(
        fn=update_visibility,
        inputs=platform,
        outputs=[aliyun_model, zhipu_model, ark_params, bailian_params, zhipu_params, zhipu_quality, zhipu_size,
                 zhipu_fps]
    )
    platform.change(
        fn=update_image_visibility,
        inputs=[platform, aliyun_model, ark_duration, zhipu_model],
        outputs=image_file
    )
    aliyun_model.change(
        fn=update_image_visibility,
        inputs=[platform, aliyun_model, ark_duration, zhipu_model],
        outputs=image_file
    )
    ark_duration.change(
        fn=update_image_visibility,
        inputs=[platform, aliyun_model, ark_duration, zhipu_model],
        outputs=image_file
    )
    zhipu_model.change(
        fn=update_image_visibility,
        inputs=[platform, aliyun_model, ark_duration, zhipu_model],
        outputs=image_file
    )
    zhipu_model.change(
        fn=lambda zhipu_model: (
            gr.update(visible="cogvideox-flash" not in zhipu_model),
            gr.update(visible="cogvideox-flash" not in zhipu_model),
            gr.update(visible="cogvideox-flash" not in zhipu_model)
        ),
        inputs=zhipu_model,
        outputs=[zhipu_quality, zhipu_size, zhipu_fps]
    )

    # 提交生成
    submit_btn.click(
        fn=generate_video,
        inputs=[platform, prompt, image_file, aliyun_model, ark_ratio, ark_duration, bailian_size, zhipu_model,
                zhipu_quality, zhipu_audio, zhipu_size, zhipu_fps],
        outputs=[video_output, status_output]
    )

    # 清除输入和输出
    clear_btn.click(
        fn=lambda: (None, "", None, ""),
        inputs=[],
        outputs=[video_output, status_output, image_file, prompt]
    )

demo.launch(server_name="0.0.0.0")
