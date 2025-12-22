"""Пайплайн OCR для OpenWebUI.

Поддерживает обработку PDF, Word документов с изображениями и прямых изображений.
Выполняет двухэтапный OCR: сначала Markdown, затем JSON.
"""

import base64
from typing import Any, Dict, Optional

from .pipeline import OCRPipeline
from .validators import validate_file_info


class Pipeline:
    """
    Пайплайн для обработки файлов через двухэтапный OCR.

    Соответствует стандарту OpenWebUI для пайплайнов.
    """

    def __init__(self):
        """Инициализирует пайплайн."""
        self.ocr_pipeline = OCRPipeline()

    async def on_file(self, file: Dict[str, Any]) -> Dict[str, Any]:
        """
        Асинхронно обрабатывает файл через двухэтапный OCR пайплайн.

        Метод вызывается OpenWebUI для каждого загруженного файла.

        Args:
            file: Словарь с информацией о файле, содержащий:
                - "data": base64 строка или data URL с данными файла
                - "name" или "filename": имя файла (опционально)
                - другие метаданные файла

        Returns:
            Словарь с результатом обработки:
                - При успехе: структурированный JSON с извлеченными данными
                - При ошибке: {"error": "описание ошибки"}
        """
        try:
            # Валидация информации о файле
            is_valid, error_msg = validate_file_info(file)
            if not is_valid:
                return {"error": error_msg}

            # Получаем данные файла
            file_data_b64 = file.get("data")
            filename = file.get("name") or file.get("filename")

            # Декодируем base64 данные
            file_bytes = self._decode_file_data(file_data_b64)

            if file_bytes is None:
                return {"error": "Не удалось декодировать данные файла"}

            # Обрабатываем файл через пайплайн (асинхронно)
            result = await self.ocr_pipeline.process(file_bytes, filename)

            return result

        except Exception as e:
            return {"error": f"Ошибка обработки: {str(e)}"}

    @staticmethod
    def _decode_file_data(file_data_b64: str) -> Optional[bytes]:
        """
        Декодирует base64 данные файла.

        Поддерживает как чистый base64, так и data URL формат.

        Args:
            file_data_b64: Base64 строка или data URL

        Returns:
            Декодированные байты или None при ошибке
        """
        try:
            # Проверяем, является ли это data URL
            if "," in file_data_b64:
                # Формат: data:image/png;base64,<base64_data>
                header, data = file_data_b64.split(",", 1)
                return base64.b64decode(data)
            else:
                # Чистый base64
                return base64.b64decode(file_data_b64)
        except Exception:
            return None
