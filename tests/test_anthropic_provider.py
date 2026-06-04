import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from mcp_ocr.provider import AnthropicProvider


class TestAnthropicProvider:
    def test_rejects_missing_api_key(self):
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            AnthropicProvider(api_key="", model="claude-sonnet-4-6")

    @pytest.mark.asyncio
    async def test_analyze_with_data_uri(self):
        mock_response = {
            "content": [{"type": "text", "text": "这是一张狗的图片"}],
            "model": "claude-sonnet-4-6",
            "usage": {"input_tokens": 200, "output_tokens": 80},
        }

        provider = AnthropicProvider(api_key="sk-ant-test", model="claude-sonnet-4-6")

        with patch("mcp_ocr.provider.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_response
            mock_client.post.return_value = mock_resp

            result = await provider.analyze("data:image/png;base64,abc123", "描述图片")

        assert result["text"] == "这是一张狗的图片"
        assert result["model"] == "claude-sonnet-4-6"
        assert result["usage"]["total_tokens"] == 280

    @pytest.mark.asyncio
    async def test_analyze_sends_correct_headers(self):
        provider = AnthropicProvider(api_key="sk-ant-test", model="claude-sonnet-4-6")

        with patch("mcp_ocr.provider.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "content": [{"type": "text", "text": "ok"}],
                "model": "claude-sonnet-4-6",
                "usage": {"input_tokens": 10, "output_tokens": 5},
            }
            mock_client.post.return_value = mock_resp

            await provider.analyze("data:image/png;base64,abc", "test")

            call_kwargs = mock_client.post.call_args
            headers = call_kwargs.kwargs.get("headers", call_kwargs[1].get("headers", {}))
            assert headers.get("x-api-key") == "sk-ant-test"
            assert "anthropic-version" in headers
