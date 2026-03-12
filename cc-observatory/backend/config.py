import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TRACES_DIR = DATA_DIR / "traces"
DB_PATH = DATA_DIR / "observatory.db"

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.lkeap.cloud.tencent.com/coding/anthropic")
LLM_MODEL = os.getenv("LLM_MODEL", "kimi-k2.5")
PATROL_INTERVAL_MINUTES = int(os.getenv("PATROL_INTERVAL_MINUTES", "30"))
CLAUDE_CODE_AUTH_TOKEN = os.getenv("CLAUDE_CODE_AUTH_TOKEN", "")
