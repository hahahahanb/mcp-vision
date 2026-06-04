from mcp.server.fastmcp import FastMCP

from mcp_ocr.config import load_config
from mcp_ocr.provider import OpenAICompatibleProvider, AnthropicProvider
from mcp_ocr.traditional_ocr import BaiduOCRProvider, TencentOCRProvider
from mcp_ocr.image_utils import validate_image_path, read_file_as_base64, is_url

mcp = FastMCP(
    "mcp-ocr",
    instructions="图像识别服务。提供图片分析（analyze_image）、文字提取（ocr_extract）和精准 OCR（ocr_precise）工具。支持本地文件路径和远程 URL。支持硅基流动/阿里/火山/OpenAI/Anthropic/百度OCR/腾讯云OCR。",
)

_provider = None


def _get_provider():
    global _provider
    if _provider is None:
        config = load_config()
        protocol = config.get("protocol", "openai")
        api_key = config.get("api_key") or ""

        if protocol == "anthropic":
            _provider = AnthropicProvider(
                api_key=api_key,
                model=config.get("model", "claude-sonnet-4-6"),
            )
        elif protocol == "baidu_ocr":
            _provider = BaiduOCRProvider(
                api_key=api_key,
                secret_key=config.get("secret_key", ""),
            )
        elif protocol == "tencent_ocr":
            _provider = TencentOCRProvider(
                secret_id=api_key,
                secret_key=config.get("secret_key", ""),
            )
        else:
            _provider = OpenAICompatibleProvider(
                base_url=config.get("base_url", ""),
                api_key=api_key,
                model=config.get("model", ""),
            )
    return _provider


def _resolve_image(image: str) -> str:
    if is_url(image):
        return image
    validate_image_path(image)
    return read_file_as_base64(image)


def _format_result(title: str, text: str, model: str, usage: dict | None) -> str:
    lines = [f"## {title}", "", text, "", "---", f"模型: {model}"]
    if usage:
        lines.append(f"Token 用量: 输入 {usage.get('prompt_tokens', '?')} / 输出 {usage.get('completion_tokens', '?')} / 总计 {usage.get('total_tokens', '?')}")
    return "\n".join(lines)


@mcp.tool()
async def analyze_image(image: str, prompt: str | None = None) -> str:
    """分析图片内容。支持本地文件路径和远程 URL。可用于图像描述、视觉问答、图表分析等场景。

    Args:
        image: 图片路径（本地绝对路径）或远程 URL
        prompt: 分析提示词，描述你希望如何分析这张图片。默认详细描述图片内容
    """
    try:
        image_data = _resolve_image(image)
        provider = _get_provider()
        result = await provider.analyze(image_data, prompt or "请详细描述这张图片的内容")
        return _format_result("图像分析结果", result["text"], result["model"], result.get("usage"))
    except Exception as e:
        return f"图像分析失败: {e}"


@mcp.tool()
async def ocr_extract(image: str, prompt: str | None = None) -> str:
    """从图片或 PDF 中提取文字（OCR）。适合识别截图、文档、代码中的文本内容。

    Args:
        image: 图片或 PDF 文件路径（本地绝对路径）或远程 URL
        prompt: OCR 提示词。默认提取并格式化所有文字内容
    """
    try:
        image_data = _resolve_image(image)
        provider = _get_provider()
        ocr_prompt = prompt or "请完整提取图片中的所有文字内容，保持原始排版格式。如果有代码，请用代码块包裹。"
        result = await provider.analyze(image_data, ocr_prompt)
        return _format_result("OCR 提取结果", result["text"], result["model"], result.get("usage"))
    except Exception as e:
        return f"OCR 提取失败: {e}"


@mcp.tool()
async def ocr_precise(image: str) -> str:
    """使用传统 OCR 引擎精准提取图片中的文字（返回结构化结果，含文字坐标和置信度）。
    需要配置百度 OCR 或腾讯云 OCR 作为 Provider。
    适合需要精确文字位置信息的场景（如发票、卡证、表格）。

    Args:
        image: 图片文件路径（本地绝对路径）或远程 URL
    """
    try:
        config = load_config()
        protocol = config.get("protocol", "openai")
        if protocol not in ("baidu_ocr", "tencent_ocr"):
            return "ocr_precise 工具需要配置传统 OCR Provider（百度或腾讯云）。请设置 MCP_OCR_PROVIDER=baidu_ocr 或 tencent_ocr。"

        image_data = _resolve_image(image)
        provider = _get_provider()
        result = await provider.analyze(image_data, "")
        return _format_result("精准 OCR 结果", result["text"], result["model"], result.get("usage"))
    except Exception as e:
        return f"精准 OCR 失败: {e}"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
