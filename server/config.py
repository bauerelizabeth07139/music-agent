"""Configuration & presets for the Music Agent demo.

Based on official MiMo platform (mimo.mi.com / platform.xiaomimimo.com):
  API (OpenAI format):       https://api.xiaomimimo.com
  API (Anthropic format):    https://api.xiaomimimo.com/anthropic
  Token Plan CN:             https://token-plan-cn.xiaomimimo.com
  Token Plan CN (Anthropic): https://token-plan-cn.xiaomimimo.com/anthropic
  Token Plan SG:             https://token-plan-sg.xiaomimimo.com
  Token Plan SG (Anthropic): https://token-plan-sg.xiaomimimo.com/anthropic

Models (verified from mimo.mi.com docs):
  mimo-v2.5-pro              - Reasoning flagship
  mimo-v2.5                  - Full-modal (omni)
  mimo-v2.5-pro-ultraspeed   - Fast reasoning
  mimo-v2-flash              - Lightweight
  mimo-v2.5-tts              - Text-to-Speech
  mimo-v2.5-tts-voiceclone   - Voice cloning
  mimo-v2.5-tts-voicedesign  - Voice design
"""

import os
from pathlib import Path
from pydantic import BaseModel
from typing import Optional

# Load .env from project root if present
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


PRESETS = [
    {
        "name": "MiMo 按量付费（API）",
        "base_url": "https://api.xiaomimimo.com",
        "provider_format": "openai",
        "model": "mimo-v2.5-pro",
        "tts_model": "mimo-v2.5-tts",
    },
    {
        "name": "MiMo Token Plan 国内集群",
        "base_url": "https://token-plan-cn.xiaomimimo.com",
        "provider_format": "openai",
        "model": "mimo-v2.5-pro",
        "tts_model": "mimo-v2.5-tts",
    },
    {
        "name": "MiMo Token Plan 新加坡集群",
        "base_url": "https://token-plan-sg.xiaomimimo.com",
        "provider_format": "openai",
        "model": "mimo-v2.5-pro",
        "tts_model": "mimo-v2.5-tts",
    },
    {
        "name": "MiMo API（Anthropic 兼容）",
        "base_url": "https://api.xiaomimimo.com/anthropic",
        "provider_format": "anthropic",
        "model": "mimo-v2.5-pro",
        "tts_model": "mimo-v2.5-tts",
    },
    {
        "name": "MiMo Token Plan 国内（Anthropic）",
        "base_url": "https://token-plan-cn.xiaomimimo.com/anthropic",
        "provider_format": "anthropic",
        "model": "mimo-v2.5-pro",
        "tts_model": "mimo-v2.5-tts",
    },
    {
        "name": "MiMo Token Plan 新加坡（Anthropic）",
        "base_url": "https://token-plan-sg.xiaomimimo.com/anthropic",
        "provider_format": "anthropic",
        "model": "mimo-v2.5-pro",
        "tts_model": "mimo-v2.5-tts",
    },
    {
        "name": "MiMo V2.5（全模态）",
        "base_url": "https://api.xiaomimimo.com",
        "provider_format": "openai",
        "model": "mimo-v2.5",
        "tts_model": "mimo-v2.5-tts",
    },
    {
        "name": "MiMo V2 Flash（轻量）",
        "base_url": "https://api.xiaomimimo.com",
        "provider_format": "openai",
        "model": "mimo-v2-flash",
        "tts_model": "mimo-v2.5-tts",
    },
    {
        "name": "MiMo V2.5 Pro Ultraspeed",
        "base_url": "https://api.xiaomimimo.com",
        "provider_format": "openai",
        "model": "mimo-v2.5-pro-ultraspeed",
        "tts_model": "mimo-v2.5-tts",
    },
]


class Config(BaseModel):
    base_url: str = os.environ.get("MIMO_BASE_URL", "https://api.xiaomimimo.com")
    api_key: str = os.environ.get("MIMO_API_KEY", "")
    provider_format: str = "openai"
    model: str = os.environ.get("MIMO_MODEL", "mimo-v2.5")
    tts_model: str = os.environ.get("MIMO_TTS_MODEL", "mimo-v2.5-tts")
    default_voice: str = "mimo_default"


class RuntimeConfig:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.config = Config()
        return cls._instance

    def update(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)
        return self.config.model_dump()


def get_config() -> Config:
    return RuntimeConfig().config


def set_config(**kwargs) -> dict:
    return RuntimeConfig().update(**kwargs)
