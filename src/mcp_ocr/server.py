import logging
import sys

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    stream=sys.stderr,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mcp-ocr")

from mcp.server.fastmcp import FastMCP

from mcp_ocr.config import load_config
from mcp_ocr.provider import OpenAICompatibleProvider, AnthropicProvider
from mcp_ocr.traditional_ocr import BaiduOCRProvider, TencentOCRProvider
from mcp_ocr.image_utils import (
    ImageInput,
    is_url,
    normalize_images,
    read_file_as_base64,
    read_url_as_base64,
    validate_image_path,
)

mcp = FastMCP(
    "mcp-ocr",
    instructions="图像识别服务。提供图片分析（analyze_image）、文字提取（ocr_extract）和精准 OCR（ocr_precise）工具。image 支持单个本地文件路径/远程 URL 或有序列表。支持硅基流动/阿里/火山/OpenAI/Anthropic/百度OCR/腾讯云OCR。",
)

_provider = None


def _get_provider():
    global _provider
    if _provider is None:
        config = load_config()
        protocol = config.get("protocol", "openai")
        api_key = config.get("api_key") or ""
        logger.info(f"初始化 Provider: {config.get('provider')} (protocol={protocol})")

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
        logger.info(f"Provider 就绪: {type(_provider).__name__}")
    return _provider


def _resolve_image(image: str) -> str:
    if is_url(image):
        return image
    validate_image_path(image)
    return read_file_as_base64(image)


def _resolve_images(image: ImageInput) -> list[str]:
    return [_resolve_image(item) for item in normalize_images(image)]


async def _resolve_precise_images(images: list[str]) -> list[str]:
    resolved = []
    for image in images:
        resolved.append(await read_url_as_base64(image) if is_url(image) else image)
    return resolved


async def _analyze_images(provider, images: list[str], prompt: str) -> dict:
    if len(images) > 1 and isinstance(provider, (BaiduOCRProvider, TencentOCRProvider)):
        raise ValueError("传统 OCR Provider 的多图输入请使用 ocr_precise 工具")
    return await provider.analyze(images[0] if len(images) == 1 else images, prompt)


def _format_result(title: str, text: str, model: str, usage: dict | None) -> str:
    lines = [f"## {title}", "", text, "", "---", f"模型: {model}"]
    if usage:
        lines.append(f"Token 用量: 输入 {usage.get('prompt_tokens', '?')} / 输出 {usage.get('completion_tokens', '?')} / 总计 {usage.get('total_tokens', '?')}")
    return "\n".join(lines)


@mcp.tool()
async def analyze_image(image: ImageInput, prompt: str | None = None) -> str:
    """分析一张或多张图片。支持本地文件路径、远程 URL 或其有序列表。

    Args:
        image: 单张图片路径/URL，或按顺序排列的图片路径/URL 列表
        prompt: 分析提示词。默认逐张描述；多图时也会概括图片间的关联
    """
    try:
        image_data = _resolve_images(image)
        provider = _get_provider()
        logger.info(f"analyze_image: image_count={len(image_data)}, prompt={prompt}")
        default_prompt = (
            "请逐张详细描述这些图片的内容，并指出图片之间的关联（如有）。"
            if len(image_data) > 1 else "请详细描述这张图片的内容"
        )
        result = await _analyze_images(provider, image_data, prompt or default_prompt)
        logger.info(f"analyze_image 完成: model={result['model']}, text_len={len(result['text'])}")
        return _format_result("图像分析结果", result["text"], result["model"], result.get("usage"))
    except Exception as e:
        logger.error(f"analyze_image 失败: {e}", exc_info=True)
        return f"图像分析失败: {e}"


@mcp.tool()
async def ocr_extract(image: ImageInput, prompt: str | None = None) -> str:
    """从一张或多张图片/PDF 中提取文字（OCR）。

    Args:
        image: 单张图片路径/URL，或按顺序排列的图片路径/URL 列表
        prompt: OCR 提示词。默认按图片顺序逐张提取并分段整理文字
    """
    try:
        image_data = _resolve_images(image)
        provider = _get_provider()
        ocr_prompt = prompt or (
            "请按输入顺序逐张提取所有图片中的文字并分别分段，保持原始排版格式。如果有代码，请用代码块包裹。"
            if len(image_data) > 1 else "请完整提取图片中的所有文字内容，保持原始排版格式。如果有代码，请用代码块包裹。"
        )
        logger.info(f"ocr_extract: image_count={len(image_data)}")
        result = await _analyze_images(provider, image_data, ocr_prompt)
        logger.info(f"ocr_extract 完成: text_len={len(result['text'])}")
        return _format_result("OCR 提取结果", result["text"], result["model"], result.get("usage"))
    except Exception as e:
        logger.error(f"ocr_extract 失败: {e}", exc_info=True)
        return f"OCR 提取失败: {e}"


@mcp.tool()
async def ocr_precise(image: ImageInput) -> str:
    """使用传统 OCR 引擎精准提取一张或多张图片中的文字。
    需要配置百度 OCR 或腾讯云 OCR 作为 Provider。
    适合需要精确文字位置信息的场景（如发票、卡证、表格）。

    Args:
        image: 单张图片路径/URL，或按顺序排列的图片路径/URL 列表
    """
    try:
        config = load_config()
        protocol = config.get("protocol", "openai")
        if protocol not in ("baidu_ocr", "tencent_ocr"):
            return "ocr_precise 工具需要配置传统 OCR Provider（百度或腾讯云）。请设置 MCP_OCR_PROVIDER=baidu_ocr 或 tencent_ocr。"

        image_data = await _resolve_precise_images(_resolve_images(image))
        provider = _get_provider()
        logger.info(f"ocr_precise: image_count={len(image_data)}")

        results = []
        for image_item in image_data:
            results.append(await provider.analyze(image_item, ""))

        if len(results) == 1:
            result = results[0]
            logger.info(f"ocr_precise 完成: text_len={len(result['text'])}")
            return _format_result("精准 OCR 结果", result["text"], result["model"], result.get("usage"))

        sections = []
        for index, result in enumerate(results, start=1):
            section = f"### 图片 {index}\n\n{result['text']}"
            usage = result.get("usage") or {}
            if usage:
                stats = " / ".join(f"{key}: {value}" for key, value in usage.items())
                section += f"\n\n识别统计: {stats}"
            sections.append(section)

        combined_text = "\n\n".join(sections)
        logger.info(f"ocr_precise 完成: image_count={len(results)}, text_len={len(combined_text)}")
        return _format_result("精准 OCR 结果", combined_text, results[0]["model"], None)
    except Exception as e:
        logger.error(f"ocr_precise 失败: {e}", exc_info=True)
        return f"精准 OCR 失败: {e}"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
