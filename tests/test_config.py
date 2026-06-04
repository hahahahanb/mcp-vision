import os
import pytest
from mcp_ocr.config import load_config, PROVIDER_PRESETS


class TestLoadConfig:
    def test_default_provider_is_siliconflow(self, monkeypatch):
        monkeypatch.delenv("MCP_OCR_PROVIDER", raising=False)
        monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)
        config = load_config()
        assert config["provider"] == "siliconflow"
        assert config["base_url"] == PROVIDER_PRESETS["siliconflow"]["base_url"]
        assert config["model"] == PROVIDER_PRESETS["siliconflow"]["model"]

    def test_siliconflow_with_custom_model(self, monkeypatch):
        monkeypatch.setenv("SILICONFLOW_API_KEY", "sk-test")
        monkeypatch.setenv("SILICONFLOW_MODEL", "custom-model")
        config = load_config()
        assert config["api_key"] == "sk-test"
        assert config["model"] == "custom-model"

    def test_dashscope_provider(self, monkeypatch):
        monkeypatch.setenv("MCP_OCR_PROVIDER", "dashscope")
        monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-dash")
        config = load_config()
        assert config["provider"] == "dashscope"
        assert config["base_url"] == PROVIDER_PRESETS["dashscope"]["base_url"]
        assert config["api_key"] == "sk-dash"

    def test_custom_provider(self, monkeypatch):
        monkeypatch.setenv("MCP_OCR_PROVIDER", "custom")
        monkeypatch.setenv("MCP_OCR_API_KEY", "sk-custom")
        monkeypatch.setenv("MCP_OCR_BASE_URL", "https://my-api.com/v1")
        monkeypatch.setenv("MCP_OCR_MODEL", "my-model")
        config = load_config()
        assert config["base_url"] == "https://my-api.com/v1"
        assert config["model"] == "my-model"
        assert config["api_key"] == "sk-custom"

    def test_missing_api_key_returns_none(self, monkeypatch):
        monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)
        monkeypatch.delenv("MCP_OCR_PROVIDER", raising=False)
        config = load_config()
        assert config["api_key"] is None
