# MCP-VISION

为 Claude Code、Codex CLI、OpenCode 等 AI 编程工具补齐图像识别能力的 MCP Server。

## 解决什么问题

Claude Code 配合 DeepSeek 等**纯文本模型**使用时，无法理解图片内容——截图里的报错、UI 设计稿、手绘架构图、文档扫描件，模型统统"看不见"。

**mcp-vision** 作为 MCP Server 插件运行，自动调用多模态视觉 API 完成图像分析，将结果以文本形式返回给 AI 编程工具，让 DeepSeek 等"看图说话"。

```
┌─────────────┐     图片路径/URL      ┌─────────────┐    多模态 API     ┌──────────────┐
│  AI 编程工具  │ ──────────────────→  │ mcp-vision  │ ──────────────→  │  视觉模型 API  │
│ Claude Code  │                      │  MCP Server  │                  │ 硅基流动/阿里.. │
│  Codex CLI   │ ←──────────────────  │             │ ←──────────────  │              │
│   OpenCode   │     文字分析结果      │             │     图片分析结果   │              │
└─────────────┘                      └─────────────┘                  └──────────────┘
```

## 工具说明

| 工具 | 用途 | 底层 |
|------|------|------|
| `analyze_image` | 图片内容分析（描述、问答、图表解读） | 多模态 LLM |
| `ocr_extract` | 从图片/PDF 提取文字（自然语言返回） | 多模态 LLM |
| `ocr_precise` | 精准 OCR（结构化结果，含坐标和置信度） | 传统 OCR 引擎 |

所有工具的 `image` 参数均支持单个**本地文件路径**或**远程 URL**，也支持按顺序传入多个路径/URL 的列表。多模态 Provider 会在一次请求中联合处理多张图片；精准 OCR 会逐张调用传统 OCR 服务并按图片分段返回。

配置百度或腾讯传统 OCR Provider 时，多图输入请使用 `ocr_precise`。图片的数量、格式和总请求体大小仍需满足所选服务和模型的限制。

## 快速开始

### 安装

```bash
pip install mcp-vision
```

或使用 uv：

```bash
uv pip install mcp-vision
```

### 最简配置

只需一个 API Key 即可运行。推荐使用硅基流动（SiliconFlow），注册即送免费额度：

```bash
# 注册地址：https://cloud.siliconflow.cn
SILICONFLOW_API_KEY=sk-your-key
```

### 配置 AI 编程工具

#### Claude Code

`~/.claude/settings.json`：

```json
{
  "mcpServers": {
    "mcp-vision": {
      "command": "uvx",
      "args": ["mcp-vision"],
      "env": {
        "SILICONFLOW_API_KEY": "sk-your-key"
      }
    }
  }
}
```

#### Codex CLI

`~/.codex/config.toml`：

```toml
[mcp_servers.mcp-vision]
command = "uvx"
args = ["mcp-ocr"]

[mcp_servers.mcp-vision.env]
SILICONFLOW_API_KEY = "sk-your-key"
```

#### Cursor

`.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "mcp-vision": {
      "command": "uvx",
      "args": ["mcp-vision"],
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
    "mcp-vision": {
      "type": "local",
      "command": ["uvx", "mcp-vision"],
      "environment": {
        "SILICONFLOW_API_KEY": "sk-your-key"
      }
    }
  }
}
```

## 支持的 Provider

通过 `MCP_OCR_PROVIDER` 环境变量切换，默认 `siliconflow`。

### 多模态 LLM（图片分析 / OCR 提取）

| Provider | 值 | API Key 环境变量 | 默认模型 |
|----------|---|-----------------|---------|
| 硅基流动（默认） | `siliconflow` | `SILICONFLOW_API_KEY` | DeepSeek-OCR |
| 阿里百炼 | `dashscope` | `DASHSCOPE_API_KEY` | qwen-vl-max |
| 火山引擎 | `volcengine` | `VOLCENGINE_API_KEY` | doubao-1.5-vision-pro-32k |
| OpenAI | `openai` | `OPENAI_API_KEY` | gpt-4o |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` | claude-sonnet-4-6 |
| 自定义 API | `custom` | `MCP_OCR_API_KEY` | 需手动指定 |

硅基流动以外的 Provider 需额外设置对应的模型环境变量（如 `DASHSCOPE_MODEL`、`OPENAI_MODEL`）。

### 切换视觉模型

每个 Provider 都有内置默认模型，通过对应的 `*_MODEL` 环境变量可以覆盖：

| Provider | 模型环境变量 | 默认值 |
|----------|------------|-------|
| 硅基流动 | `SILICONFLOW_MODEL` | `deepseek-ai/DeepSeek-OCR` |
| 阿里百炼 | `DASHSCOPE_MODEL` | `qwen-vl-max` |
| 火山引擎 | `VOLCENGINE_MODEL` | `doubao-1.5-vision-pro-32k` |
| OpenAI | `OPENAI_MODEL` | `gpt-4o` |
| Anthropic | `ANTHROPIC_MODEL` | `claude-sonnet-4-6` |

以硅基流动为例，在 `.env` 或环境变量中指定：

```bash
MCP_OCR_PROVIDER=siliconflow
SILICONFLOW_API_KEY=sk-your-key
SILICONFLOW_MODEL=deepseek-ai/DeepSeek-OCR
```

在 AI 编程工具的 `env` 配置中直接指定：

```json
{
  "mcpServers": {
    "mcp-vision": {
      "command": "uvx",
      "args": ["mcp-vision"],
      "env": {
        "SILICONFLOW_API_KEY": "sk-your-key",
        "SILICONFLOW_MODEL": "Qwen/Qwen2.5-VL-72B-Instruct"
      }
    }
  }
}
```

> **提示**：请确保指定的模型是视觉模型（支持图片输入）。纯文本模型会导致 API 调用失败。

### 传统 OCR（精准提取，结构化结果）

| Provider | 值 | 环境变量 |
|----------|---|---------|
| 百度 OCR | `baidu_ocr` | `BAIDU_OCR_API_KEY` + `BAIDU_OCR_SECRET_KEY` |
| 腾讯云 OCR | `tencent_ocr` | `TENCENT_SECRET_ID` + `TENCENT_SECRET_KEY` |

传统 OCR 仅支持 `ocr_precise` 工具，返回结构化数据（含文字坐标和置信度）。

### 自定义 Provider

兼容所有 OpenAI `/chat/completions` 协议的视觉 API：

```bash
MCP_OCR_PROVIDER=custom
MCP_OCR_API_KEY=your-key
MCP_OCR_BASE_URL=https://your-api.com/v1
MCP_OCR_MODEL=your-vision-model
```

## 环境变量完整列表

```bash
# Provider 选择（默认 siliconflow）
MCP_OCR_PROVIDER=siliconflow

