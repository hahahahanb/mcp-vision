import logging
from typing import Protocol

import httpx

from mcp_ocr.image_utils import ImageInput, normalize_images, read_url_as_base64

logger = logging.getLogger("mcp-ocr")


class VisionProvider(Protocol):
    async def analyze(self, image: ImageInput, prompt: str) -> dict: ...


class OpenAICompatibleProvider:
    def __init__(self, base_url: str, api_key: str, model: str):
        if not api_key:
            raise ValueError("API Key 未配置。请设置对应的环境变量。")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def analyze(self, image: ImageInput, prompt: str) -> dict:
        images = normalize_images(image)
        content = []
        for index, image_data in enumerate(images, start=1):
            if len(images) > 1:
                content.append({"type": "text", "text": f"图片 {index}："})
            image_url = (
                image_data
                if image_data.startswith(("data:", "http"))
                else f"data:image/png;base64,{image_data}"
            )
            content.append({"type": "image_url", "image_url": {"url": image_url}})
        content.append({"type": "text", "text": prompt})

        body = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": content,
                }
            ],
            "max_tokens": 4096,
        }

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        _log_request(url, headers, body)

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json=body)

        if resp.status_code != 200:
            raise RuntimeError(f"API 调用失败 ({resp.status_code}): {resp.text}")

        data = resp.json()
        return {
            "text": data["choices"][0]["message"]["content"],
            "model": data.get("model", self.model),
            "usage": data.get("usage"),
        }


class AnthropicProvider:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        if not api_key:
            raise ValueError("API Key 未配置。请设置 ANTHROPIC_API_KEY 环境变量。")
        self.api_key = api_key
        self.model = model

    async def analyze(self, image: ImageInput, prompt: str) -> dict:
        images = normalize_images(image)
        content = []

        for index, image_data in enumerate(images, start=1):
            if len(images) > 1:
                content.append({"type": "text", "text": f"图片 {index}："})
            content.append(await _anthropic_image_block(image_data))

        content.append({"type": "text", "text": prompt})

        body = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": content}],
        }

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        _log_request(url, headers, body)

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json=body)

        if resp.status_code != 200:
            raise RuntimeError(f"Anthropic API 调用失败 ({resp.status_code}): {resp.text}")

        data = resp.json()
        return {
            "text": data["content"][0]["text"],
            "model": data.get("model", self.model),
            "usage": {
                "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
                "total_tokens": data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0),
            },
        }


async def _anthropic_image_block(image: str) -> dict:
    if image.startswith("http"):
        image = await read_url_as_base64(image)

    if image.startswith("data:"):
        prefix, data = image.split(",", 1)
        media_type = prefix.split(":")[1].split(";")[0]
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": data},
        }

    raise ValueError("Anthropic provider 需要 data URI 或 URL 图片输入")


def _mask(value: str, keep: int = 4) -> str:
    if len(value) <= keep * 2:
        return "***"
    return f"{value[:keep]}...{value[-keep:]}"


def _log_request(url: str, headers: dict, body: dict):
    safe_headers = {
        k: _mask(v) if "key" in k.lower() or "auth" in k.lower() else v
        for k, v in headers.items()
    }

    safe_body = _truncate_base64_in_body(body)

    logger.debug(f"HTTP 请求 → {url}")
    logger.debug(f"  headers: {safe_headers}")
    logger.debug(f"  body: {safe_body}")


def _truncate_base64_in_body(obj, max_len: int = 80):
    if isinstance(obj, dict):
        return {k: _truncate_base64_in_body(v, max_len) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_truncate_base64_in_body(v, max_len) for v in obj]
    if isinstance(obj, str) and (obj.startswith("data:") or len(obj) > max_len):
        return f"{obj[:max_len]}...({len(obj)} chars)"
    return obj
