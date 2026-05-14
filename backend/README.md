# Backend

Стартовый каркас бэкенда для проекта маршрутизации мехобработки.

Текущий стек:
- FastAPI;
- SQLAlchemy;
- Alembic;
- PostgreSQL.
- MinIO(S3-compatible storage).
- Blender inside API container for OBJ rendering.

`run` трактуется как сессия пользователя над одной CAD-моделью.

## Запуск Через Docker Compose

1. Перейти в папку `backend`.
2. Скопировать `.env.example` в `.env` и при необходимости скорректировать секреты.
3. Выполнить:

```bash
docker compose up --build
```

После запуска будут доступны:
- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Postgres: `localhost:5432`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`

При старте контейнера API автоматически выполняется команда:

```bash
alembic upgrade head
```

То есть при первом запуске схема БД создастся автоматически из миграций.

`docker compose` также поднимает MinIO и автоматически создаёт bucket для артефактов.

Для `POST /api/v1/runs/{run_id}/process` backend использует встроенный Blender-скрипт
`backend/app/modules/processing/blender_render_script.py`. Дополнительные файлы из корня
репозитория для контейнерного рендера не нужны.

Архитектурная карта backend: `backend/ARCHITECTURE.md`.

## Базовые Ручки MVP

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/users/me`
- `POST /api/v1/runs`
- `GET /api/v1/runs`
- `GET /api/v1/runs/{run_id}`
- `POST /api/v1/runs/{run_id}/source-file`
- `POST /api/v1/runs/{run_id}/process`

Для всех ручек кроме `health` и `auth/*` нужен Bearer access token.

## ML / VLM Генерация JSON

`POST /api/v1/runs/{run_id}/generations` теперь может работать в нескольких режимах:

- `provider=stub` — локальный режим без внешнего API, полезен для тестов.
- `provider=mistral` — Pixtral через Mistral API.
- `provider=qwen` — Qwen VL через DashScope OpenAI-compatible API.

Пример payload для реальной генерации:

```json
{
  "provider": "qwen",
  "model_name": "qwen-vl-max",
  "prompt_version": "v1"
}
```

Для `mistral` нужен `ML_MISTRAL_API_KEY`, для `qwen` нужен `ML_QWEN_API_KEY`.
Prompt-файлы и таблица оборудования/стандартов перенесены внутрь backend в
`app/modules/ml/assets`, поэтому контейнеру не нужен доступ к соседней ML-папке.
