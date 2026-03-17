"""文件上传路由。

提供 multipart/form-data 文件上传端点，将文件保存到本地 uploads/ 目录并返回访问 URL。
后续可替换为 OSS 存储。
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile

from ai_parenting.backend.auth import get_current_user_id
from ai_parenting.backend.schemas import FileUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])

# 允许上传的 MIME 类型白名单
ALLOWED_MIME_PREFIXES = ("audio/", "image/")

# 上传文件大小上限：50MB
MAX_FILE_SIZE = 50 * 1024 * 1024

# 上传目录
UPLOADS_DIR = Path("uploads")

# 文件 magic number 校验表
_MAGIC_NUMBERS: dict[bytes, str] = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"RIFF": "audio/wav",
    b"ID3": "audio/mpeg",
    b"\xff\xfb": "audio/mpeg",
    b"\xff\xf3": "audio/mpeg",
    b"fLaC": "audio/flac",
    b"OggS": "audio/ogg",
}

# 分块读取大小
_CHUNK_SIZE = 64 * 1024  # 64KB


def _validate_magic_bytes(header: bytes) -> bool:
    """通过 magic number 验证文件内容真实性。"""
    for magic, _ in _MAGIC_NUMBERS.items():
        if header.startswith(magic):
            return True
    # M4A/MP4 容器格式
    if len(header) >= 8 and header[4:8] == b"ftyp":
        return True
    return False


@router.post("/upload", response_model=FileUploadResponse, status_code=201)
async def upload_file(
    request: Request,
    file: UploadFile,
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> FileUploadResponse:
    """上传文件（音频、图片），保存到本地 uploads/ 目录并返回访问 URL。

    - 校验文件大小上限 50MB
    - 校验 MIME 类型白名单（audio/*, image/*）
    - 校验文件 magic number 防止伪造 Content-Type
    - 使用 UUID 重命名避免路径遍历攻击
    - 使用 aiofiles 流式写入避免阻塞事件循环
    """
    # MIME 类型校验
    content_type = file.content_type or ""
    if not any(content_type.startswith(prefix) for prefix in ALLOWED_MIME_PREFIXES):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type}. Allowed: audio/*, image/*",
        )

    # 生成安全文件名（UUID + 原始扩展名）
    original_name = file.filename or "unnamed"
    extension = Path(original_name).suffix or ".bin"
    safe_filename = f"{uuid.uuid4().hex}{extension}"

    # 确保上传目录存在
    UPLOADS_DIR.mkdir(exist_ok=True)
    file_path = UPLOADS_DIR / safe_filename

    # 流式读取并写入文件，同时校验大小和 magic bytes
    total_size = 0
    first_chunk = True

    try:
        async with aiofiles.open(file_path, "wb") as f:
            while True:
                chunk = await file.read(_CHUNK_SIZE)
                if not chunk:
                    break

                # 首块校验 magic number
                if first_chunk:
                    if not _validate_magic_bytes(chunk[:16]):
                        raise HTTPException(
                            status_code=400,
                            detail="File content does not match declared MIME type",
                        )
                    first_chunk = True

                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    # 超大文件：删除已写入部分并返回错误
                    await f.close()
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)}MB",
                    )

                await f.write(chunk)
                first_chunk = False

    except HTTPException:
        # 重新抛出 HTTP 异常
        file_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        file_path.unlink(missing_ok=True)
        logger.error("File upload failed: %s", exc)
        raise HTTPException(status_code=500, detail="File upload failed") from exc

    logger.info("File uploaded: %s (%d bytes)", safe_filename, total_size)

    # 构造访问 URL
    base_url = str(request.base_url).rstrip("/")
    file_url = f"{base_url}/uploads/{safe_filename}"

    return FileUploadResponse(
        url=file_url,
        filename=original_name,
        size=total_size,
    )
