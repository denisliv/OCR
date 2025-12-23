import os
from typing import Final

VLM_API_URL: Final[str] = os.getenv("VLM_API_URL", "http://localhost:8000/v1")
VLM_API_KEY: Final[str] = os.getenv("VLM_API_KEY", "token-abc")
VLM_MODEL_NAME: Final[str] = os.getenv("VLM_MODEL_NAME", "qwen3vl-8b-instruct-fp8")

OCR_TEMPERATURE: Final[float] = 0.0
JSON_TEMPERATURE: Final[float] = 0.0

OCR_PRESENCE_PENALTY: Final[float] = 0.0
JSON_PRESENCE_PENALTY: Final[float] = 1.2

OCR_REPETITION_PENALTY: Final[float] = 1.0
JSON_REPETITION_PENALTY: Final[float] = 1.5

DPI: Final[int] = 150
MAX_TILE_SIZE: Final[int] = 4096
TILE_OVERLAP: Final[int] = 120
