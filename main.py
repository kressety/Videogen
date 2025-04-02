import logging
import os
import locale
import json
import sys
import gradio as gr
from PIL import Image

from api.ark import generate_volcengine
from api.bailian import generate_aliyun, MODEL_MAPPING
from api.tebi import upload_file_to_tebi
from api.zhipu import generate_zhipu

# Set global logging level to WARNING
logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Load translation files from i18n directory
def load_translations():
    translations = {}
    i18n_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'i18n')
    
    for lang_file in os.listdir(i18n_dir):
        if lang_file.endswith('.json'):
            lang_code = os.path.splitext(lang_file)[0]
            with open(os.path.join(i18n_dir, lang_file), 'r', encoding='utf-8') as f:
                translations[lang_code] = json.load(f)
    
    if not translations:
        logging.error("No translation files found in i18n directory.")
        sys.exit(1)
        
    return translations

# Load translations
try:
    TRANSLATIONS = load_translations()
except Exception as e:
    logging.error(f"Error loading translations: {str(e)}. Application cannot continue without translations.")
    sys.exit(1)

# Get platform name translations
def get_platform_names(translations):
    platform_names = {}
    for lang, trans in translations.items():
        if 'platforms' in trans:
            # English to localized
            to_localized = {}
            # Localized to English
            to_english = {}
            
            for key, value in trans['platforms'].items():
                if key == 'volcengine':
                    to_english[value] = 'Volcengine'
                    to_localized['Volcengine'] = value
                elif key == 'aliyun':
                    to_english[value] = 'Aliyun Bailian'
                    to_localized['Aliyun Bailian'] = value
                elif key == 'zhipu':
                    to_english[value] = 'Zhipu AI'
                    to_localized['Zhipu AI'] = value
                elif key == 'no_api':
                    to_english[value] = 'No API Configured'
                    to_localized['No API Configured'] = value
            
            platform_names[lang] = {'to_english': to_english, 'to_localized': to_localized}
    
    return platform_names

# Create platform name translation mappings
PLATFORM_NAMES = get_platform_names(TRANSLATIONS)

# Try to detect system language using newer APIs to avoid deprecation warning
try:
    # Use setlocale() to get current locale and then getlocale()
    current_locale = locale.setlocale(locale.LC_ALL, '')
    # Check if the locale contains a language code we can use
    default_lang = "zh" if current_locale and current_locale.startswith(("zh", "Chinese")) else "en"
    
    if default_lang not in TRANSLATIONS:
        default_lang = "en"  # Fallback to English if the detected language is not supported
except Exception:
    default_lang = "en"  # Default to English on error

# Check environment variables for each API
available_apis = []
enable_image_to_video = True

# Check Tebi.io configuration
tebi_access_key = os.getenv('TEBI_ACCESS_KEY')
tebi_secret_key = os.getenv('TEBI_SECRET_KEY')
if not (tebi_access_key and tebi_secret_key):
    missing = []
    if not tebi_access_key:
        missing.append("TEBI_ACCESS_KEY")
    if not tebi_secret_key:
        missing.append("TEBI_SECRET_KEY")
    logging.warning(f"Missing Tebi.io environment variables: {', '.join(missing)}. Image to video features will be disabled.")
    enable_image_to_video = False

# Check Volcengine configuration
ark_api_key = os.getenv('ARK_API_KEY')
ark_endpoint = os.getenv('ARK_ENDPOINT')
if ark_api_key and ark_endpoint:
    available_apis.append(TRANSLATIONS["zh"]["platforms"]["volcengine"])  # Use Chinese as base
else:
    missing = []
    if not ark_api_key:
        missing.append("ARK_API_KEY")
    if not ark_endpoint:
        missing.append("ARK_ENDPOINT")
    logging.warning(f"Missing Volcengine API environment variables: {', '.join(missing)}. This API will be disabled.")

# Check Aliyun Bailian configuration
dashscope_api_key = os.getenv('DASHSCOPE_API_KEY')
if dashscope_api_key:
    available_apis.append(TRANSLATIONS["zh"]["platforms"]["aliyun"])  # Use Chinese as base
