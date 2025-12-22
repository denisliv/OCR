import base64
import json
import os
import tempfile
from typing import Any, Dict

from .pdf_handler import extract_and_tile_pdf
from .vlm_client import invoke_vlm_json, invoke_vlm_ocr


def pipe(
    body: Dict[str, Any],
    __user__: Dict[str, Any],
    __metadata__: Dict[str, Any],
    __llm__: Any,
) -> str:
    """
    Pipeline for Open WebUI: PDF → VLM → Structured JSON
    """

    try:
        files = body.get("files", [])
        if not files:
            return json.dumps({"error": "No PDF file provided"}, ensure_ascii=False)

        # Берём первый файл (ожидаем PDF)
        file_info = files[0]
        file_data_b64 = file_info.get("data")
        if not file_data_b64:
            return json.dumps({"error": "File data missing"}, ensure_ascii=False)

        # Декодируем и сохраняем во временный файл
        file_bytes = bytes(file_data_b64, "utf-8")
        if file_data_b64.startswith(""):
            # Если пришёл data URL — обрезаем заголовок
            file_bytes = base64.b64decode(file_data_b64.split(",", 1)[1])
        else:
            file_bytes = base64.b64decode(file_data_b64)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            # 1. Извлекаем тайлы
            b64_tiles = extract_and_tile_pdf(tmp_path)
            if not b64_tiles:
                return json.dumps(
                    {"error": "No images extracted from PDF"}, ensure_ascii=False
                )

            # 2. OCR → Markdown
            markdown_result = invoke_vlm_ocr(b64_tiles)
            if not markdown_result.strip():
                return json.dumps(
                    {"error": "OCR returned empty result"}, ensure_ascii=False
                )

            # 3. Markdown → JSON
            final_json = invoke_vlm_json(markdown_result)

            return json.dumps(final_json, ensure_ascii=False, indent=2)

        finally:
            os.unlink(tmp_path)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
