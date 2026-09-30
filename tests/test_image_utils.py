import pytest
from pathlib import Path
import httpx
from mcp_ocr.image_utils import (
    is_supported_format,
    validate_image_path,
    read_file_as_base64,
    is_url,
    normalize_images,
    read_url_as_base64,
)


class TestIsSupportedFormat:
    def test_accepts_common_image_formats(self):
        for ext in ["png", "jpg", "jpeg", "gif", "bmp", "webp", "pdf"]:
            assert is_supported_format(f"test.{ext}") is True

    def test_case_insensitive(self):
        assert is_supported_format("photo.JPG") is True
        assert is_supported_format("doc.PDF") is True

    def test_rejects_unsupported(self):
        assert is_supported_format("test.txt") is False
        assert is_supported_format("script.exe") is False


class TestValidateImagePath:
    def test_rejects_path_traversal(self):
        with pytest.raises(ValueError, match="路径不合法"):
            validate_image_path("../../etc/passwd")
        with pytest.raises(ValueError, match="路径不合法"):
            validate_image_path("..\\Windows\\System32")

    def test_rejects_unsupported_format(self):
        with pytest.raises(ValueError, match="不支持的文件格式"):
            validate_image_path("test.exe")

    def test_rejects_nonexistent_file(self):
        with pytest.raises(ValueError, match="文件不存在"):
            validate_image_path("nonexistent_image_abc123.png")


class TestReadFileAsBase64:
    def test_returns_data_uri(self, tmp_path: Path):
        f = tmp_path / "test.png"
        f.write_bytes(b"\x89PNG\r\n\x1a\n")
        result = read_file_as_base64(str(f))
        assert result.startswith("data:image/png;base64,")

    def test_rejects_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            read_file_as_base64("/nonexistent/file.png")


class TestIsUrl:
    def test_http_urls(self):
        assert is_url("https://example.com/img.png") is True
        assert is_url("http://example.com/img.png") is True

    def test_non_urls(self):
        assert is_url("/path/to/file.png") is False
        assert is_url("C:\\Users\\test.png") is False
        assert is_url("just some text") is False


class TestNormalizeImages:
    def test_accepts_a_single_image_or_an_ordered_list(self):
        assert normalize_images("first.png") == ["first.png"]
        assert normalize_images(["first.png", "https://example.com/second.png"]) == [
            "first.png",
            "https://example.com/second.png",
        ]

    def test_rejects_empty_lists_and_invalid_items(self):
        with pytest.raises(ValueError, match="至少需要提供一张图片"):
            normalize_images([])
        with pytest.raises(ValueError, match="不能为空"):
            normalize_images(["first.png", ""])
        with pytest.raises(ValueError, match="必须是字符串"):
            normalize_images(["first.png", 2])


class TestReadUrlAsBase64:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("headers", [{"content-type": "image/png; charset=binary"}, {}])
    async def test_returns_data_uri_and_checks_content_type(self, headers, monkeypatch):
        requests = []
        def handler(request):
            requests.append(request)
            return httpx.Response(200, headers=headers, content=b"image bytes")
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client)
        result = await read_url_as_base64("https://example.com/image.png")
        assert result == "data:image/png;base64,aW1hZ2UgYnl0ZXM="
        assert len(requests) == 1
        assert str(requests[0].url) == "https://example.com/image.png"

    @pytest.mark.asyncio
    async def test_rejects_non_image_url_content(self, monkeypatch):
        client = httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html />")
        ))
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client)
        with pytest.raises(ValueError, match="远程内容类型不支持"):
            await read_url_as_base64("https://example.com/not-an-image")

    @pytest.mark.asyncio
    async def test_stops_reading_and_closes_stream_when_size_limit_is_exceeded(self, monkeypatch):
        from mcp_ocr import image_utils
        consumed = []
        closed = []

        class ImageStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                for chunk in (b"123", b"456", b"789"):
                    consumed.append(chunk)
                    yield chunk

            async def aclose(self):
                closed.append(True)

        client = httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, headers={"content-type": "image/png"}, stream=ImageStream())
        ))
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client)
        monkeypatch.setattr(image_utils, "MAX_FILE_SIZE", 4)
        with pytest.raises(ValueError, match="图片过大"):
            await read_url_as_base64("https://example.com/large.png")
        assert consumed == [b"123", b"456"]
        assert closed == [True]
