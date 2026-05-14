# Backend Context For Codex

Обновлено: 2026-04-24.

Этот файл нужен как быстрый вход в контекст `backend`, если в будущем пользователь скажет
что-то вроде "прочитай контекст backend". Он описывает текущее состояние рабочей копии, а не
только закоммиченный код: на момент чтения в `backend` уже были незакоммиченные изменения и
новые файлы.

## Краткая Суть

`backend` - FastAPI-сервис для маршрутизации процесса мехобработки вокруг одной загруженной
CAD/OBJ-модели.

Главная бизнес-сущность - `run`: одна пользовательская сессия работы с одной 3D-моделью.
`run` связывает пользователя, исходный `.obj`, рендеры, коллажи, генерации JSON и историю
событий.

Стек:
- FastAPI.
- SQLAlchemy 2.x.
- Alembic.
- PostgreSQL.
- S3-compatible storage через MinIO и `boto3`.
- PyJWT для access/refresh токенов.
- `passlib` с `pbkdf2_sha256` для паролей.
- Blender вызывается внешним процессом для рендера `.obj`.
- Pillow, numpy, scikit-learn/Isomap используются для коллажей.

## Как Запускается

Основной app создается в `app/main.py`:
- `create_app()` создает `FastAPI(title=settings.app_name, version="0.1.0")`.
- `api_router` подключается с префиксом `settings.api_prefix`, по умолчанию `/api/v1`.

Docker:
- `backend/docker-compose.yml` поднимает `api`, `db`, `minio`, `minio-init`.
- API-контейнер монтирует текущую папку в `/app` и запускает `/app/docker-entrypoint.sh`.
- entrypoint выполняет `alembic upgrade head`, затем `uvicorn app.main:app --reload`.
- MinIO bucket создается сервисом `minio-init`.

Настройки:
- `app/core/config.py` использует `pydantic-settings`.
- `.env.example` содержит переменные для БД, JWT, S3/MinIO и Blender/render.
- `.env` есть локально, но его не надо переносить в документацию или коммиты.

## API

