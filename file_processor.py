"""Модуль для обработки различных типов файлов (PDF, Word, изображения)."""

import base64
from io import BytesIO
from pathlib import Path
from typing import List, Optional

import fitz
from docx import Document
from PIL import Image

from .config import DPI, MAX_TILE_SIZE, TILE_OVERLAP
from .image_enhancer import enhance_scan_for_ocr


class FileProcessor:
    """Обработчик файлов различных форматов для извлечения изображений."""

    @staticmethod
    def detect_file_type(file_bytes: bytes, filename: Optional[str] = None) -> str:
        """
        Определяет тип файла по содержимому и имени.

        Args:
            file_bytes: Байты файла
            filename: Имя файла (опционально)

        Returns:
            Тип файла: 'pdf', 'docx', 'image' или 'unknown'
        """
        if len(file_bytes) < 4:
            return "unknown"

        # Проверка по магическим байтам (более надежно)
        # PDF
        if file_bytes.startswith(b"%PDF"):
            return "pdf"

        # Изображения (проверяем перед DOCX, так как DOCX тоже начинается с PK)
        # JPEG: FF D8 FF
        if file_bytes.startswith(b"\xff\xd8\xff"):
            return "image"
        # PNG: 89 50 4E 47
        if file_bytes.startswith(b"\x89PNG"):
            return "image"
        # GIF: GIF87a или GIF89a
        if file_bytes.startswith((b"GIF87a", b"GIF89a")):
            return "image"
        # BMP: BM
        if file_bytes.startswith(b"BM"):
            return "image"
        # TIFF: II (little-endian) или MM (big-endian)
        if file_bytes.startswith((b"II\x2a\x00", b"MM\x00\x2a")):
            return "image"
        # WEBP: RIFF...WEBP
        if file_bytes.startswith(b"RIFF") and len(file_bytes) >= 12:
            if file_bytes[8:12] == b"WEBP":
                return "image"

        # DOCX/XLSX/PPTX - это ZIP архивы, начинаются с PK
        # Проверяем наличие [Content_Types].xml в ZIP структуре для более точного определения
        if file_bytes.startswith(b"PK"):
            # Если есть расширение .docx, считаем DOCX
            if filename:
                ext = Path(filename).suffix.lower()
                if ext in [".docx", ".doc"]:
                    return "docx"
            # Иначе пытаемся определить по содержимому ZIP
            # DOCX должен содержать word/ в структуре
            try:
                # Простая проверка: ищем признаки DOCX в первых 1024 байтах
                if (
                    b"word/" in file_bytes[:1024]
                    or b"[Content_Types].xml" in file_bytes[:2048]
                ):
                    return "docx"
            except Exception:
                pass

        # Проверка по расширению файла (fallback)
        if filename:
            ext = Path(filename).suffix.lower()
            if ext == ".pdf":
                return "pdf"
            elif ext in [".docx", ".doc"]:
                return "docx"
            elif ext in [
                ".jpg",
                ".jpeg",
                ".png",
                ".gif",
                ".bmp",
                ".tiff",
                ".tif",
                ".webp",
            ]:
                return "image"

        return "unknown"

    @staticmethod
    def extract_images_from_pdf(pdf_path: str) -> List[str]:
        """
        Извлекает и тайлит изображения из PDF.

        Args:
            pdf_path: Путь к PDF файлу

        Returns:
            Список base64-строк изображений
        """
        b64_tiles = []
        matrix = fitz.Matrix(DPI / 72.0, DPI / 72.0)

        with fitz.open(pdf_path) as doc:
            for page in doc:
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                mode = "RGB" if pix.n == 3 else "L" if pix.n == 1 else "RGB"
                img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
                if mode != "RGB":
                    img = img.convert("RGB")

                img = enhance_scan_for_ocr(img)
                tiles = FileProcessor._tile_image(img)

                for tile in tiles:
                    b64 = FileProcessor._image_to_base64(tile)
                    b64_tiles.append(b64)

        return b64_tiles

    @staticmethod
    def extract_images_from_docx(docx_path: str) -> List[str]:
        """
        Извлекает изображения из Word документа.

        Args:
            docx_path: Путь к DOCX файлу

        Returns:
            Список base64-строк изображений
        """
        b64_images = []

        try:
            doc = Document(docx_path)

            # Извлекаем изображения из всех частей документа
            # DOCX хранит изображения в relationships документа
            image_parts = []

            # Проверяем основные relationships
            for rel in doc.part.rels.values():
                if "image" in rel.target_ref or rel.target_ref.endswith(
                    (".png", ".jpg", ".jpeg", ".gif", ".bmp")
                ):
                    try:
                        image_part = rel.target_part
                        if hasattr(image_part, "blob"):
                            image_parts.append(image_part.blob)
                    except Exception:
                        continue

            # Также проверяем изображения в параграфах (inline shapes)
            for paragraph in doc.paragraphs:
                for run in paragraph.runs:
                    if hasattr(run, "_element"):
                        # Ищем изображения в run элементах
                        for drawing in run._element.xpath(".//a:blip"):
                            rId = drawing.get(
                                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
                            )
                            if rId:
                                try:
                                    image_part = doc.part.related_parts[rId]
                                    if hasattr(image_part, "blob"):
                                        image_parts.append(image_part.blob)
                                except Exception:
                                    continue

            # Обрабатываем найденные изображения
            for image_bytes in image_parts:
                try:
                    # Конвертируем в PIL Image
                    img = Image.open(BytesIO(image_bytes))
                    if img.mode != "RGB":
                        img = img.convert("RGB")

                    # Улучшаем для OCR
                    img = enhance_scan_for_ocr(img)

                    # Тайлим если нужно
                    tiles = FileProcessor._tile_image(img)
                    for tile in tiles:
                        b64 = FileProcessor._image_to_base64(tile)
                        b64_images.append(b64)
                except Exception:
                    # Пропускаем невалидные изображения
                    continue

        except Exception as e:
            raise ValueError(f"Ошибка при извлечении изображений из DOCX: {e}")

        if not b64_images:
            raise ValueError("В DOCX документе не найдено изображений")

        return b64_images

    @staticmethod
    def process_image(image_bytes: bytes) -> List[str]:
        """
        Обрабатывает изображение: улучшает и тайлит при необходимости.

        Args:
            image_bytes: Байты изображения

        Returns:
            Список base64-строк изображений
        """
        try:
            img = Image.open(BytesIO(image_bytes))
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Улучшаем для OCR
            img = enhance_scan_for_ocr(img)

            # Тайлим если нужно
            tiles = FileProcessor._tile_image(img)

            b64_images = []
            for tile in tiles:
                b64 = FileProcessor._image_to_base64(tile)
                b64_images.append(b64)

            return b64_images
        except Exception as e:
            raise ValueError(f"Ошибка при обработке изображения: {e}")

    @staticmethod
    def _tile_image(img: Image.Image) -> List[Image.Image]:
        """
        Разбивает изображение на тайлы если оно слишком большое.

        Args:
            img: PIL Image объект

        Returns:
            Список тайлов (может быть один элемент если изображение маленькое)
        """
        width, height = img.size

        if width <= MAX_TILE_SIZE and height <= MAX_TILE_SIZE:
            return [img]

        tiles = []
        if height > width:
            # Вертикальное разбиение
            y = 0
            while y < height:
                y2 = min(y + MAX_TILE_SIZE, height)
                tile = img.crop((0, y, width, y2))
                tiles.append(tile)
                if y2 == height:
                    break
                y = y2 - TILE_OVERLAP
        else:
            # Горизонтальное разбиение
            x = 0
            while x < width:
                x2 = min(x + MAX_TILE_SIZE, width)
                tile = img.crop((x, 0, x2, height))
                tiles.append(tile)
                if x2 == width:
                    break
                x = x2 - TILE_OVERLAP

        return tiles

    @staticmethod
    def _image_to_base64(img: Image.Image) -> str:
        """
        Конвертирует PIL Image в base64 строку.

        Args:
            img: PIL Image объект

        Returns:
            Base64 строка изображения
        """
        buf = BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
