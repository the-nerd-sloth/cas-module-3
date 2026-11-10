"""
config.py: centralised settings for the Cancer AI Agent (Local version - Ollama)
"""
import os

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
SQLITE_DB  = os.path.join(DATA_DIR, "cancer_data.db")
VECTOR_DIR = os.path.join(DATA_DIR, "vectorstore")

# Ollama
OLLAMA_BASE_URL = "http://localhost:11434"

# LLM model qwen3.5:9b is the best open tool-calling model for 8 GB VRAM.
LLM_MODEL   = "qwen3.5:9b"

# Embedding model
EMBED_MODEL = "nomic-embed-text"

# WHO GHO
WHO_GHO_API = "https://ghoapi.azureedge.net/api"

WHO_INDICATORS = {
    "SA_0000001807": "Cancer: age-standardised death rate, all cancers",
    "SA_0000001438": "Cancer: breast, age-standardised death rate",
    "SA_0000001439": "Cancer: cervical, age-standardised death rate",
    "SA_0000001445": "Cancer: colorectal, age-standardised death rate",
    "SA_0000001449": "Cancer: liver, age-standardised death rate",
    "SA_0000001448": "Cancer: lung, age-standardised death rate",
    "SA_0000001419": "Cancer: incidence rate, all cancers, female",
    "SA_0000001420": "Cancer: incidence rate, all cancers, male",
    "SA_0000001426": "Cancer: prostate, age-standardised death rate",
    "NCDMORT3070":   "NCD: probability of dying from cancer/CVD/diabetes age 30-70",
    "NCD_DTH_TOT":   "NCD: total deaths from cancer, CVD, diabetes, CRD",
}

# Wikipedia scraping targets
CANCER_TYPES_TO_SCRAPE = [
    "lung cancer", "breast cancer", "colorectal cancer", "prostate cancer",
    "stomach cancer", "liver cancer", "cervical cancer", "leukemia",
    "melanoma", "pancreatic cancer", "ovarian cancer", "bladder cancer",
    "thyroid cancer", "esophageal cancer", "kidney cancer",
]

# Agent settings
MAX_SEARCH_ITERATIONS = 10
CHUNK_SIZE            = 800
CHUNK_OVERLAP         = 100
