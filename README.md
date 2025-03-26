# Videogen - AI视频生成工具

![Videogen](assets/creation-light.svg)

Videogen是一个基于多种AI模型的视频生成工具，支持火山引擎、阿里云百炼和智谱AI三大平台，可以通过文本提示词或图片+文本组合生成高质量视频。

## 功能特点

- **多平台支持**：
  - 火山引擎视频生成
  - 阿里云百炼通义万相系列模型
  - 智谱AI的CogVideoX模型系列
- **多种生成模式**：
  - 文生视频：仅通过文本描述生成视频
  - 图生视频：通过图片和文本联合生成视频
- **高度定制化**：
  - 支持设置宽高比、分辨率、时长、帧率等参数
  - 支持AI音效生成（智谱AI）
- **便捷文件管理**：
  - 集成Tebi.io云存储服务，自动上传和管理图片素材

## 环境变量配置

使用本项目需要配置以下环境变量：

```bash
# 火山引擎配置
ARK_API_KEY=your_ark_api_key    # 火山引擎的API KEY
ARK_ENDPOINT=your_ark_endpoint  # 火山引擎的推理接入点

# 阿里云百炼配置
DASHSCOPE_API_KEY=your_dashscope_api_key  # 阿里云百炼的API KEY

# 智谱AI配置
ZHIPUAI_API_KEY=your_zhipuai_api_key  # 智谱AI的API KEY

# Tebi.io云存储配置
TEBI_ACCESS_KEY=your_tebi_access_key  # Tebi.io的ACCESS KEY
TEBI_SECRET_KEY=your_tebi_secret_key  # Tebi.io的SECRET KEY
```

## 安装说明

1. 克隆仓库：

```bash
git clone https://github.com/yourusername/videogen.git
cd videogen
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 设置环境变量（可使用.env文件或系统环境变量）

4. 启动应用：

```bash
python main.py
```

## 使用方法

1. 在浏览器中访问 `http://localhost:7860`（默认端口）
2. 选择目标AI平台（火山引擎/阿里云百炼/智谱AI）
3. 输入详细的提示词描述您想要生成的视频内容
4. 如果需要图生视频，请上传参考图片
5. 根据您选择的平台，设置合适的参数（宽高比、分辨率、时长等）
6. 点击"生成视频"按钮，等待生成完成
7. 生成完成后，可以直接在界面中预览或下载视频

## Docker部署

### 使用预构建镜像（推荐）

我们提供了预构建的Docker镜像，支持arm64和amd64平台，可以直接使用：

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

### 自行构建镜像

也可以自行构建镜像：

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

## 注意事项

- 请确保您拥有所有必需的API密钥和访问权限
- 上传的图片需符合各平台的要求（建议分辨率≥300px，宽高比在0.4-2.5之间）
- 生成的视频内容应遵守相关法律法规和平台政策

## 鸣谢

本项目使用了以下开源库和API服务：
- Gradio
- Volcengine SDK
- DashScope SDK
- ZhipuAI SDK
- Boto3 (用于S3兼容存储) 