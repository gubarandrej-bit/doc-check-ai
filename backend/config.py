"""Конфигурация приложения.

Все параметры читаются из переменных окружения или .env.
Никаких секретов не встроено в код — дефолты требуют замены при развёртывании.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# --- Режим работы: local | cloud | hybrid
MODE = os.environ.get("MODE", "local")

# --- Security
SECRET_KEY = os.environ.get("SECRET_KEY", "CHANGE-ME-please-generate-a-random-string")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

# --- Database
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'data' / 'doccheck.db'}",
)

# --- File storage
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", BASE_DIR / "data" / "uploads"))
REPORT_DIR = Path(os.environ.get("REPORT_DIR", BASE_DIR / "data" / "reports"))
for _d in (UPLOAD_DIR, REPORT_DIR, BASE_DIR / "data"):
    _d.mkdir(parents=True, exist_ok=True)

# --- CORS / frontend
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

# --- AI / neural layer configuration (pluggable) ---
AI_DEFAULT_PROVIDER = os.environ.get("AI_DEFAULT_PROVIDER", "openrouter")
AI_DEFAULT_MODEL = os.environ.get("AI_DEFAULT_MODEL", "openrouter/free")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Локальные модели (Ollama) — используются в режиме local
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_DEFAULT_MODEL = os.environ.get("OLLAMA_DEFAULT_MODEL", "llama3.1:8b")

# Максимальный размер загружаемого файла, байт
MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", "200")) * 1024 * 1024

# Поддерживаемые форматы входных данных
ALLOWED_EXTENSIONS = {"xls", "xlsx", "doc", "docx", "pdf", "dwg", "zip"}