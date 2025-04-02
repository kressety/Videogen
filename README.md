# Videogen - AI Video Generation Tool

![Videogen](assets/creation-light.svg)

*English | [中文](README_zh.md)*

Videogen is a video generation tool based on multiple AI models, supporting three major platforms: Volcengine, Aliyun Bailian, and Zhipu AI. It can generate high-quality videos through text prompts or a combination of images and text.

## Features

- **Multi-platform Support**:
  - Volcengine video generation
  - Aliyun Bailian Tongyi Wanxiang series models
  - Zhipu AI's CogVideoX model series
- **Multiple Generation Modes**:
  - Text-to-video: Generate videos through text descriptions only
  - Image-to-video: Generate videos through a combination of images and text
- **Highly Customizable**:
  - Set aspect ratio, resolution, duration, frame rate, and other parameters
  - Support for AI sound effect generation (Zhipu AI)
- **Convenient File Management**:
  - Integrated with Tebi.io cloud storage service for automatic upload and management of image materials
- **Multilingual Support**:
  - English and Chinese interface
  - Auto-detects system language
  - Easily switch languages within the interface

## Environment Variables

The following environment variables need to be configured to use this project:

```bash
# Volcengine Configuration
ARK_API_KEY=your_ark_api_key    # Volcengine API KEY
ARK_ENDPOINT=your_ark_endpoint  # Volcengine inference endpoint

# Aliyun Bailian Configuration
DASHSCOPE_API_KEY=your_dashscope_api_key  # Aliyun Bailian API KEY

# Zhipu AI Configuration
ZHIPUAI_API_KEY=your_zhipuai_api_key  # Zhipu AI API KEY

# Tebi.io Cloud Storage Configuration
TEBI_ACCESS_KEY=your_tebi_access_key  # Tebi.io ACCESS KEY
TEBI_SECRET_KEY=your_tebi_secret_key  # Tebi.io SECRET KEY
```

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/videogen.git
cd videogen
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set environment variables (using .env file or system environment variables)

4. Start the application:

```bash
python main.py
```

## Usage

1. Access `http://localhost:7860` in your browser (default port)
2. Select the target AI platform (Volcengine/Aliyun Bailian/Zhipu AI)
3. Enter detailed prompt describing the video content you want to generate
4. If you need image-to-video generation, upload a reference image
5. Set appropriate parameters based on your chosen platform (aspect ratio, resolution, duration, etc.)
6. Click the "Generate Video" button and wait for generation to complete
7. Once generation is complete, you can preview or download the video directly from the interface

## Docker Deployment

### Using Pre-built Image (Recommended)

We provide pre-built Docker images supporting arm64 and amd64 platforms:

```bash
docker run -p 7860:7860 \
  -e ARK_API_KEY=your_ark_api_key \
  -e ARK_ENDPOINT=your_ark_endpoint \
  -e DASHSCOPE_API_KEY=your_dashscope_api_key \
  -e ZHIPUAI_API_KEY=your_zhipuai_api_key \
  -e TEBI_ACCESS_KEY=your_tebi_access_key \
  -e TEBI_SECRET_KEY=your_tebi_secret_key \
  arnocher/videogen
```

### Build Your Own Image

You can also build the image yourself:

```bash
docker build -t videogen .
docker run -p 7860:7860 \
  -e ARK_API_KEY=your_ark_api_key \
  -e ARK_ENDPOINT=your_ark_endpoint \
  -e DASHSCOPE_API_KEY=your_dashscope_api_key \
  -e ZHIPUAI_API_KEY=your_zhipuai_api_key \
  -e TEBI_ACCESS_KEY=your_tebi_access_key \
  -e TEBI_SECRET_KEY=your_tebi_secret_key \
  videogen
```

## Notes

- Make sure you have all required API keys and access permissions
- Uploaded images must comply with the requirements of each platform (recommended resolution ≥300px, aspect ratio between 0.4-2.5)
- Generated video content should comply with relevant laws, regulations, and platform policies
- If the Tebi.io configuration is missing, image-to-video features will be disabled
- The application requires translation files in the i18n directory to run

## Internationalization

The application supports multiple languages through the i18n system:
- Translation files are stored in the `i18n` directory as JSON files
- Currently supported languages: English (`en.json`) and Chinese (`zh.json`)
- To add a new language, create a new JSON file in the i18n directory following the same format

## Acknowledgements

This project uses the following open-source libraries and API services:
- Gradio
- Volcengine SDK
- DashScope SDK
- ZhipuAI SDK
- Boto3 (for S3-compatible storage) 