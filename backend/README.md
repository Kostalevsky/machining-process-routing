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