else:
    logging.warning("Missing Aliyun Bailian API environment variable: DASHSCOPE_API_KEY. This API will be disabled.")

# Check Zhipu AI configuration
zhipuai_api_key = os.getenv('ZHIPUAI_API_KEY')
if zhipuai_api_key:
    available_apis.append(TRANSLATIONS["zh"]["platforms"]["zhipu"])  # Use Chinese as base
else:
    logging.warning("Missing Zhipu AI API environment variable: ZHIPUAI_API_KEY. This API will be disabled.")

# If no APIs are available, show warning but continue running
if not available_apis:
    logging.warning("All API environment variables are incomplete. WebUI will start but no video generation services will be available.")
    # Set a default value to avoid program errors
    available_apis = [TRANSLATIONS["zh"]["platforms"]["no_api"]]  # Use Chinese as base

# Check if image meets Volcengine requirements
def validate_image(file_path):
    try:
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:
            return False, "Image file size exceeds 10MB"

        with Image.open(file_path) as img:
            valid_formats = {"JPEG", "PNG", "WEBP", "BMP", "TIFF"}
            if img.format not in valid_formats:
                return False, f"Image format not supported. Only {', '.join(valid_formats)} are supported."
            width, height = img.size
            aspect_ratio = width / height
            min_side = min(width, height)
            max_side = max(width, height)
            if not (0.4 <= aspect_ratio <= 2.5):
                return False, "Image aspect ratio must be between 2:5 and 5:2 (0.4 - 2.5)"
            if min_side < 300:
                return False, "Image short side must be at least 300px"
            if max_side > 6000:
                return False, "Image long side must not exceed 6000px"
        return True, "Image validation passed"
    except Exception as e:
        return False, f"Image validation failed: {str(e)}"


# Determine if image upload is required
def is_image_required(platform, aliyun_model, ark_duration, zhipu_model):
    # If Tebi.io is not configured, disable image to video features
    if not enable_image_to_video:
        return False
    
    volcengine_names = [TRANSLATIONS["zh"]["platforms"]["volcengine"], TRANSLATIONS["en"]["platforms"]["volcengine"]]
    aliyun_names = [TRANSLATIONS["zh"]["platforms"]["aliyun"], TRANSLATIONS["en"]["platforms"]["aliyun"]]
    zhipu_names = [TRANSLATIONS["zh"]["platforms"]["zhipu"], TRANSLATIONS["en"]["platforms"]["zhipu"]]
        
    if platform in volcengine_names:
        return ark_duration == 5
    elif platform in aliyun_names:
        return aliyun_model in ["通义万相-图生视频2.1-Turbo", "通义万相-图生视频2.1-Plus"]
    elif platform in zhipu_names:
        return zhipu_model == "CogVideoX-2 (图生视频)"
    return False


# Generate video logic
def generate_video(platform, prompt, image_file, aliyun_model, ark_ratio, ark_duration, bailian_size, zhipu_model,
                   zhipu_quality, zhipu_audio, zhipu_size, zhipu_fps):
    # Translate platform name to Chinese if needed
    for lang in TRANSLATIONS:
        if lang != "zh" and platform in PLATFORM_NAMES[lang]["to_english"]:
            platform = PLATFORM_NAMES["zh"]["to_localized"][PLATFORM_NAMES[lang]["to_english"][platform]]
            break

    image_url = None
    if is_image_required(platform, aliyun_model, ark_duration, zhipu_model) and image_file:
        is_valid, message = validate_image(image_file)
        if not is_valid:
            return None, message
        
        # Upload image to Tebi.io
        image_url = upload_file_to_tebi(image_file)
            
        if not image_url:
            return None, "Image upload failed"

    # Use Chinese platform names for API calls as that's how they're defined in the API functions
    if platform == TRANSLATIONS["zh"]["platforms"]["volcengine"]:  # 火山引擎
        video_url, status = generate_volcengine(prompt, image_url, ark_ratio, ark_duration)
    elif platform == TRANSLATIONS["zh"]["platforms"]["aliyun"]:  # 阿里云百炼
        video_url, status = generate_aliyun(prompt, image_url, aliyun_model, bailian_size)
    elif platform == TRANSLATIONS["zh"]["platforms"]["zhipu"]:  # 智谱AI
        model = "cogvideox-2" if "CogVideoX-2" in zhipu_model else "cogvideox-flash"
        video_url, status = generate_zhipu(prompt, image_url, model, zhipu_quality, zhipu_audio, zhipu_size, zhipu_fps)
    else:
        return None, "Please select a valid platform"

    return video_url, status


