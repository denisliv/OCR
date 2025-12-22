"""Основной пайплайн для двухэтапного OCR."""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .file_processor import FileProcessor
from .vlm_client import invoke_vlm_json, invoke_vlm_ocr


class OCRPipeline:
    """Пайплайн для двухэтапного OCR: Markdown → JSON."""

    def __init__(self):
        self.file_processor = FileProcessor()

    async def process(
        self,
        file_bytes: bytes,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Асинхронно обрабатывает файл через двухэтапный OCR пайплайн.

        Args:
            file_bytes: Байты файла
            filename: Имя файла (опционально)

        Returns:
            Словарь с результатом обработки или ошибкой
        """
        try:
            # Этап 1: Определение типа файла и извлечение изображений
            file_type = self.file_processor.detect_file_type(file_bytes, filename)

            if file_type == "unknown":
                return {
                    "error": "Неподдерживаемый тип файла. Поддерживаются: PDF, DOCX, изображения (JPG, PNG, GIF, BMP, TIFF, WEBP)"
                }

            # Этап 2: Извлечение изображений в зависимости от типа
            b64_images = self._extract_images(file_bytes, file_type, filename)

            if not b64_images:
                return {
                    "error": "Не удалось извлечь изображения из файла. Убедитесь, что файл содержит изображения или сканы документов."
                }

            # Этап 3: OCR → Markdown (асинхронно)
            markdown_result = await invoke_vlm_ocr(b64_images)

            if not markdown_result or not markdown_result.strip():
                return {
                    "error": "OCR не вернул результатов. Возможно, изображения не содержат читаемого текста."
                }

            # Этап 4: Markdown → JSON (асинхронно)
            final_json = await invoke_vlm_json(markdown_result)

            return final_json

        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Внутренняя ошибка обработки: {str(e)}"}

    def _extract_images(
        self,
        file_bytes: bytes,
        file_type: str,
        filename: Optional[str] = None,
    ) -> List[str]:
        """
        Извлекает изображения из файла в зависимости от его типа.

        Args:
            file_bytes: Байты файла
            file_type: Тип файла ('pdf', 'docx', 'image')
            filename: Имя файла (опционально)

        Returns:
            Список base64-строк изображений
        """
        if file_type == "pdf":
            return self._extract_from_pdf(file_bytes)
        elif file_type == "docx":
            return self._extract_from_docx(file_bytes, filename)
        elif file_type == "image":
            return self.file_processor.process_image(file_bytes)
        else:
            raise ValueError(f"Неподдерживаемый тип файла: {file_type}")

    def _extract_from_pdf(self, file_bytes: bytes) -> List[str]:
        """Извлекает изображения из PDF файла."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            return self.file_processor.extract_images_from_pdf(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _extract_from_docx(
        self, file_bytes: bytes, filename: Optional[str] = None
    ) -> List[str]:
        """Извлекает изображения из DOCX файла."""
        # Определяем расширение из имени файла или используем .docx по умолчанию
        if filename:
            suffix = Path(filename).suffix.lower()
            if suffix not in [".docx", ".doc"]:
                suffix = ".docx"
        else:
            suffix = ".docx"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            return self.file_processor.extract_images_from_docx(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