Публичные ручки:
- `GET /api/v1/health`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`

Ручки с Bearer access token:
- `GET /api/v1/users/me`
- `POST /api/v1/runs`
- `GET /api/v1/runs`
- `GET /api/v1/runs/{run_id}`
- `GET /api/v1/runs/{run_id}/selected-collage`
- `POST /api/v1/runs/{run_id}/source-file`
- `POST /api/v1/runs/{run_id}/renders`
- `POST /api/v1/runs/{run_id}/process`
- `POST /api/v1/runs/{run_id}/collages/generate`
- `POST /api/v1/runs/{run_id}/collages/select`
- `POST /api/v1/runs/{run_id}/generations`

`README.md` перечисляет базовый MVP, но текущий код уже содержит дополнительные endpoints для
рендеров, коллажей и генераций.

## Данные И Модели

Все SQLAlchemy-модели наследуются от `app/db/base_class.py::Base`.
`app/db/base.py` импортирует модели для Alembic metadata.

### User

Файл: `app/models/user.py`.

Поля:
- `id`
- `email`, unique, indexed
- `password_hash`
- `created_at`, `updated_at` из `TimestampMixin`

Связь:
- `runs`

### Run

Файл: `app/models/run.py`.

Поля:
- `id`
- `user_id`
- `name`
- `status`
- `source_artifact_id`
- `selected_collage_artifact_id`
- `latest_generation_id`
- `created_at`, `updated_at`

Связи:
- `user`
- `artifacts`
- `generations`
- `events`

`RunStatus`:
- `created`
- `source_uploaded`
- `rendering`
- `rendered`
- `collages_ready`
- `generating_json`
- `completed`
- `failed`

### Artifact

Файл: `app/models/artifact.py`.

`artifact` - универсальная запись о файле в S3/MinIO.

Поля:
- `id`
- `run_id`
- `user_id`
- `type`
- `bucket`
- `object_key`
- `file_name`
- `content_type`
- `size_bytes`
- `checksum`
- `meta_json`
- `created_at`, `updated_at`

`ArtifactType`:
- `source_obj`
- `render`
- `collage`
- `generated_json`

### RunEvent

Файл: `app/models/run_event.py`.

История действий внутри run.

Поля:
- `id`
- `run_id`
- `event_type`
- `payload_json`
- `created_at`

Известные события из текущего кода:
- `run_created`
- `source_uploaded`
- `renders_uploaded`
- `render_started`
- `render_finished`
- `collage_created`
- `collage_selected`
- `generation_started`
- `generation_completed`

### Generation

Файл: `app/models/generation.py`.

Запись об отдельной попытке генерации результата.

Поля:
- `id`
- `run_id`
- `user_id`
- `input_collage_artifact_id`
- `output_artifact_id`
- `provider`
- `model_name`
- `prompt_version`
- `status`
- `error_message`
- `completed_at`
- `created_at`, `updated_at`

`GenerationStatus`:
- `pending`
- `running`
- `succeeded`
- `failed`

## Основные Сценарии

### Auth

Код:
- `app/modules/identity/api.py`
- `app/modules/identity/service.py`
- `app/core/security.py`
- `app/modules/identity/schemas.py`

Регистрация:
1. email нормализуется через `strip().lower()`.
2. Проверяется уникальность.
3. Пароль хэшируется `pbkdf2_sha256`.
4. Создается пользователь.
5. Возвращается пара токенов.

Логин:
1. email нормализуется.
2. Пользователь ищется в БД.
3. Проверяется пароль.
4. Возвращается access/refresh token pair.

Refresh:
1. `decode_refresh_token`.
2. `sub` превращается в `user_id`.
3. Пользователь должен существовать.
4. Возвращается новая пара токенов.

`get_current_user` использует `HTTPBearer(auto_error=False)`, сам возвращает 401 если токена нет,
токен плохой или пользователь не найден.

### Создание Run

Код:
- `app/modules/runs/api.py`
- `app/modules/runs/service.py::create_run`

Создается `Run(status=created)`, затем событие `run_created`.
Ответ сериализуется через `serialize_run`, где artifacts/events/generations сортируются по
`created_at` в обратном порядке.

### Загрузка Source OBJ

Код:
- `app/modules/runs/service.py::upload_source_model`
- `app/modules/artifacts/service.py`

Правила:
- разрешен только `.obj`;
- пустой файл отклоняется;
- повторная загрузка source в тот же run отклоняется 409;
- объект кладется в S3 по ключу
  `users/{user_id}/runs/{run_id}/source/{uuid}_{safe_file_name}`;
- создается artifact `source_obj`;
- `run.source_artifact_id` заполняется;
- `run.status` становится `source_uploaded`;
- добавляется событие `source_uploaded`.

### Ручная Загрузка Render Images

Код:
- endpoint `POST /runs/{run_id}/renders`
- `app/modules/runs/service.py::upload_render_images`

Правила:
- нужен хотя бы один файл;
- разрешены `.png`, `.jpg`, `.jpeg`;
- пустой файл отклоняется;
- каждый файл кладется в S3 по ключу
  `users/{user_id}/runs/{run_id}/renders/{uuid}_{safe_file_name}`;
- создаются artifacts `render`;
- `run.status` становится `rendered`;
- событие `renders_uploaded`.

### Автоматический Processing / Blender Render

Код:
- endpoint `POST /runs/{run_id}/process`
- `app/modules/processing/service.py`
- `app/modules/processing/rendering.py`

Логика:
1. Нужен `source_artifact_id`, иначе 409.
2. Если статус уже `rendering`, возвращается 409.
3. Source artifact должен быть в `run.artifacts` и иметь type `source_obj`.
4. Source bytes скачиваются из S3.
5. Run переводится в `rendering`.
6. Пишется событие `render_started`.
7. `render_source_model` вызывает Blender:
   - создает temp dir;
   - записывает source `.obj`;
   - создает `object_paths.pkl`;
   - запускает `settings.blender_binary -b -P settings.blender_render_script_path -- ...`;
   - ожидает PNG в `rendered_imgs/{source_stem}`.
8. Каждый PNG загружается в S3 как artifact `render`.
9. Run переводится в `rendered`.
10. Пишется событие `render_finished`.

Скрипт Blender теперь vendored внутрь backend по пути
`app/modules/processing/blender_render_script.py`, так что контейнерный рендер не зависит
от bind-mount файлов из корня репозитория.

`render_source_model` теперь возвращает байты PNG, а не пути к временным файлам, поэтому
temp dir безопасно удаляется сразу после завершения Blender-процесса.

Еще одна заметка: `start_run_processing` запрещает только повторный запуск при статусе
`rendering`. Также он теперь отклоняет повторный process, если у run уже есть render artifacts.

### Генерация Коллажей

Код:
- endpoint `POST /runs/{run_id}/collages/generate`
- `app/modules/collages/service.py`

Логика:
1. Берутся все artifacts с type `render`, сортируются по `created_at`.
2. Нужно минимум 3 render image.
3. `counts` нормализуется: разрешены только 3, 4, 6 и не больше доступного количества рендеров.
4. Если `selected_count` задан, он должен входить в нормализованные counts.
5. Изображения скачиваются из S3, открываются Pillow, приводятся к RGB.
6. Для каждого изображения строится grayscale vector 64x64.
7. `Isomap(n_components=2)` проецирует в 2D.
8. Выбираются самые удаленные точки через `_get_farthest_indices`.
9. Собираются коллажи:
   - 3: горизонтальная строка 3x1;
   - 4: сетка 2x2;
   - 6: сетка 3x2.
10. Коллажи загружаются в S3 как artifacts `collage`.
11. На каждый коллаж пишется событие `collage_created`.
12. `run.selected_collage_artifact_id` ставится по `selected_count` или первому normalized count.
13. `run.status` становится `collages_ready`.

### Выбор Коллажа

Код:
- endpoint `POST /runs/{run_id}/collages/select`
- `app/modules/collages/service.py::select_collage_for_run`

Проверяется, что artifact существует внутри этого run и type == `collage`.
Затем обновляется `run.selected_collage_artifact_id` и пишется событие `collage_selected`.

Endpoint `GET /runs/{run_id}/selected-collage` возвращает выбранный artifact с presigned URL.

### Stub JSON Generation

Код:
- endpoint `POST /runs/{run_id}/generations`
- `app/modules/generations/service.py`

Логика:
1. Нужен выбранный коллаж.
2. Artifact выбранного коллажа должен существовать и иметь type `collage`.
3. Создается `Generation(status=running)`.
4. Пишется событие `generation_started`.
5. Формируется stub JSON payload с run/user/generation/provider/model/prompt.
6. JSON загружается в S3 как artifact `generated_json`.
7. Generation переводится в `succeeded`, заполняется `output_artifact_id` и `completed_at`.
8. `run.latest_generation_id` обновляется.
9. `run.status` становится `completed`.
10. Пишется событие `generation_completed`.

Это пока не реальная AI/inference-генерация, а синхронный stub.

## S3 / Storage

Код:
- `app/infrastructure/storage.py`
- `app/modules/artifacts/service.py`

`S3Storage` создает boto3 S3 client по settings:
- `S3_ENDPOINT_URL`
- `S3_PUBLIC_ENDPOINT_URL`
- `S3_ACCESS_KEY`
- `S3_SECRET_KEY`
- `S3_BUCKET`
- `S3_REGION`
- `S3_PRESIGN_EXPIRE_SECONDS`

Методы:
- `upload_bytes`
- `download_bytes`
- `generate_presigned_url`

`generate_presigned_url` сначала получает URL от boto3, затем `_replace_base_url` заменяет
scheme/netloc на public endpoint. Это нужно, потому что внутри docker endpoint может быть
`http://minio:9000`, а снаружи пользователь должен получать `http://localhost:9000`.

