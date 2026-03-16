"""文件上传路由。

提供 multipart/form-data 文件上传端点，将文件保存到本地 uploads/ 目录并返回访问 URL。
后续可替换为 OSS 存储。
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile

from ai_parenting.backend.schemas import FileUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])

# 允许上传的 MIME 类型白名单
ALLOWED_MIME_PREFIXES = ("audio/", "image/")

# 上传文件大小上限：50MB
MAX_FILE_SIZE = 50 * 1024 * 1024

# 上传目录
UPLOADS_DIR = Path("uploads")


@router.post("/upload", response_model=FileUploadResponse, status_code=201)
async def upload_file(
    request: Request,
    file: UploadFile,
) -> FileUploadResponse:
    """上传文件（音频、图片），保存到本地 uploads/ 目录并返回访问 URL。

    - 校验文件大小上限 50MB
    - 校验 MIME 类型白名单（audio/*, image/*）
    - 使用 UUID 重命名避免路径遍历攻击
    """
    # MIME 类型校验
    content_type = file.content_type or ""
    if not any(content_type.startswith(prefix) for prefix in ALLOWED_MIME_PREFIXES):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type}. Allowed: audio/*, image/*",
        )

    # 读取文件内容并校验大小
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    # 生成安全文件名（UUID + 原始扩展名）
    original_name = file.filename or "unnamed"
    extension = Path(original_name).suffix or ".bin"
    safe_filename = f"{uuid.uuid4().hex}{extension}"

    # 确保上传目录存在
    UPLOADS_DIR.mkdir(exist_ok=True)

    # 保存文件
    file_path = UPLOADS_DIR / safe_filename
    file_path.write_bytes(contents)
    logger.info("File uploaded: %s (%d bytes)", safe_filename, len(contents))

    # 构造访问 URL
    base_url = str(request.base_url).rstrip("/")
    file_url = f"{base_url}/uploads/{safe_filename}"

    return FileUploadResponse(
        url=file_url,
        filename=original_name,
        size=len(contents),
    )
