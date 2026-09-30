from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ocr import server
from mcp_ocr.traditional_ocr import BaiduOCRProvider, TencentOCRProvider


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", [server.analyze_image, server.ocr_extract])
async def test_multiple_images_with_traditional_provider_prompt_use_precise(monkeypatch, tool):
    provider = BaiduOCRProvider("test-key", "test-secret")
    provider.analyze = AsyncMock()
    monkeypatch.setattr(server, "_get_provider", lambda: provider)
    monkeypatch.setattr(server, "_resolve_images", lambda image: ["first", "second"])
    result = await tool(["one.png", "two.png"])
    assert "多图输入请使用 ocr_precise" in result
    provider.analyze.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("multiple", [False, True])
async def test_mcp_call_accepts_single_and_multiple_images(tmp_path, monkeypatch, multiple):
    image = tmp_path / "one.png"
    image.write_bytes(b"first")
    provider = AsyncMock()
    provider.analyze.return_value = {"text": "完成", "model": "test", "usage": None}
    monkeypatch.setattr(server, "_get_provider", lambda: provider)
    references = [str(image), "https://example.com/two.png"] if multiple else str(image)
    await server.mcp.call_tool("analyze_image", {"image": references, "prompt": "用户提示词"})
    expected = ["data:image/png;base64,Zmlyc3Q=", "https://example.com/two.png"] if multiple else "data:image/png;base64,Zmlyc3Q="
    provider.analyze.assert_awaited_once_with(expected, "用户提示词")


@pytest.mark.asyncio
async def test_precise_ocr_downloads_url_and_preserves_local_image_order(tmp_path, monkeypatch):
    image = tmp_path / "first.png"
    image.write_bytes(b"first")
    monkeypatch.setattr(server, "load_config", lambda: {"protocol": "tencent_ocr"})
    download = AsyncMock(return_value="data:image/png;base64,second")
    monkeypatch.setattr(server, "read_url_as_base64", download)
    provider = AsyncMock()
    provider.analyze.side_effect = [
        {"text": "第一页", "model": "tencent-ocr", "usage": None},
        {"text": "第二页", "model": "tencent-ocr", "usage": None},
    ]
    monkeypatch.setattr(server, "_get_provider", lambda: provider)
    result = await server.ocr_precise([str(image), "https://example.com/second.png"])
    download.assert_awaited_once_with("https://example.com/second.png")
    assert [call.args[0] for call in provider.analyze.await_args_list] == [
        "data:image/png;base64,Zmlyc3Q=", "data:image/png;base64,second"
    ]
    assert result.index("第一页") < result.index("第二页")


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", [server.analyze_image, server.ocr_extract])
@pytest.mark.parametrize("provider_type", [BaiduOCRProvider, TencentOCRProvider])
async def test_single_image_tools_keep_traditional_provider_compatible(monkeypatch, tool, provider_type):
    if provider_type is BaiduOCRProvider:
        provider = BaiduOCRProvider("test-key", "test-secret")
        provider._access_token = "test-token"
    else:
        provider = TencentOCRProvider("test-id", "test-secret")
    monkeypatch.setattr(server, "_get_provider", lambda: provider)
    monkeypatch.setattr(server, "_resolve_images", lambda image: ["data:image/png;base64,one"])
    with patch("mcp_ocr.traditional_ocr.httpx.AsyncClient") as client_type:
        client = AsyncMock()
        client_type.return_value.__aenter__.return_value = client
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "words_result": [{"words": "识别成功"}],
            "Response": {"TextDetections": [{"DetectedText": "识别成功"}]},
        }
        client.post.return_value = response
        result = await tool("one.png")
    assert "识别成功" in result
    client.post.assert_awaited_once()


def test_resolve_images_preserves_local_and_remote_order(tmp_path):
    local_image = tmp_path / "first.png"
    local_image.write_bytes(b"first")

    result = server._resolve_images(
        [str(local_image), "https://example.com/second.png"]
    )

    assert result == [
        "data:image/png;base64,Zmlyc3Q=",
        "https://example.com/second.png",
    ]


