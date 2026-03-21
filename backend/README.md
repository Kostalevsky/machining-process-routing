# Backend

Стартовый каркас бэкенда для проекта маршрутизации мехобработки.

Текущий стек:
- FastAPI;
- SQLAlchemy;
- Alembic;
- PostgreSQL.

`run` трактуется как сессия пользователя над одной CAD-моделью.

## Запуск Через Docker Compose

1. Перейти в папку `backend`.
2. При необходимости сверить `.env` с `.env.example`.
3. Выполнить:

```bash
docker compose up --build
```

После запуска будут доступны:
- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Postgres: `localhost:5432`