Object key helpers:
- source: `users/{user_id}/runs/{run_id}/source/{uuid}_{file_name}`
- render: `users/{user_id}/runs/{run_id}/renders/{uuid}_{file_name}`
- collage: `users/{user_id}/runs/{run_id}/collages/{count}_{uuid}.png`
- generated JSON: `users/{user_id}/runs/{run_id}/generated/{uuid}.json`

## Миграции

`alembic/env.py` берет database URL из settings и использует `Base.metadata`.

Миграции:
- `20260321_0001_initial_schema.py`
  - создает enum types: `run_status`, `artifact_type`, `generation_status`;
  - создает таблицы `users`, `runs`, `artifacts`, `generations`, `run_events`;
  - добавляет индексы;
  - добавляет FK из `runs` на `artifacts` и `generations` после создания таблиц.
- `20260412_0002_add_created_at_to_run_events.py`
  - добавляет `run_events.created_at`.

Заметка: ORM-модели сейчас имеют `updated_at` с `onupdate`, но миграции создают только
server defaults, без DB-level trigger для автообновления `updated_at`. SQLAlchemy `onupdate`
сработает при ORM update, но не при прямых SQL update.

## Тесты И E2E

Unit/API tests:
- `tests/test_health_api.py`
  - healthcheck;
  - OpenAPI содержит auth/register и runs.
