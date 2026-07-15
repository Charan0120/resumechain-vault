import os
import hashlib
import uuid
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError


# ── S3 Client ─────────────────────────────────────────────────
def _get_client():
    return boto3.client(
        "s3",
        region_name=os.getenv("AWS_REGION", "ap-south-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


BUCKET = lambda: os.getenv("AWS_S3_BUCKET")

# Allowed MIME types and extensions
ALLOWED_EXTENSIONS = {"pdf", "docx", "doc"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ── Helpers ───────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def compute_sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


# ── Upload ────────────────────────────────────────────────────

def upload_resume(file_obj, user_id: str) -> dict:
    """
    Uploads a resume file to S3 with server-side AES-256 encryption.

    Returns a dict with:
      - s3_key: the key in the S3 bucket
      - file_hash: SHA-256 hex digest of the file bytes
      - file_size: size in bytes
      - content_type: MIME type
      - original_filename: sanitized filename

    Raises ValueError for invalid files.
    """
    original_filename = file_obj.filename

    if not allowed_file(original_filename):
        raise ValueError("Only PDF, DOCX, and DOC files are allowed.")

    file_bytes = file_obj.read()

    if len(file_bytes) == 0:
        raise ValueError("Uploaded file is empty.")
    if len(file_bytes) > MAX_FILE_SIZE:
        raise ValueError("File exceeds the 10 MB limit.")

    # Detect content type from filename extension
    ext = original_filename.rsplit(".", 1)[1].lower()
    content_type_map = {
        "pdf":  "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "doc":  "application/msword",
    }
    content_type = content_type_map.get(ext, "application/octet-stream")

    # Compute hash before upload
    file_hash = compute_sha256(file_bytes)

    # Build a unique S3 key: resumes/<user_id>/<uuid>_<timestamp>.<ext>
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    s3_key = f"resumes/{user_id}/{unique_id}_{timestamp}.{ext}"

    # Upload with server-side AES-256 encryption
    client = _get_client()
    client.put_object(
        Bucket=BUCKET(),
        Key=s3_key,
        Body=file_bytes,
        ContentType=content_type,
        ServerSideEncryption="AES256",
        Metadata={
            "original-filename": original_filename,
            "user-id": user_id,
            "sha256": file_hash,
        },
    )

    return {
        "s3_key": s3_key,
        "file_hash": file_hash,
        "file_size": len(file_bytes),
        "content_type": content_type,
        "original_filename": original_filename,
    }


# ── Pre-signed Download URL ────────────────────────────────────

def generate_download_url(s3_key: str, filename: str, expiry: int = 900) -> str:
    """
    Generates a pre-signed URL valid for `expiry` seconds (default 15 min).
    The browser will prompt a download with the original filename.
    """
    client = _get_client()
    url = client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": BUCKET(),
            "Key": s3_key,
            "ResponseContentDisposition": f'attachment; filename="{filename}"',
        },
        ExpiresIn=expiry,
    )
    return url


# ── Delete ────────────────────────────────────────────────────

def delete_resume(s3_key: str) -> None:
    """Deletes a file from S3. Raises ClientError on failure."""
    client = _get_client()
    client.delete_object(Bucket=BUCKET(), Key=s3_key)


# ── Stream File (server-side download) ───────────────────────

def stream_file(s3_key: str) -> bytes:
    """
    Downloads the file from S3 on the server side and returns raw bytes.
    The S3 URL is NEVER sent to the user — Flask serves the file directly.
    This prevents AWS credentials or S3 URLs from being exposed in the browser.
    """
    client = _get_client()
    response = client.get_object(Bucket=BUCKET(), Key=s3_key)
    return response["Body"].read()

