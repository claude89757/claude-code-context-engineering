import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TRACES_DIR = DATA_DIR / "traces"
DB_PATH = DATA_DIR / "observatory.db"

ANTHROPIC_AUTH_TOKEN = os.getenv("ANTHROPIC_AUTH_TOKEN", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.lkeap.cloud.tencent.com/coding/anthropic")
LLM_MODEL = os.getenv("LLM_MODEL", "kimi-k2.5")
PATROL_INTERVAL_MINUTES = int(os.getenv("PATROL_INTERVAL_MINUTES", "30"))