- `tests/test_security.py`
  - password hash/verify;
  - access token encode/decode;
  - refresh token encode/decode.
- `tests/test_artifact_service.py`
  - source object key sanitized by `Path(file_name).name`;
  - `.obj` принимается;
  - non-`.obj` отклоняется.

`tests/conftest.py` добавляет `backend` в `sys.path`.

### E2E Скрипты

Для end-to-end проверок есть два скрипта в `scripts/`.

`scripts/run_e2e_checks.py` - основной самописный e2e runner на стандартном `urllib`, без pytest.
Он:
- читает базовый URL из `E2E_BASE_URL`, по умолчанию `http://localhost:8000`;
- пишет отчеты в `backend/e2e-results`;
- создает `e2e-results/e2e-YYYYMMDD-HHMMSS.log`;
- создает `e2e-results/e2e-YYYYMMDD-HHMMSS.json`;
- перезаписывает `e2e-results/latest.log` и `e2e-results/latest.json`;
- использует временные входные файлы из `e2e-results/tmp`;
- для source upload использует реальный OBJ:
  `../abc_dataset/00009490/00009490_48f21d6478e64f7d8eea685f_trimesh_001.obj`
  относительно backend root.

Текущий `run_e2e_checks.py` покрывает 29 кейсов:
- `healthcheck`;
- `openapi`;
- registration/login/refresh и негативные auth-проверки;
- `GET /users/me` без токена и с токеном;
- создание пустого и основного run;
- запрет processing без source artifact;
- list/get runs;
- запрет генерации коллажа без render artifacts;
- запрет generation без выбранного коллажа;
- валидацию source upload: non-`.obj`, пустой `.obj`, успешный upload, повторный upload;
- `POST /runs/{run_id}/process` с реальным Blender-render ожиданием;
- запрет повторного process после появления render artifacts;
- генерацию коллажей размеров 3, 4, 6 и выбор `selected_count`;
- запрет выбора несуществующего коллажа;
- успешный выбор коллажа;
- первую и вторую stub generation;
- финальное состояние run `completed` и наличие ожидаемых событий.

Важная деталь текущего `run_e2e_checks.py`: кейс `process_success` ожидает HTTP `202`,
статус run `rendered`, минимум 6 artifacts типа `render`, события `render_started` и
`render_finished`. Это проверяет реальный путь через Blender, а не ручную загрузку render images.

