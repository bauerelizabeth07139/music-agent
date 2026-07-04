<p align="center">
  <h1 align="center">Music Agent</h1>
  <p align="center">基于 <b>小米 MiMo</b> 的 AI 编曲工作站</p>
  <p align="center">用自然语言驱动作曲、编曲、配音与混音的一体化音乐创作工具。</p>
</p>

## 🚀 项目简介

**Music Agent** 以 **小米 MiMo 系列模型** 为核心，面向音乐创作场景，提供 AI 编曲、文本转语音（TTS）、声音克隆与多轨混音能力。  
它将 **MiMo 的生成能力** 与 **前端可视化编排体验** 结合，帮助创作者用一句话完成从创意到可播放 Demo 的流程。

> 本项目强调：这是一个 **基于小米 MiMo** 的音乐 Agent 演示应用。

---

## 🎯 核心特性

- 🎼 **自然语言编曲**：用中文/英文描述音乐风格与结构，AI 自动生成多轨方案
- 🎙️ **TTS 语音合成**：文本转语音，支持不同角色声线
- 🧬 **声音克隆**：上传/拖拽音频样本，快速构建个性化语音合成
- 🎹 **10 种乐器 Skill**：把编曲描述转换成可播放乐器音轨
- 🎛️ **混音与试听**：分轨播放、音量控制、快速导出整体 Demo

---

## 🧠 为什么强调「基于小米 MiMo」

本项目默认对接 **小米 MiMo API**，并在架构设计中围绕 MiMo 的接口风格与调用模式进行适配：  
- API 预置中包含 MiMo 官方与兼容集群  
- 前端配置面板优先支持 MiMo 场景切换  
- 后端 LLM/TTS 能力通过 MiMo 为主入口串联  

这使得项目更适合用于展示 **MiMo 在创意生产链路上的应用潜力**。

---

## 🛠️ 技术栈

- **前端**：React + Vite
- **后端**：Python + FastAPI
- **音频**：numpy + soundfile
- **模型服务**：小米 MiMo（默认）
- **交互**：语音面板 + 编曲面板 + 混音总线

---

## 📦 快速开始

```bash
# 1) 安装前端依赖
npm install

# 2) 启动后端
cd server
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload

# 3) 启动前端（新终端）
npm run dev
```

启动后访问：

http://localhost:5173

---

## ⚙️ 配置说明

在应用侧边栏中可配置：

- `API URL`：默认指向 MiMo 官方服务
- `API Key`：你的模型服务密钥
- `Model Name`：不同任务使用的模型名
- `Protocol`：OpenAI / Anthropic 风格兼容

> 建议优先使用 MiMo 相关地址进行演示，以突出本项目定位。

---

## 📁 目录结构

```
.
├─ server/               # 后端服务与 Skill 逻辑
├─ src/                  # 前端应用
├─ skills/               # 音乐与乐器 Skill
├─ start.ps1             # Windows 启动脚本
└─ README.md
```

---

## 📣 致谢

本项目为 **基于小米 MiMo** 的创意应用演示，重点展示 MiMo 在音乐创作 Agent 场景中的集成能力。

---

## 📝 License

当前未显式声明许可证。如需开源协作，可补充 MIT 或其他许可证。
