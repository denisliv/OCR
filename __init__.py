"""Пайплайн OCR для OpenWebUI.

Поддерживает обработку PDF, Word документов с изображениями и прямых изображений.
Выполняет двухэтапный OCR: сначала Markdown, затем JSON.
"""

from .pipeline import Pipeline

__all__ = ["Pipeline"]
