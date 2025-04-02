import hashlib
import os
import time
import logging

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

# Set up logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Configure Tebi.io credentials and endpoint
ACCESS_KEY = os.getenv('TEBI_ACCESS_KEY')
SECRET_KEY = os.getenv('TEBI_SECRET_KEY')
ENDPOINT_URL = 'http://s3.tebi.io'
BUCKET_NAME = 'src.ziqizhu.com'  # Replace with your bucket name

# Check if environment variables are configured
if not (ACCESS_KEY and SECRET_KEY):
    logger.warning("Missing Tebi.io configuration (TEBI_ACCESS_KEY/TEBI_SECRET_KEY). Image to video features will be disabled.")

# Create S3 client
s3_client = None
if ACCESS_KEY and SECRET_KEY:
    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=ENDPOINT_URL,
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY,
            config=Config(signature_version='s3v4')
        )
    except Exception as e:
        logger.error(f"Failed to initialize Tebi.io client: {str(e)}")


# Check if file exists helper function
def file_exists(bucket, key):
    if not s3_client:
        return False
    
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        raise e


# Calculate MD5 hash (hex encoded)
def calculate_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


# Upload file function
def upload_file_to_tebi(local_file_path, remote_file_name=None):
    """
    Upload a local file to Tebi.io and return the access link, avoiding duplicate filenames
    If Tebi.io is not configured, this function will return None
    :param local_file_path: Local file path, e.g., 'path/to/example.jpg'
    :param remote_file_name: Filename in the bucket (optional), defaults to local filename
    :return: File access link or None if failed
    """
    # Check if Tebi.io is properly configured
    if not s3_client:
        logger.error("Tebi.io client not initialized. Cannot upload file.")
        return None
        
    # Check if file exists
    if not os.path.exists(local_file_path):
        logger.error(f"Error: File does not exist - {local_file_path}")
        return None

    # Get file size
    file_size = os.path.getsize(local_file_path)
    if file_size == 0:
        logger.error(f"Error: File is empty - {local_file_path}")
        return None
    logger.info(f"Uploading file: {local_file_path}, size: {file_size} bytes")

    # If remote filename not specified, use local filename
    if remote_file_name is None:
        remote_file_name = os.path.basename(local_file_path)

    # Split filename and extension
    base_name, ext = os.path.splitext(remote_file_name)
    final_file_name = remote_file_name

    # Check if file already exists, if so, generate unique filename
    counter = 1
    while file_exists(BUCKET_NAME, final_file_name):
        timestamp = int(time.time())
        final_file_name = f"{base_name}-{timestamp}-{counter}{ext}"
        counter += 1

    try:
        # Read file content
        with open(local_file_path, 'rb') as f:
            file_data = f.read()

        # Calculate Content-MD5 (optional, for integrity check)
        md5_hex = calculate_md5(local_file_path)

        # Use put_object to upload file, explicitly specify Content-Length
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=final_file_name,
            Body=file_data,
            ACL='public-read',
            ContentLength=file_size,  # Explicitly set Content-Length
            ContentMD5=md5_hex  # Optional, provide MD5 for integrity check
        )
        # Generate access link
        file_url = f"https://{BUCKET_NAME}/{final_file_name}"
        logger.info(f"File uploaded successfully: {file_url}")
        return file_url
    except Exception as e:
        logger.error(f"Upload failed: Failed to upload {local_file_path} to {BUCKET_NAME}/{final_file_name}: {str(e)}")
        return None
