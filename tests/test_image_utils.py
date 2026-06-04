import pytest
from pathlib import Path
from mcp_ocr.image_utils import is_supported_format, validate_image_path, read_file_as_base64, is_url


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