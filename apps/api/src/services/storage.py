import os

import aioboto3


async def upload_image_to_r2(file_bytes: bytes, destination_path: str) -> str:
    """
    Uploads an image to Cloudflare R2 and returns its public URL.
    """
    endpoint_url = os.getenv("R2_ENDPOINT_URL")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
    bucket_name = os.getenv("R2_BUCKET_NAME")
    public_url = os.getenv("R2_PUBLIC_URL")

    if not all([endpoint_url, access_key, secret_key, bucket_name, public_url]):
        raise ValueError("Missing required R2 environment variables")

    session = aioboto3.Session()
    
    async with session.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    ) as s3_client:
        await s3_client.put_object(
            Bucket=bucket_name,
            Key=destination_path,
            Body=file_bytes,
        )
        
    # Ensure no double slashes if public_url ends with slash
    import time
    base_url = public_url.rstrip("/") if public_url else "" # type: ignore
    return f"{base_url}/{destination_path}?v={int(time.time())}"

async def delete_chapter_from_r2(chapter_id: str) -> None:
    """
    Deletes all images associated with a chapter from Cloudflare R2.
    """
    endpoint_url = os.getenv("R2_ENDPOINT_URL")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
    bucket_name = os.getenv("R2_BUCKET_NAME")

    if not all([endpoint_url, access_key, secret_key, bucket_name]):
        return

    session = aioboto3.Session()
    
    async with session.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    ) as s3_client:
        # List all objects with the chapter_id prefix
        paginator = s3_client.get_paginator('list_objects_v2')
        async for page in paginator.paginate(Bucket=bucket_name, Prefix=f"{chapter_id}/"):
            if 'Contents' in page:
                objects_to_delete = [{'Key': obj['Key']} for obj in page['Contents']]
                await s3_client.delete_objects(
                    Bucket=bucket_name,
                    Delete={'Objects': objects_to_delete}
                )
