import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from mcp_ocr.provider import OpenAICompatibleProvider


class TestOpenAICompatibleProvider:
    def test_rejects_missing_api_key(self):
        with pytest.raises(ValueError, match="API Key"):
            OpenAICompatibleProvider(
                base_url="https://api.test.com/v1",
                api_key="",
                model="test-model",
            )

    @pytest.mark.asyncio
    async def test_analyze_returns_result(self):
        mock_response = {
            "choices": [{"message": {"content": "这是一张猫的图片"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            "model": "test-model",
        }

        provider = OpenAICompatibleProvider(
            base_url="https://api.test.com/v1",
            api_key="sk-test",
            model="test-model",
        )

        with patch("mcp_ocr.provider.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_response
            mock_resp.raise_for_status = lambda: None
            mock_client.post.return_value = mock_resp

            result = await provider.analyze("data:image/png;base64,abc", "描述图片")

        assert result["text"] == "这是一张猫的图片"
        assert result["model"] == "test-model"
        assert result["usage"]["total_tokens"] == 150

    @pytest.mark.asyncio
    async def test_analyze_throws_on_api_error(self):
        provider = OpenAICompatibleProvider(
            base_url="https://api.test.com/v1",
            api_key="sk-test",
            model="test-model",
        )

        with patch("mcp_ocr.provider.httpx.AsyncClient") as mock_client_cls:
            import httpx
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.status_code = 401
            mock_resp.text = "Unauthorized"
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Unauthorized", request=None, response=mock_resp
            )
            mock_client.post.return_value = mock_resp

            with pytest.raises(RuntimeError, match="API 调用失败"):
                await provider.analyze("data:image/png;base64,abc", "描述图片")
