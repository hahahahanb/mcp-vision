# MCP-OCR

为 Claude Code + DeepSeek 等纯文本模型补齐图像识别能力的 MCP Server。

通过调用硅基流动、阿里百炼、火山引擎、OpenAI、Anthropic 等多模态 API，以及百度/腾讯云等传统 OCR API，实现图片分析、OCR 文字提取。

## 安装

### 方式一：uvx 直接运行（推荐）

```bash
# 从 PyPI 安装并运行，无需 clone 仓库
uvx mcp-ocr
```

### 方式二：本地开发安装

```bash
cd D:\project\mcp-ocr
uv pip install -e .
```

安装后可通过 `python -m mcp_ocr.server` 启动。代码修改实时生效，无需重新安装。

## 配置

### 1. 设置环境变量

复制 `.env.example` 为 `.env`，填入你的 API Key：

```bash
# 最简配置：只需硅基流动一个 Key
SILICONFLOW_API_KEY=sk-your-siliconflow-key
```

### 2. 配置 AI 编程工具

#### Claude Code

`~/.claude/settings.json` 或项目 `.claude/settings.json`：

```json
{
  "mcpServers": {
    "mcp-ocr": {
      "command": "uvx",
      "args": ["mcp-ocr"],
      "env": {
        "SILICONFLOW_API_KEY": "sk-your-key"
      }
    }
  }
}
```

本地开发安装后也可使用：

```json
{
  "mcpServers": {
    "mcp-ocr": {
      "command": "python",
      "args": ["-m", "mcp_ocr.server"],
      "env": {
        "SILICONFLOW_API_KEY": "sk-your-key"
      }
    }
  }
}
```

#### OpenCode

`opencode.json`：

```json
{
  "mcp": {
    "mcp-ocr": {
      "type": "local",
      "command": ["uvx", "mcp-ocr"],
      "environment": {
        "SILICONFLOW_API_KEY": "sk-your-key"
      }
    }
  }
}
```

#### Codex CLI

`~/.codex/config.toml`：

```toml
[mcp_servers.mcp-ocr]
command = "uvx"
args = ["mcp-ocr"]

[mcp_servers.mcp-ocr.env]
SILICONFLOW_API_KEY = "sk-your-key"
```

#### Cursor

`.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "mcp-ocr": {
      "command": "uvx",
      "args": ["mcp-ocr"],
      "env": {
        "SILICONFLOW_API_KEY": "sk-your-key"
      }
    }
  }
}
```

## 工具说明

### analyze_image
分析图片内容（描述、问答、图表分析等）。使用 LLM 多模态模型。

### ocr_extract
从图片或 PDF 中提取文字（LLM 模式，自然语言返回）。使用 LLM 多模态模型。

### ocr_precise
精准提取图片中的文字（传统 OCR，结构化返回）。需配置百度或腾讯云 OCR。

## 支持的 Provider

设置 `MCP_OCR_PROVIDER` 环境变量切换：

| Provider | 值 | 协议族 | 环境变量 | 默认模型 |
|----------|---|--------|---------|---------|
| 硅基流动（默认） | `siliconflow` | OpenAI 兼容 | `SILICONFLOW_API_KEY` | Qwen2.5-VL-72B |
| 阿里百炼 | `dashscope` | OpenAI 兼容 | `DASHSCOPE_API_KEY` | qwen-vl-max |
| 火山引擎 | `volcengine` | OpenAI 兼容 | `VOLCENGINE_API_KEY` | doubao-1.5-vision-pro |
| OpenAI | `openai` | OpenAI 兼容 | `OPENAI_API_KEY` | gpt-4o |
| Anthropic | `anthropic` | Messages | `ANTHROPIC_API_KEY` | claude-sonnet-4-6 |
| 百度 OCR | `baidu_ocr` | 传统 OCR | `BAIDU_OCR_API_KEY` + `BAIDU_OCR_SECRET_KEY` | — |
| 腾讯云 OCR | `tencent_ocr` | 传统 OCR | `TENCENT_SECRET_ID` + `TENCENT_SECRET_KEY` | — |
| 自定义 | `custom` | OpenAI 兼容 | `MCP_OCR_API_KEY` | `MCP_OCR_MODEL` |

## 图片格式

PNG, JPG, JPEG, GIF, BMP, WebP, PDF

## 开发

```bash
# 运行测试
uv run pytest -v

# MCP Inspector 调试
uv run mcp dev src/mcp_ocr/server.py
```
