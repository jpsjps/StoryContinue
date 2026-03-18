from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "data" / "config.json"


@dataclass
class APIConfig:
  provider: str = "openai"  # "openai" | "anthropic"
  api_base: Optional[str] = None
  api_key: str = ""
  model: str = "gpt-4.1"


def load_config() -> APIConfig:
  """
  优先从 data/config.json 读取配置；
  若不存在或字段缺失，则回退到环境变量。
  """
  cfg = APIConfig()

  if CONFIG_PATH.exists():
    try:
      with CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
      cfg.provider = data.get("provider", cfg.provider)
      cfg.api_base = data.get("api_base", cfg.api_base)
      cfg.api_key = data.get("api_key", cfg.api_key)
      cfg.model = data.get("model", cfg.model)
    except Exception:
      # 读取失败时退回环境变量，不抛异常阻断启动
      pass

  # 环境变量覆盖 JSON（方便临时调试）
  cfg.provider = os.getenv("LLM_PROVIDER", cfg.provider)
  cfg.api_base = os.getenv("OPENAI_BASE_URL", cfg.api_base)
  cfg.api_key = (
    os.getenv("OPENAI_API_KEY")
    or os.getenv("OPENAI_KEY")
    or os.getenv("ANTHROPIC_API_KEY")
    or cfg.api_key
  )
  cfg.model = os.getenv("OPENAI_MODEL", cfg.model)

  return cfg

