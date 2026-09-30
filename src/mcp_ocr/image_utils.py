import base64
from pathlib import Path

import httpx

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".pdf"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
ImageInput = str | list[str]

MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}


def is_supported_format(filepath: str) -> bool:
    return Path(filepath).suffix.lower() in SUPPORTED_EXTENSIONS


def validate_image_path(filepath: str) -> None:
    if ".." in filepath:
        raise ValueError(f"路径不合法: 不允许包含 '..'")

    resolved = Path(filepath).resolve()

    if not is_supported_format(str(resolved)):
        raise ValueError(f"不支持的文件格式: {resolved.suffix}。支持: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")

    if not resolved.exists():
        raise ValueError(f"文件不存在: {resolved}")


def read_file_as_base64(filepath: str) -> str:
    resolved = Path(filepath).resolve()

    if not resolved.exists():
        raise FileNotFoundError(f"文件不存在: {resolved}")

    ext = resolved.suffix.lower()
    mime = MIME_MAP.get(ext)
    if not mime:
        raise ValueError(f"不支持的文件格式: {ext}")

    data = resolved.read_bytes()
    if len(data) > MAX_FILE_SIZE:
        raise ValueError(f"文件过大: {len(data) / 1024 / 1024:.1f}MB，上限 20MB")

    encoded = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def is_url(text: str) -> bool:
    return text.startswith("http://") or text.startswith("https://")


def normalize_images(image: ImageInput) -> list[str]:
    """Normalize a single image reference or an ordered list of references."""
    if isinstance(image, str):
        images = [image]
    elif isinstance(image, list):
        images = image
    else:
        raise ValueError("image 必须是图片路径/URL 或其列表")

    if not images:
        raise ValueError("至少需要提供一张图片")

    if any(not isinstance(item, str) or not item.strip() for item in images):
        raise ValueError("图片路径/URL 不能为空，且必须是字符串")

    return images


async def read_url_as_base64(url: str) -> str:
    """Download a remote image and return it as a data URI."""
    async with httpx.AsyncClient(timeout=30) as client:
        async with client.stream("GET", url) as resp:
            if resp.status_code != 200:
                raise RuntimeError(f"下载图片失败 ({resp.status_code})")

            mime = resp.headers.get("content-type", "image/png").split(";", 1)[0].strip().lower()
            if mime not in MIME_MAP.values():
                raise ValueError(f"远程内容类型不支持: {mime or '未知'}")

            data = bytearray()
            async for chunk in resp.aiter_bytes():
                if len(data) + len(chunk) > MAX_FILE_SIZE:
                    raise ValueError("图片过大，上限 20MB")
                data.extend(chunk)

    encoded = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{encoded}"
