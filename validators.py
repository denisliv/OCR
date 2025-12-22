"""Модуль для валидации входных данных."""

from typing import Any, Dict, List, Optional, Tuple


def validate_request_body(body: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Валидирует тело запроса от OpenWebUI.

    Args:
        body: Тело запроса

    Returns:
        Кортеж (валидно ли, сообщение об ошибке если невалидно)
    """
    if not isinstance(body, dict):
        return False, "Тело запроса должно быть словарем"

    if "files" not in body:
        return False, "Отсутствует поле 'files' в запросе"

    files = body.get("files", [])
    if not isinstance(files, list):
        return False, "Поле 'files' должно быть списком"

    if len(files) == 0:
        return False, "Список файлов пуст"

    return True, None


def validate_file_info(file_info: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Валидирует информацию о файле.

    Args:
        file_info: Информация о файле

    Returns:
        Кортеж (валидно ли, сообщение об ошибке если невалидно)
    """
    if not isinstance(file_info, dict):
        return False, "Информация о файле должна быть словарем"

    if "data" not in file_info:
        return False, "Отсутствует поле 'data' в информации о файле"

    file_data = file_info.get("data")
    if not isinstance(file_data, str):
        return False, "Поле 'data' должно быть строкой"

    if not file_data.strip():
        return False, "Поле 'data' не может быть пустым"

    return True, None


def get_supported_formats() -> List[str]:
    """
    Возвращает список поддерживаемых форматов файлов.

    Returns:
        Список расширений файлов
    """
    return [
        ".pdf",
        ".docx",
        ".doc",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".tiff",
        ".tif",
        ".webp",
    ]