# Update image upload area visibility
def update_image_visibility(platform, aliyun_model, ark_duration, zhipu_model):
    return gr.update(visible=is_image_required(platform, aliyun_model, ark_duration, zhipu_model))


# Filter available models based on Tebi.io configuration
def get_available_aliyun_models():
    if enable_image_to_video:
        return list(MODEL_MAPPING.keys())
    else:
        # Only return text-to-video models if image-to-video is disabled
        return ["通义万相-文生视频2.1-Turbo", "通义万相-文生视频2.1-Plus"]


def get_available_zhipu_models():
    if enable_image_to_video:
        return ["CogVideoX-2 (文生视频)", "CogVideoX-2 (图生视频)", "CogVideoX-Flash"]
    else:
        # Remove image-to-video model if Tebi.io is not configured
        return ["CogVideoX-2 (文生视频)", "CogVideoX-Flash"]


# Function to translate platform names
def translate_platform_names(platform_list, target_lang):
    if target_lang == "zh":
        return platform_list  # Chinese is the base
    
    if target_lang not in PLATFORM_NAMES:
        return platform_list  # Language not supported, return original
    
    translated = []
    for platform in platform_list:
        if platform in PLATFORM_NAMES["zh"]["to_english"]:
            english_name = PLATFORM_NAMES["zh"]["to_english"][platform]
            translated.append(PLATFORM_NAMES[target_lang]["to_localized"].get(english_name, english_name))
        else:
            translated.append(platform)
    return translated


# Function to update UI language
def update_ui_language(lang):
    if lang not in TRANSLATIONS:
        lang = "en"  # Fallback to English
        
    t = TRANSLATIONS[lang]
    
    # Translate platform choices
    translated_platforms = translate_platform_names(available_apis, lang)
    platform_value = translated_platforms[0] if translated_platforms else None
    
    return (
        t["title"],  # Page title
        t["subtitle"],  # Subtitle
        gr.update(choices=translated_platforms, label=t["platform"], value=platform_value),  # Platform dropdown
        gr.update(label=t["aliyun_model"]),  # Aliyun model dropdown
        gr.update(label=t["zhipu_model"]),  # Zhipu model dropdown
        gr.update(label=t["prompt"], placeholder=t["prompt_placeholder"]),  # Prompt textbox
        gr.update(label=t["image_upload"]),  # Image upload
        gr.update(label=t["ratio"]),  # Ratio dropdown
        gr.update(label=t["duration"]),  # Duration dropdown
        gr.update(label=t["resolution"]),  # Resolution dropdown
        gr.update(label=t["output_mode"]),  # Output mode dropdown
        gr.update(label=t["ai_audio"]),  # AI audio checkbox
        gr.update(label=t["resolution"]),  # Resolution dropdown for Zhipu
        gr.update(label=t["fps"]),  # FPS dropdown
        gr.update(label=t["generate"]),  # Generate button
        gr.update(label=t["clear"]),  # Clear button
        gr.update(label=t["result"]),  # Video output
        gr.update(label=t["status"])  # Status output
    )


