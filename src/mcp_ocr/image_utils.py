import base64
from pathlib import Path

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".pdf"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

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