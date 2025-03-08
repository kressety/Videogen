import hashlib
import os
import time

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

# 配置 Tebi.io 的凭证和端点
ACCESS_KEY = os.getenv('TEBI_ACCESS_KEY')
SECRET_KEY = os.getenv('TEBI_SECRET_KEY')
ENDPOINT_URL = 'http://s3.tebi.io'
BUCKET_NAME = 'src.ziqizhu.com'  # 替换为你的存储桶名称

# 创建 S3 客户端
s3_client = boto3.client(
    's3',
    endpoint_url=ENDPOINT_URL,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    config=Config(signature_version='s3v4')
)


# 检查文件是否存在的辅助函数
def file_exists(bucket, key):
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        raise e


# 计算文件的 MD5（base64 编码）
def calculate_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()  # 返回 HEX 格式的 MD5


# 上传文件函数
def upload_file_to_tebi(local_file_path, remote_file_name=None):
    """
    将本地文件上传到 Tebi.io 并返回访问链接，避免文件名重复
    :param local_file_path: 本地文件路径，例如 'path/to/example.jpg'
    :param remote_file_name: 存储桶中的文件名（可选），默认使用本地文件名
    :return: 文件的访问链接
    """
    # 检查文件是否存在
    if not os.path.exists(local_file_path):
        print(f"错误: 文件不存在 - {local_file_path}")
        return None

    # 获取文件大小
    file_size = os.path.getsize(local_file_path)
    if file_size == 0:
        print(f"错误: 文件为空 - {local_file_path}")
        return None
    print(f"正在上传文件: {local_file_path}，大小: {file_size} 字节")

    # 如果未指定远程文件名，则使用本地文件名
    if remote_file_name is None:
        remote_file_name = os.path.basename(local_file_path)

    # 分离文件名和扩展名
    base_name, ext = os.path.splitext(remote_file_name)
    final_file_name = remote_file_name

    # 检查文件是否已存在，若存在则生成唯一文件名
    counter = 1
    while file_exists(BUCKET_NAME, final_file_name):
        timestamp = int(time.time())
        final_file_name = f"{base_name}-{timestamp}-{counter}{ext}"
        counter += 1

    try:
        # 读取文件内容
        with open(local_file_path, 'rb') as f:
            file_data = f.read()

        # 计算 Content-MD5（可选，用于完整性检查）
        md5_hex = calculate_md5(local_file_path)

        # 使用 put_object 上传文件，明确指定 Content-Length
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=final_file_name,
            Body=file_data,
            ACL='public-read',
            ContentLength=file_size,  # 明确设置 Content-Length
            ContentMD5=md5_hex  # 可选，提供 MD5 用于完整性检查
        )
        # 生成访问链接
        file_url = f"https://{BUCKET_NAME}/{final_file_name}"
        print(f"文件上传成功: {file_url}")
        return file_url
    except Exception as e:
        print(f"上传失败: Failed to upload {local_file_path} to {BUCKET_NAME}/{final_file_name}: {str(e)}")
        return None