# Gradio Interface
with gr.Blocks(title="Videogen Project") as demo:
    current_lang = gr.State(value=default_lang)
    
    page_title = gr.Markdown("# Videogen Project")
    subtitle = gr.Markdown("Enter prompts and select a platform to generate videos. Upload images for image-to-video generation.")

    with gr.Row():
        lang_selector = gr.Radio(
            choices=["中文", "English"],
            value="中文" if default_lang == "zh" else "English",
            label="语言/Language",
            interactive=True
        )

    with gr.Row():
        with gr.Column(scale=1):
            # Create platform selection dropdown based on available APIs
            platform = gr.Dropdown(
                choices=translate_platform_names(available_apis, default_lang),
                label=TRANSLATIONS[default_lang]["platform"],
                value=translate_platform_names(available_apis, default_lang)[0] if available_apis else None
            )
            aliyun_model = gr.Dropdown(
                choices=get_available_aliyun_models(),
                label=TRANSLATIONS[default_lang]["aliyun_model"],
                value="通义万相-文生视频2.1-Turbo",
                visible=TRANSLATIONS["zh"]["platforms"]["aliyun"] in available_apis or 
                       TRANSLATIONS["en"]["platforms"]["aliyun"] in translate_platform_names(available_apis, default_lang)
            )
            zhipu_model = gr.Dropdown(
                choices=get_available_zhipu_models(),
                label=TRANSLATIONS[default_lang]["zhipu_model"],
                value="CogVideoX-2 (文生视频)",
                visible=TRANSLATIONS["zh"]["platforms"]["zhipu"] in available_apis or 
                       TRANSLATIONS["en"]["platforms"]["zhipu"] in translate_platform_names(available_apis, default_lang)
            )
            prompt = gr.Textbox(
                label=TRANSLATIONS[default_lang]["prompt"],
                placeholder=TRANSLATIONS[default_lang]["prompt_placeholder"]
            )
            image_file = gr.File(
                label=TRANSLATIONS[default_lang]["image_upload"],
                type="filepath"
            )

            # Volcengine parameters
            with gr.Group(visible=TRANSLATIONS["zh"]["platforms"]["volcengine"] in available_apis or 
                                 TRANSLATIONS["en"]["platforms"]["volcengine"] in translate_platform_names(available_apis, default_lang)) as ark_params:
                ark_ratio = gr.Dropdown(
                    choices=["16:9", "4:3", "1:1", "3:4", "9:16", "21:9"],
                    label=TRANSLATIONS[default_lang]["ratio"],
                    value="16:9"
                )
                ark_duration = gr.Dropdown(
                    choices=[5, 10],
                    label=TRANSLATIONS[default_lang]["duration"],
                    value=5
                )

            # Aliyun parameters
            with gr.Group(visible=TRANSLATIONS["zh"]["platforms"]["aliyun"] in available_apis or 
                                 TRANSLATIONS["en"]["platforms"]["aliyun"] in translate_platform_names(available_apis, default_lang)) as bailian_params:
                bailian_size = gr.Dropdown(
                    choices=["1280*720", "960*960", "720*1280", "1088*832", "832*1088"],
                    label=TRANSLATIONS[default_lang]["resolution"],
                    value="1280*720"
                )

            # Zhipu AI parameters
            with gr.Group(visible=TRANSLATIONS["zh"]["platforms"]["zhipu"] in available_apis or 
                                 TRANSLATIONS["en"]["platforms"]["zhipu"] in translate_platform_names(available_apis, default_lang)) as zhipu_params:
                zhipu_quality = gr.Dropdown(
                    choices=["speed", "quality"],
                    label=TRANSLATIONS[default_lang]["output_mode"],
                    value="speed",
                    visible=True  # Default visible, will be adjusted dynamically
                )
                zhipu_audio = gr.Checkbox(
                    label=TRANSLATIONS[default_lang]["ai_audio"],
                    value=False
                )
                zhipu_size = gr.Dropdown(
                    choices=["720x480", "1024x1024", "1280x960", "960x1280", "1920x1080", "1080x1920", "2048x1080",
                             "3840x2160"],
                    label=TRANSLATIONS[default_lang]["resolution"],
                    value="1920x1080",
                    visible=True  # Default visible, will be adjusted dynamically
                )
                zhipu_fps = gr.Dropdown(
                    choices=[30, 60],
                    label=TRANSLATIONS[default_lang]["fps"],
                    value=30,
                    visible=True  # Default visible, will be adjusted dynamically
                )

            with gr.Row():
                submit_btn = gr.Button(label=TRANSLATIONS[default_lang]["generate"])
                clear_btn = gr.Button(label=TRANSLATIONS[default_lang]["clear"])

        with gr.Column(scale=1):
            video_output = gr.Video(label=TRANSLATIONS[default_lang]["result"])
            status_output = gr.Textbox(label=TRANSLATIONS[default_lang]["status"])

    # Language selector event handler
    def handle_language_change(lang_choice, curr_lang):
        new_lang = "zh" if lang_choice == "中文" else "en"
        if new_lang == curr_lang:
            return curr_lang
        return new_lang
    
    lang_selector.change(
        fn=handle_language_change,
        inputs=[lang_selector, current_lang],
        outputs=current_lang
    ).then(
        fn=update_ui_language,
        inputs=current_lang,
        outputs=[
            page_title, subtitle, platform, aliyun_model, zhipu_model, prompt, image_file,
            ark_ratio, ark_duration, bailian_size, zhipu_quality, zhipu_audio, zhipu_size,
            zhipu_fps, submit_btn, clear_btn, video_output, status_output
        ]
    )

    # Dynamic display logic
    def update_visibility(platform, zhipu_model):
        # Handle both English and Chinese platform names
        volcengine_names = [TRANSLATIONS["zh"]["platforms"]["volcengine"], TRANSLATIONS["en"]["platforms"]["volcengine"]]
        aliyun_names = [TRANSLATIONS["zh"]["platforms"]["aliyun"], TRANSLATIONS["en"]["platforms"]["aliyun"]]
        zhipu_names = [TRANSLATIONS["zh"]["platforms"]["zhipu"], TRANSLATIONS["en"]["platforms"]["zhipu"]]
        
        is_aliyun = platform in aliyun_names
        is_zhipu = platform in zhipu_names
        is_volcengine = platform in volcengine_names
        is_zhipu_flash = is_zhipu and zhipu_model == "CogVideoX-Flash"
        
        return (
            gr.update(visible=is_aliyun),  # aliyun_model
            gr.update(visible=is_zhipu),  # zhipu_model
            gr.update(visible=is_volcengine),  # ark_params
            gr.update(visible=is_aliyun),  # bailian_params
            gr.update(visible=is_zhipu),  # zhipu_params
            gr.update(visible=is_zhipu and not is_zhipu_flash),  # zhipu_quality
            gr.update(visible=is_zhipu and not is_zhipu_flash),  # zhipu_size
            gr.update(visible=is_zhipu and not is_zhipu_flash)  # zhipu_fps
        )

    # Only enable event handlers if at least one API is available
    no_api_platforms = [TRANSLATIONS["zh"]["platforms"]["no_api"], TRANSLATIONS["en"]["platforms"]["no_api"]]
    if len(available_apis) > 0 and available_apis[0] not in no_api_platforms:
        platform.change(
            fn=update_visibility,
            inputs=[platform, zhipu_model],
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
                gr.update(visible=zhipu_model != "CogVideoX-Flash"),
                gr.update(visible=zhipu_model != "CogVideoX-Flash"),
                gr.update(visible=zhipu_model != "CogVideoX-Flash")
            ),
            inputs=zhipu_model,
            outputs=[zhipu_quality, zhipu_size, zhipu_fps]
        )

        # Submit generation
        submit_btn.click(
            fn=generate_video,
            inputs=[platform, prompt, image_file, aliyun_model, ark_ratio, ark_duration, bailian_size, zhipu_model,
                    zhipu_quality, zhipu_audio, zhipu_size, zhipu_fps],
            outputs=[video_output, status_output]
        )

    # Clear inputs and outputs
    clear_btn.click(
        fn=lambda: (None, "", None, ""),
        inputs=[],
        outputs=[video_output, status_output, image_file, prompt]
    )

    # Initialize UI with default language within the Blocks context
    demo.load(
        fn=update_ui_language,
        inputs=current_lang,
        outputs=[
            page_title, subtitle, platform, aliyun_model, zhipu_model, prompt, image_file,
            ark_ratio, ark_duration, bailian_size, zhipu_quality, zhipu_audio, zhipu_size,
            zhipu_fps, submit_btn, clear_btn, video_output, status_output
        ]
    )

demo.launch(server_name="0.0.0.0")
