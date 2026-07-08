# Music Agent

<p align="center">
  <h1 align="center">Music Agent</h1>
  <p align="center">基于 <b>小米 MiMo</b> 的 AI 编曲工作站</p>
  <p align="center">用自然语言驱动作曲、编曲、配音与混音的一体化音乐创作工具。</p>
</p>

![Platform](https://img.shields.io/badge/platform-Windows%20|%20macOS%20|%20Linux-blue)
![Node](https://img.shields.io/badge/node.js-18+-339933)
![Python](https://img.shields.io/badge/python-3.8+-3776ab)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 项目简介

**Music Agent** 以 **小米 MiMo 系列模型** 为核心，面向音乐创作场景，提供 AI 编曲、文本转语音（TTS）、声音克隆与多轨混音能力。它将 MiMo 的生成能力与前端可视化编排体验结合，帮助创作者用一句话完成从创意到可播放 Demo 的流程。

---

## 核心特性

| 功能 | 说明 |
|------|------|
| 🎼 **自然语言编曲** | 用中文/英文描述音乐风格与结构，AI 自动生成多轨方案 |
| 🎙️ **TTS 语音合成** | 文本转语音，支持多种角色声线 |
| 🧬 **声音克隆** | 上传/拖拽音频样本，快速构建个性化语音合成 |
| 🎹 **10 种乐器 Skill** | 把编曲描述转换成可播放乐器音轨 |
| 🎛️ **混音与试听** | 分轨播放、音量控制、快速导出整体 Demo |
| 🌓 **暗色/亮色主题** | 支持日间/夜间模式切换 |

---

## MIMO API Key 测试结果

| 模型 | 状态 | 说明 |
|------|------|------|
| mimo-v2.5 | ✅ 可用 | 全模态模型，用于编曲生成 |
| mimo-v2.5-pro | ✅ 可用 | 推理旗舰模型 |
| mimo-v2.5-tts | ✅ 可用 | 文本转语音，用于歌声合成 |
| mimo-v2.5-asr | ✅ 可用 | 语音识别 |

API 端点：https://api.xiaomimimo.com/v1

---

## 快速开始

### 前置条件

- [Node.js 18+](https://nodejs.org)
- [Python 3.8+](https://python.org)

### 安装与启动

```bash
# 1. 安装前端依赖
npm install

# 2. 安装后端依赖
pip install -r requirements.txt

# 3. 启动后端
cd server
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload

# 4. 启动前端（新终端）
npm run dev
```

启动后访问：http://localhost:5173

### 一键启动（Windows）

```powershell
# 方式一：PowerShell 脚本
powershell -ExecutionPolicy Bypass -File start.ps1

# 方式二：批处理
launch.bat

# 方式三：Python 脚本
python launch.py
```

---

## 独立窗口模式

本项目支持独立窗口运行，适合演示或沉浸式创作：

- start.ps1 - PowerShell 启动脚本
- launch.bat - 批处理启动
- launch.py - Python 启动脚本
- launch_window.py - 独立窗口启动

---

## 配置说明

### 环境变量 (.env)

```env
MIMO_API_KEY=your-api-key-here
MIMO_BASE_URL=https://api.xiaomimimo.com
MIMO_MODEL=mimo-v2.5
MIMO_TTS_MODEL=mimo-v2.5-tts
```

也可以在应用侧边栏中配置：

- **API URL**：默认指向 MiMo 官方服务
- **API Key**：你的模型服务密钥
- **Model Name**：不同任务使用的模型名
- **Protocol**：OpenAI / Anthropic 风格兼容

---

## MiMo 预设配置

| 预设名称 | Base URL | 模型 |
|----------|----------|------|
| MiMo 按量付费（API） | https://api.xiaomimimo.com | mimo-v2.5-pro |
| MiMo Token Plan 国内集群 | https://token-plan-cn.xiaomimimo.com | mimo-v2.5-pro |
| MiMo Token Plan 新加坡集群 | https://token-plan-sg.xiaomimimo.com | mimo-v2.5-pro |
| MiMo V2.5（全模态） | https://api.xiaomimimo.com | mimo-v2.5 |
| MiMo V2.5 Pro Ultraspeed | https://api.xiaomimimo.com | mimo-v2.5-pro-ultraspeed |

---

## 目录结构

```text
.
├── server/               # 后端服务与 Skill 逻辑
│   ├── app.py            # FastAPI 主应用
│   ├── config.py         # 配置与预设
│   ├── llm_client.py     # LLM/TTS 客户端
│   └── skills/           # 后端技能
├── src/                  # 前端应用
├── skills/               # 音乐与乐器 Skill
│   ├── instruments/      # 10 种乐器技能
│   └── music-search/     # 音乐搜索
├── .env                  # 环境变量配置
├── start.ps1             # Windows 启动脚本
└── README.md
```

---

## 技术栈

- **前端**：React + Vite
- **后端**：Python + FastAPI
- **音频**：numpy + soundfile
- **模型服务**：小米 MiMo（默认）

---

## 致谢

本项目为基于小米 MiMo 的创意应用演示，重点展示 MiMo 在音乐创作 Agent 场景中的集成能力。

---

## License

MIT