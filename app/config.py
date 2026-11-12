"""All settings in one place. Values that may change are read from the .env file."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Project root folder (the folder that contains "app" and "data")
ROOT = Path(__file__).resolve().parent.parent

# Read the .env file into environment variables
load_dotenv(ROOT / ".env")

# Folders
GUIDELINES_DIR = ROOT / "data" / "guidelines"   # put the ICMR PDFs here
INDEX_DIR = ROOT / "data" / "index"             # saved index files go here

# Chunking and search
CHUNK_SIZE = 500      # words per chunk
CHUNK_OVERLAP = 50    # words shared between neighbouring chunks
TOP_K = 4             # how many chunks we return for each question

# Local embedding model (free, runs on CPU)
EMBED_MODEL = "all-MiniLM-L6-v2"

# AI model settings (from .env)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")

# Minimum score needed before we even ask the AI
VECTOR_MIN_SCORE = float(os.getenv("VECTOR_MIN_SCORE", "0.30"))
KEYWORD_MIN_SCORE = float(os.getenv("KEYWORD_MIN_SCORE", "4.0"))