`scripts/run_real_render_collage_e2e.py` - более короткий smoke/e2e для реального рендера и
коллажа. Он:
- регистрирует пользователя;
- создает run;
- загружает тот же реальный OBJ из `../abc_dataset/...`;
- вызывает `POST /runs/{run_id}/process` с timeout 300 секунд;
- ожидает статус run `rendered` и минимум 6 render artifacts;
- вызывает `POST /runs/{run_id}/collages/generate` с `counts: [3, 4, 6]` и
  `selected_count: 6`;
- вызывает `GET /runs/{run_id}/selected-collage`;
- скачивает выбранный коллаж по presigned URL;
- печатает JSON summary в stdout: `run_id`, `render_artifact_count`,
  `selected_collage_artifact_id`, `selected_collage_size_bytes`, `download_url`.

### Как Запускать E2E

Предусловия:
- запущен backend stack (`docker compose up --build` из `backend`);
- API доступен на `E2E_BASE_URL` или на `http://localhost:8000`;
- MinIO доступен и bucket создан через `minio-init`;
- в API-контейнере доступен Blender и vendored script
  `app/modules/processing/blender_render_script.py`;
- рядом с `backend` существует `abc_dataset` с файлом, указанным выше.

Команды из `backend`:

```bash
python3 scripts/run_e2e_checks.py
python3 scripts/run_real_render_collage_e2e.py
```

Если API слушает другой адрес:

```bash
E2E_BASE_URL=http://localhost:8000 python3 scripts/run_e2e_checks.py
```

### Сохраненные E2E Артефакты

В `backend/e2e-results` сейчас лежат исторические отчеты:
- `e2e-20260412-144503.{log,json}`;
- `e2e-20260412-154920.{log,json}`;
- `e2e-20260412-183332.{log,json}`;
- `e2e-20260412-185341.{log,json}`;
- `latest.log`;
- `latest.json`;
- `selected-collage.png`;
- `selected-collage-via-endpoint.png`;
- `real-render-collage.png`;
- `tmp/*` с временными тестовыми файлами.

Важное расхождение:
- `e2e-results/latest.json` от 2026-04-12 показывает старый сценарий: 32 passed, 0 failed,
  но там есть ручная загрузка render images и `process_success` только "switched run to
  rendering", финальный статус остался `rendering`.
- Текущий `scripts/run_e2e_checks.py` уже другой: он ожидает реальный Blender processing до
  статуса `rendered`, render artifacts и финальный статус `completed`.
- Поэтому сохраненные `latest.*` нельзя считать подтверждением текущего e2e-сценария; после
  изменений processing/collage/generation их нужно пересоздать запуском актуального скрипта.

## Известные Риски И Точки Внимания

1. `process_success` в текущем e2e скрипте и `latest.json` описывают разные ожидания.

2. `GenerationStatus` имеет `failed`, `RunStatus` имеет `failed` и `generating_json`, но
   текущая generation-логика не использует эти статусы при ошибках, потому что stub выполняется
   синхронно и без try/except.

3. Auth токены не имеют revocation/blacklist/session table. Refresh token валиден до exp, если
   пользователь существует.

4. Валидация upload сейчас основана на расширениях файлов, не на MIME/content inspection.

5. Presigned URL создается при каждой сериализации artifact. Любой list/get run потенциально
   делает много S3 signing operations.

6. `README.md` отстает от текущего API: там нет `/renders`, `/collages/*`, `/generations`.

## Если Нужно Быстро Восстановить Контекст

Сначала читать:
1. `backend/CODEX_BACKEND_CONTEXT.md`
2. `backend/CODEX_BACKEND_FILE_MAP.md`
3. `backend/app/modules/runs/api.py`
4. `backend/app/modules/runs/service.py`
5. `backend/app/modules/processing/service.py`
6. `backend/app/modules/collages/service.py`
7. `backend/app/modules/generations/service.py`
8. `backend/app/models/enums.py`
9. `backend/MANAGER_DATA_OVERVIEW.md`

Для проверки поведения:
- unit tests: `pytest` из `backend`;
- e2e: `python3 backend/scripts/run_e2e_checks.py` при поднятом API/DB/MinIO/Blender.
