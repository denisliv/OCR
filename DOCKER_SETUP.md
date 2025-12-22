# Инструкция по установке и запуску с Docker

## Быстрый старт

### 1. Подготовка

Убедитесь, что у вас есть:
- Docker и Docker Compose установлены
- VLM API доступен (локально или в Docker сети)
- Код пайплайна находится в директории `OCR/`

### 2. Настройка переменных окружения (опционально)

Создайте файл `.env` в корне проекта:

```bash
VLM_API_URL=http://host.docker.internal:8000/v1
VLM_API_KEY=token-abc
VLM_MODEL_NAME=qwen3vl-8b-instruct-fp8
```

Если VLM API запущен в Docker сети, используйте имя сервиса:
```bash
VLM_API_URL=http://vlm-api:8000/v1
```

### 3. Сборка и запуск

```bash
# Сборка контейнера пайплайна
docker-compose build ocr-pipeline

# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f
```

### 4. Проверка работы

```bash
# Проверьте статус контейнеров
docker-compose ps

# Проверьте логи пайплайна
docker-compose logs ocr-pipeline

# Проверьте установку зависимостей
docker exec -it ocr-pipeline python -c "import fitz; import docx; import PIL; import cv2; print('All dependencies OK')"

# Проверьте, что пайплайн виден в OpenWebUI
docker exec -it open-webui ls -la /app/pipelines/OCR
```

### 5. Использование

1. Откройте OpenWebUI: http://localhost:3000
2. Загрузите файл (PDF/DOCX/изображение)
3. Пайплайн автоматически обработает файл и вернет JSON результат

## Структура контейнеров

```
┌─────────────────────────┐
│  ocr-pipeline            │
│  - Устанавливает         │
│    зависимости в /deps   │
│  - Предоставляет через   │
│    named volume          │
└─────────────────────────┘
         │
         │ Named Volume
         ▼
┌─────────────────────────┐
│  ocr-pipeline-deps      │
│  (зависимости)          │
└─────────────────────────┘
         │
         │ + Bind Mount (код с хоста)
         ▼
┌─────────────────────────┐
│  open-webui             │
│  - Код: ./OCR ->        │
│    /app/pipelines/OCR   │
│  - Зависимости: volume ->│
│    /app/pipelines-deps   │
└─────────────────────────┘
```

**Как это работает:**
1. Контейнер `ocr-pipeline` устанавливает зависимости в `/deps` при сборке образа
2. При первом запуске Docker автоматически копирует данные из образа в named volume `ocr-pipeline-deps`
3. Код пайплайна монтируется напрямую с хоста (`./OCR`) в OpenWebUI
4. Зависимости монтируются из volume в OpenWebUI

## Обновление пайплайна

После изменения кода:

```bash
# Пересоберите контейнер
docker-compose build ocr-pipeline

# Перезапустите
docker-compose restart ocr-pipeline open-webui
```

## Остановка

```bash
# Остановка контейнеров
docker-compose down

# Остановка с удалением volumes (удалит все данные!)
docker-compose down -v
```

## Решение проблем

### Пайплайн не загружается

1. Проверьте логи: `docker-compose logs open-webui | grep -i pipeline`
2. Убедитесь, что `ENABLE_PIPELINES=true` установлена
3. Проверьте монтирование: `docker exec -it open-webui ls -la /app/pipelines/OCR`

### Ошибки импорта зависимостей

1. Проверьте установку: `docker exec -it ocr-pipeline pip list`
2. Проверьте копирование: `docker exec -it ocr-pipeline ls -la /shared/pipeline-deps`
3. Пересоберите контейнер: `docker-compose build --no-cache ocr-pipeline`

### VLM API недоступен

1. Проверьте сеть: `docker network inspect ocr_open-webui-network`
2. Проверьте переменные окружения: `docker exec -it open-webui env | grep VLM`
3. Если VLM на хосте, добавьте в docker-compose.yml:
   ```yaml
   open-webui:
     extra_hosts:
       - "host.docker.internal:host-gateway"
   ```

## Интеграция с VLM API в Docker

Если VLM API тоже в Docker, добавьте в `docker-compose.yml`:

```yaml
services:
  vlm-api:
    image: your-vlm-api-image:latest
    container_name: vlm-api
    ports:
      - "8000:8000"
    networks:
      - open-webui-network

  open-webui:
    # ...
    environment:
      - VLM_API_URL=http://vlm-api:8000/v1
    depends_on:
      - vlm-api
```