# === 硅基流动 ===
SILICONFLOW_API_KEY=your-key
# SILICONFLOW_MODEL=deepseek-ai/DeepSeek-OCR    # 可选，覆盖默认模型

# === 阿里百炼 ===
# DASHSCOPE_API_KEY=your-key
# DASHSCOPE_MODEL=qwen-vl-max

# === 火山引擎 ===
# VOLCENGINE_API_KEY=your-key
# VOLCENGINE_MODEL=doubao-1.5-vision-pro-32k

# === OpenAI ===
# OPENAI_API_KEY=sk-your-key
# OPENAI_MODEL=gpt-4o

# === Anthropic ===
# ANTHROPIC_API_KEY=sk-ant-your-key
# ANTHROPIC_MODEL=claude-sonnet-4-6

# === 百度 OCR ===
# BAIDU_OCR_API_KEY=your-api-key
# BAIDU_OCR_SECRET_KEY=your-secret-key

# === 腾讯云 OCR ===
# TENCENT_SECRET_ID=your-secret-id
# TENCENT_SECRET_KEY=your-secret-key

# === 自定义 OpenAI 兼容 API ===
# MCP_OCR_API_KEY=your-key
# MCP_OCR_BASE_URL=https://your-api.com/v1
# MCP_OCR_MODEL=your-model
```

也可将这些变量写在项目根目录的 `.env` 文件中，Server 启动时自动加载。

## 图片格式

PNG、JPG、JPEG、GIF、BMP、WebP、PDF

## 自动触发：粘贴图片即分析

在 Claude Code 中可以通过 Skill 实现粘贴图片后自动调用 mcp-vision，无需手动输入命令。

### 步骤一：创建 Skill 文件

在项目根目录创建 `.claude/skills/image-analysis.md`：

```markdown
---
name: image-analysis
description: 当用户粘贴图片时自动调用 mcp-vision 进行分析
trigger: 当用户消息中包含图片（[Image: ...] 或 [Image #N] 标记）时自动触发
---

当用户消息中包含图片标记时，自动调用 mcp-vision 的工具处理：

1. **如果用户没有文字说明**，默认调用 `analyze_image` 工具分析图片内容
2. **如果用户附带了文字说明**，将文字说明作为 prompt 传给对应工具

根据用户意图选择工具：
- 图片描述、问答、图表分析 → `analyze_image`
- 提取文字 → `ocr_extract`
- 需要坐标和置信度 → `ocr_precise`

将消息中所有图片标记对应的路径按出现顺序提取：单张传字符串，多张传数组，统一作为 `image` 参数传入。若客户端只提供剪切板中的最后一张图片，服务端无法恢复更早的图片内容。
```

### 步骤二：在 CLAUDE.md 中注册触发规则

在项目的 `CLAUDE.md`（或全局 `~/.claude/CLAUDE.md`）中添加：

```markdown
### 图片自动分析
- **触发条件**：当用户消息中包含 `[Image:`、`[Image #N]` 标记时（即通过 Alt+V 粘贴的图片）
- **执行动作**：立即调用 `image-analysis` skill，根据图片内容和用户意图自动选择分析模式
- **无需用户明确指示**：只要消息中有图片就应触发，无文字说明时自动智能路由
```

### 效果

配置完成后：

- **Alt+V 粘贴图片** → Claude Code 自动调用 mcp-vision 的 `analyze_image` → 返回图片分析结果
- **粘贴图片 + 文字说明**（如"提取这里的文字"） → 自动路由到 `ocr_extract`
- 无需手动输入任何命令

## 本地开发

```bash
# 克隆仓库
git clone https://github.com/hahahahanb/mcp-vision.git
cd mcp-vision

# 安装依赖
uv sync

# 运行测试
uv run pytest -v

# MCP Inspector 调试
uv run mcp dev src/mcp_ocr/server.py
```

本地安装后，AI 编程工具的配置可改为直接运行源码：

```json
{
  "mcpServers": {
    "mcp-vision": {
      "command": "uv",
      "args": ["run", "mcp-vision"],
      "env": {
        "SILICONFLOW_API_KEY": "sk-your-key"
      }
    }
  }
}
```

## License

MIT
