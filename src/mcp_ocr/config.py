import os

PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "siliconflow": {
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "deepseek-ai/DeepSeek-OCR",
        "env_key": "SILICONFLOW_API_KEY",
        "protocol": "openai",
    },
    "dashscope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-vl-max",
        "env_key": "DASHSCOPE_API_KEY",
        "protocol": "openai",
    },
    "volcengine": {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "doubao-1.5-vision-pro-32k",
        "env_key": "VOLCENGINE_API_KEY",
        "protocol": "openai",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "env_key": "OPENAI_API_KEY",
        "protocol": "openai",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "model": "claude-sonnet-4-6",
        "env_key": "ANTHROPIC_API_KEY",
        "protocol": "anthropic",
    },
    "baidu_ocr": {
        "env_key": "BAIDU_OCR_API_KEY",
        "protocol": "baidu_ocr",
    },
    "tencent_ocr": {
        "env_key": "TENCENT_SECRET_ID",
        "protocol": "tencent_ocr",
    },
}

_PROVIDER_ENV_MAP = {
    "siliconflow": {"key": "SILICONFLOW_API_KEY", "model": "SILICONFLOW_MODEL"},
    "dashscope": {"key": "DASHSCOPE_API_KEY", "model": "DASHSCOPE_MODEL"},
    "volcengine": {"key": "VOLCENGINE_API_KEY", "model": "VOLCENGINE_MODEL"},
    "openai": {"key": "OPENAI_API_KEY", "model": "OPENAI_MODEL"},
    "anthropic": {"key": "ANTHROPIC_API_KEY", "model": "ANTHROPIC_MODEL"},
    "baidu_ocr": {"key": "BAIDU_OCR_API_KEY", "model": None},
    "tencent_ocr": {"key": "TENCENT_SECRET_ID", "model": None},
}


def load_config() -> dict:
    provider = os.environ.get("MCP_OCR_PROVIDER", "siliconflow").lower()

    if provider in PROVIDER_PRESETS:
        preset = PROVIDER_PRESETS[provider]
        env = _PROVIDER_ENV_MAP[provider]
        result = {
            "provider": provider,
            "protocol": preset["protocol"],
            "api_key": os.environ.get(env["key"]),
        }
        if "base_url" in preset:
            result["base_url"] = preset["base_url"]
        if env["model"]:
            result["model"] = os.environ.get(env["model"], preset.get("model", ""))
        if provider == "baidu_ocr":
            result["secret_key"] = os.environ.get("BAIDU_OCR_SECRET_KEY")
        if provider == "tencent_ocr":
            result["secret_key"] = os.environ.get("TENCENT_SECRET_KEY")
        return result

    # custom provider
    return {
        "provider": "custom",
        "protocol": "openai",
        "base_url": os.environ.get("MCP_OCR_BASE_URL", ""),
        "model": os.environ.get("MCP_OCR_MODEL", ""),
        "api_key": os.environ.get("MCP_OCR_API_KEY"),
    }