@pytest.mark.asyncio
async def test_tool_schema_accepts_single_or_multiple_images():
    tools = {tool.name: tool for tool in await server.mcp.list_tools()}

    for tool_name in ("analyze_image", "ocr_extract", "ocr_precise"):
        image_schema = tools[tool_name].inputSchema["properties"]["image"]
        choices = image_schema.get("anyOf", image_schema.get("oneOf", []))
        assert {choice["type"] for choice in choices} == {"string", "array"}
        array_schema = next(choice for choice in choices if choice["type"] == "array")
        assert array_schema["items"]["type"] == "string"


@pytest.mark.asyncio
async def test_analyze_image_preserves_single_image_call(monkeypatch):
    monkeypatch.setattr(server, "_resolve_images", lambda image: ["data:image/png;base64,one"])
    provider = AsyncMock()
    provider.analyze.return_value = {"text": "描述", "model": "test-model", "usage": None}
    monkeypatch.setattr(server, "_get_provider", lambda: provider)

    result = await server.analyze_image("one.png")

    provider.analyze.assert_awaited_once_with(
        "data:image/png;base64,one", "请详细描述这张图片的内容"
    )
    assert "描述" in result


@pytest.mark.asyncio
async def test_analyze_image_passes_multiple_images_and_default_prompt(monkeypatch):
    monkeypatch.setattr(
        server,
        "_resolve_images",
        lambda image: ["data:image/png;base64,one", "data:image/png;base64,two"],
    )
    provider = AsyncMock()
    provider.analyze.return_value = {"text": "比较结果", "model": "test-model", "usage": None}
    monkeypatch.setattr(server, "_get_provider", lambda: provider)

    result = await server.analyze_image(["one.png", "two.png"])

    provider.analyze.assert_awaited_once_with(
        ["data:image/png;base64,one", "data:image/png;base64,two"],
        "请逐张详细描述这些图片的内容，并指出图片之间的关联（如有）。",
    )
    assert "比较结果" in result


@pytest.mark.asyncio
async def test_ocr_extract_passes_multiple_images_and_default_prompt(monkeypatch):
    monkeypatch.setattr(
        server,
        "_resolve_images",
        lambda image: ["data:image/png;base64,one", "data:image/jpeg;base64,two"],
    )
    provider = AsyncMock()
    provider.analyze.return_value = {"text": "文字", "model": "test-model", "usage": None}
    monkeypatch.setattr(server, "_get_provider", lambda: provider)

    result = await server.ocr_extract(["one.png", "two.jpg"])

    provider.analyze.assert_awaited_once_with(
        ["data:image/png;base64,one", "data:image/jpeg;base64,two"],
        "请按输入顺序逐张提取所有图片中的文字并分别分段，保持原始排版格式。如果有代码，请用代码块包裹。",
    )
    assert "文字" in result


@pytest.mark.asyncio
async def test_ocr_precise_processes_images_in_order_and_groups_results(monkeypatch):
    monkeypatch.setattr(server, "load_config", lambda: {"protocol": "baidu_ocr"})
    monkeypatch.setattr(
        server,
        "_resolve_images",
        lambda image: ["data:image/png;base64,one", "data:image/png;base64,two"],
    )
    monkeypatch.setattr(
        server,
        "_resolve_precise_images",
        AsyncMock(side_effect=lambda images: images),
    )
    provider = AsyncMock()
    provider.analyze.side_effect = [
        {"text": "第一张的文字", "model": "baidu-ocr", "usage": {"total_words": 2}},
        {"text": "第二张的文字", "model": "baidu-ocr", "usage": {"total_words": 3}},
    ]
    monkeypatch.setattr(server, "_get_provider", lambda: provider)

    result = await server.ocr_precise(["one.png", "two.png"])

    assert provider.analyze.await_args_list[0].args == ("data:image/png;base64,one", "")
    assert provider.analyze.await_args_list[1].args == ("data:image/png;base64,two", "")
    assert result.index("第一张的文字") < result.index("第二张的文字")
    assert "### 图片 1" in result
    assert "### 图片 2" in result
    assert "total_words: 3" in result
