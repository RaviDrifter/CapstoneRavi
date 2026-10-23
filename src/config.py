from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data")).resolve()
DOCS_PATH = Path(os.getenv("DOCUMENTATION_PATH", DATA_DIR / "documentation.json")).resolve()
DEV_PATH = Path(os.getenv("DEVELOPMENT_TICKETS_PATH", DATA_DIR / "development_tickets.json")).resolve()
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", ROOT / "storage" / "chroma")).resolve()
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(ROOT / 'storage' / 'decisions.db').as_posix()}")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/llama-3.1-8b-instruct")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
RETRIEVAL_BACKEND = os.getenv("RETRIEVAL_BACKEND", "tfidf").lower()
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.10"))
ANSWERABILITY_THRESHOLD = float(os.getenv("ANSWERABILITY_THRESHOLD", "0.40"))
RETRIEVAL_MIN_SCORE = float(os.getenv("RETRIEVAL_MIN_SCORE", "0.025"))
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "12"))
USE_LLM = os.getenv("USE_LLM", "false").lower() in {"1", "true", "yes"}
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
