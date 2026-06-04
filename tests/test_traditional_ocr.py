import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from mcp_ocr.traditional_ocr import BaiduOCRProvider, TencentOCRProvider


class TestBaiduOCRProvider:
    def test_rejects_missing_api_key(self):
        with pytest.raises(ValueError, match="百度 OCR"):
            BaiduOCRProvider(api_key="", secret_key="secret")

    @pytest.mark.asyncio
    async def test_ocr_returns_structured_text(self):
        provider = BaiduOCRProvider(api_key="test-key", secret_key="test-secret")

        mock_token_resp = MagicMock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = {"access_token": "mock-token-123"}

        mock_ocr_resp = MagicMock()
        mock_ocr_resp.status_code = 200
        mock_ocr_resp.json.return_value = {
            "words_result": [
                {"words": "Hello World"},
                {"words": "你好世界"},
            ],
            "words_result_num": 2,
            "log_id": 12345,
        }

        with patch("mcp_ocr.traditional_ocr.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_client.post.side_effect = [mock_token_resp, mock_ocr_resp]

            result = await provider.analyze("data:image/png;base64,abc", "")

        assert "Hello World" in result["text"]
        assert "你好世界" in result["text"]
        assert result["model"] == "baidu-ocr"


class TestTencentOCRProvider:
    def test_rejects_missing_secret_id(self):
        with pytest.raises(ValueError, match="腾讯云 OCR"):
            TencentOCRProvider(secret_id="", secret_key="key")

    @pytest.mark.asyncio
    async def test_ocr_returns_structured_text(self):
        provider = TencentOCRProvider(secret_id="test-id", secret_key="test-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "Response": {
                "TextDetections": [
                    {"DetectedText": "Hello World", "Confidence": 99},
                    {"DetectedText": "你好世界", "Confidence": 98},
                ]
            }
        }

        with patch("mcp_ocr.traditional_ocr.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_client.post.return_value = mock_resp

            result = await provider.analyze("data:image/png;base64,abc", "")

        assert "Hello World" in result["text"]
        assert result["model"] == "tencent-ocr"
