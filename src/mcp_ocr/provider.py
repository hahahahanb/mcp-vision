import base64
import httpx
from typing import Protocol


class VisionProvider(Protocol):
    async def analyze(self, image: str, prompt: str) -> dict: ...


class OpenAICompatibleProvider:
    def __init__(self, base_url: str, api_key: str, model: str):
        if not api_key:
            raise ValueError("API Key 未配置。请设置对应的环境变量。")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def analyze(self, image: str, prompt: str) -> dict:
        image_url = image if image.startswith(("data:", "http")) else f"data:image/png;base64,{image}"

        body = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "max_tokens": 4096,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json=body,
            )

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

    async def analyze(self, image: str, prompt: str) -> dict:
        if image.startswith("data:"):
            prefix, data = image.split(",", 1)
            media_type = prefix.split(":")[1].split(";")[0]
            image_block = {
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": data},
            }
        elif image.startswith("http"):
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(image)
                if resp.status_code != 200:
                    raise RuntimeError(f"下载图片失败 ({resp.status_code})")
                content_type = resp.headers.get("content-type", "image/png")
                image_block = {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": content_type,
                        "data": base64.b64encode(resp.content).decode("utf-8"),
                    },
                }
        else:
            raise ValueError("Anthropic provider 需要 data URI 或 URL 图片输入")

        body = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": [image_block, {"type": "text", "text": prompt}],
                }
            ],
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                },
                json=body,
            )

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
