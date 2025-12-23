"""Основной пайплайн для двухэтапного OCR в формате OpenWebUI."""

import asyncio
import base64
import json
import os
import tempfile
from pathlib import Path
from typing import Generator, Iterator, List, Union

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from .config import (
    JSON_PRESENCE_PENALTY,
    JSON_REPETITION_PENALTY,
    JSON_TEMPERATURE,
    OCR_PRESENCE_PENALTY,
    OCR_REPETITION_PENALTY,
    OCR_TEMPERATURE,
    VLM_API_KEY,
    VLM_API_URL,
    VLM_MODEL_NAME,
)
from .file_processor import FileProcessor
from .markdown_postproc import fix_ocr_markdown, remove_parentheses_around_numbers
from .prompts import FRAGMENT_PROMPT, SYSTEM_PROMPT_JSON, SYSTEM_PROMPT_MD
from .schemas import parser


class Pipeline:
    """Пайплайн для двухэтапного OCR: Markdown → JSON."""

    class Valves(BaseModel):
        VLM_API_URL: str
        VLM_API_KEY: str
        VLM_MODEL_NAME: str

    def __init__(self):
        self.name = "OCR Pipeline"
        self.file_processor = FileProcessor()

        self.valves = self.Valves(
            **{
                "pipelines": ["*"],
                "VLM_API_URL": os.getenv("VLM_API_URL", VLM_API_URL),
                "VLM_API_KEY": os.getenv("VLM_API_KEY", VLM_API_KEY),
                "VLM_MODEL_NAME": os.getenv("VLM_MODEL_NAME", VLM_MODEL_NAME),
            }
        )

    async def on_startup(self):
        """Вызывается при запуске пайплайна."""
        pass

    async def on_shutdown(self):
        """Вызывается при остановке пайплайна."""
        pass

    def _decode_file_data(self, file_data_b64: str) -> bytes:
        """Декодирует base64 данные файла."""
        if "," in file_data_b64:
            header, data = file_data_b64.split(",", 1)
            return base64.b64decode(data)
        else:
            return base64.b64decode(file_data_b64)

    async def _invoke_vlm_ocr(self, b64_images: List[str]) -> str:
        """Асинхронно выполняет OCR через VLM и возвращает Markdown."""
        llm = ChatOpenAI(
            base_url=self.valves.VLM_API_URL,
            api_key=self.valves.VLM_API_KEY,
            model=self.valves.VLM_MODEL_NAME,
            temperature=OCR_TEMPERATURE,
            presence_penalty=OCR_PRESENCE_PENALTY,
            extra_body={"repetition_penalty": OCR_REPETITION_PENALTY},
        )

        all_md = []
        for b64 in b64_images:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT_MD),
                HumanMessage(
                    content=[
                        {"type": "text", "text": FRAGMENT_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                        },
                    ]
                ),
            ]
            resp = await llm.ainvoke(messages)
            cleaned = fix_ocr_markdown(resp.content.strip())
            all_md.append(cleaned)

        return "\n\n".join(md for md in all_md if md)

    async def _invoke_vlm_json(self, markdown_text: str) -> dict:
        """Асинхронно преобразует Markdown в JSON через VLM."""
        llm = ChatOpenAI(
            base_url=self.valves.VLM_API_URL,
            api_key=self.valves.VLM_API_KEY,
            model=self.valves.VLM_MODEL_NAME,
            temperature=JSON_TEMPERATURE,
            presence_penalty=JSON_PRESENCE_PENALTY,
            extra_body={"repetition_penalty": JSON_REPETITION_PENALTY},
        )

        cleaned_md = remove_parentheses_around_numbers(markdown_text)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT_JSON),
            HumanMessage(content=[{"type": "text", "text": cleaned_md}]),
        ]

        response = await llm.ainvoke(messages)

        try:
            parsed = parser.parse(response.content)
            result = parsed.model_dump(by_alias=True, exclude_none=False)
        except Exception as e:
            raise ValueError(
                f"Ошибка парсинга JSON ответа от VLM: {str(e)}. Ответ: {response.content[:500]}"
            )

        required_keys = [
            "balance_head_table",
            "balance_dates_table",
            "balance_main_table_dates",
            "balance_main_table",
            "report_main_table",
        ]
        tables_data = result.get("tables_data", {})
        message = {
            key: "OK" if key in tables_data else "Missing" for key in required_keys
        }
        enriched = {"message": message, "xlsx": None, **result}
        return enriched

    def _extract_images(
        self, file_bytes: bytes, file_type: str, filename: str = None
    ) -> List[str]:
        """Извлекает изображения из файла в зависимости от его типа."""
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

    def _extract_from_docx(self, file_bytes: bytes, filename: str = None) -> List[str]:
        """Извлекает изображения из DOCX файла."""
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

    async def _process_file(self, file_bytes: bytes, filename: str = None) -> dict:
        """Обрабатывает файл через двухэтапный OCR пайплайн."""
        # Определение типа файла и извлечение изображений
        file_type = self.file_processor.detect_file_type(file_bytes, filename)

        if file_type == "unknown":
            return {
                "error": "Неподдерживаемый тип файла. Поддерживаются: PDF, DOCX, изображения (JPG, PNG, GIF, BMP, TIFF, WEBP)"
            }

        # Извлечение изображений
        b64_images = self._extract_images(file_bytes, file_type, filename)

        if not b64_images:
            return {
                "error": "Не удалось извлечь изображения из файла. Убедитесь, что файл содержит изображения или сканы документов."
            }

        # OCR → Markdown
        markdown_result = await self._invoke_vlm_ocr(b64_images)

        if not markdown_result or not markdown_result.strip():
            return {
                "error": "OCR не вернул результатов. Возможно, изображения не содержат читаемого текста."
            }

        # Markdown → JSON
        final_json = await self._invoke_vlm_json(markdown_result)

        return final_json

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        """
        Основной метод пайплайна для обработки запросов от OpenWebUI.

        Args:
            user_message: Сообщение пользователя
            model_id: ID модели
            messages: Список сообщений
            body: Тело запроса с файлами

        Returns:
            Результат обработки в виде строки или генератора
        """
        try:
            # Извлекаем файлы из body
            files = body.get("files", [])
            if not files:
                return "Ошибка: файлы не найдены в запросе. Пожалуйста, загрузите файл для обработки."

            # Обрабатываем первый файл (можно расширить для множественных файлов)
            file_info = files[0]
            file_data_b64 = file_info.get("data")
            filename = file_info.get("name") or file_info.get("filename")

            if not file_data_b64:
                return "Ошибка: данные файла не найдены."

            # Декодируем файл
            try:
                file_bytes = self._decode_file_data(file_data_b64)
            except Exception as e:
                return f"Ошибка декодирования файла: {str(e)}"

            # Обрабатываем файл асинхронно
            # Используем asyncio для запуска асинхронной функции в синхронном контексте
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Если цикл уже запущен, создаем новый
                    import nest_asyncio

                    nest_asyncio.apply()
                    result = asyncio.run(self._process_file(file_bytes, filename))
                else:
                    result = loop.run_until_complete(
                        self._process_file(file_bytes, filename)
                    )
            except RuntimeError:
                # Если нет event loop, создаем новый
                result = asyncio.run(self._process_file(file_bytes, filename))

            # Возвращаем результат как JSON строку
            return json.dumps(result, ensure_ascii=False, indent=2)

        except ValueError as e:
            return f"Ошибка валидации: {str(e)}"
        except Exception as e:
            return f"Внутренняя ошибка обработки: {str(e)}"
