# Music Agent - AI 编曲工作站

基于小米 MiMo 系列模型的 AI 编曲与语音工作站。

## 功能

- **🎼 编曲模式**: 用自然语言描述音乐，AI 自动生成多轨编曲
- **🎙️ 语音合成 (TTS)**: 文本转语音，支持多种声音角色
- **🧬 声音克隆**: 上传/拖拽音频样本，克隆声音并合成新语音
- **🎹 10 种乐器 Skill**: 自动将编曲 JSON 转换为可播放的乐器音轨
- **🎛️ 混音总线**: 分轨试听、独立音量控制、Master 导出

## 快速启动

```powershell
# 一键启动
powershell -ExecutionPolicy Bypass -File start.ps1

# 或手动启动
# 1. 安装前端依赖
npm install

# 2. 启动后端
cd server
D:\1\jieshi10\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload

# 3. 启动前端 (另一个终端)
npm run dev
```

启动后访问 http://localhost:5173

## 配置

在左侧边栏配置:
- **API URL**: 默认为小米 MiMo 官方地址，可切换不同集群
- **API Key**: 你的 API 密钥
- **协议格式**: OpenAI 兼容 / Anthropic 兼容
- **模型名称**: 编曲/TTS/克隆模型分别配置

### 预设地址

| 名称 | URL | 格式 |
|------|-----|------|
| MiMo 官方默认 | `https://api.mimo.xiaomi.com/v1` | OpenAI |
| MiMo Token Plan 集群 A | `https://cluster-a.mimo.xiaomi.com/v1` | OpenAI |
| MiMo Token Plan 集群 B | `https://cluster-b.mimo.xiaomi.com/v1` | OpenAI |
| MiMo Anthropic 兼容 | `https://api.mimo.xiaomi.com/v1` | Anthropic |

## 技术栈

- **后端**: Python 3.10 + FastAPI + httpx
- **前端**: React 19 + Vite 8
- **音频合成**: numpy + soundfile (纯算法合成，无需采样库)
- **乐器 Skill**: 10 种内置合成引擎 (Piano, Guitar, Bass, Drums, Violin, Cello, Flute, Trumpet, Synth Pad, Synth Lead)

## 目录结构

```
music-agent-demo/
├── server/                # Python 后端
│   ├── app.py             # FastAPI 主应用
│   ├── config.py          # 配置管理与预设
│   ├── llm_client.py      # LLM/TTS/Clone 统一客户端
│   └── skills/
│       └── instruments.py # 乐器渲染 Skill 引擎
├── src/                   # React 前端
│   ├── App.jsx            # 主应用
│   └── components/
│       ├── ConfigPanel.jsx
│       ├── ArrangePanel.jsx
│       ├── VoicePanel.jsx
│       ├── TrackList.jsx
│       └── MasterPlayer.jsx
├── start.ps1              # 一键启动脚本
└── README.md
```
