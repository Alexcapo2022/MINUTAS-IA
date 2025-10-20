import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "30"))

# View por defecto para /extract
DEFAULT_VIEW = os.getenv("DEFAULT_VIEW", "compact")  # compact | full
MASK_IDS = os.getenv("MASK_IDS", "true").lower() == "true"

if not OPENAI_API_KEY:
    raise RuntimeError("Falta OPENAI_API_KEY en .env")

UBIGEO_ONLINE_ENABLED = os.getenv("UBIGEO_ONLINE_ENABLED", "true").lower() == "true"
UBIGEO_ONLINE_URL = os.getenv("UBIGEO_ONLINE_URL", "https://free.e-api.net.pe/ubigeos.json")
UBIGEO_HTTP_TIMEOUT = float(os.getenv("UBIGEO_HTTP_TIMEOUT", "3.0"))
