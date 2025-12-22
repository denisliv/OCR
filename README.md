```
openwebui-pipelines/
└── pdf_financial_parser/
    ├── __init__.py             # Точка входа для Open WebUI
    ├── pdf_handler.py          # Извлечение и подготовка изображений из PDF
    ├── image_enhancer.py       # Улучшение сканов
    ├── vlm_client.py           # Работа с VLM через OpenAI-совместимый API
    ├── markdown_postproc.py    # Постобработка OCR-результата
    ├── schemas.py              # Pydantic-модели и парсер
    └── config.py               # Конфигурация (URL, токен, модель и т.д.)
```