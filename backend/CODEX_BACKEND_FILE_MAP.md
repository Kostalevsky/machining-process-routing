# Backend File Map For Codex

Обновлено: 2026-04-23.

Карта файлов `backend` с назначением каждого существенного файла.

## Root Backend Files

`README.md`
- Краткое описание backend, Docker Compose запуска и базовых MVP endpoints.
- Отстает от текущего кода: не описывает render upload, collages, generations.

`MANAGER_DATA_OVERVIEW.md`
- Бизнес-описание хранения данных.
- Хорошо объясняет разделение Postgres и S3/MinIO.
- Описывает users, runs, artifacts, run events, generations.

`CODEX_BACKEND_CONTEXT.md`
- Сводный технический контекст для будущего Codex.

`CODEX_BACKEND_FILE_MAP.md`
- Этот файл: карта проекта.

`pyproject.toml`
- Ruff config: Python 3.12, line length 100, selects E/F/I/B/UP, ignores B008.
- Pytest config: `testpaths = ["tests"]`, `python_files = ["test_*.py"]`, `addopts = "-q"`.

`requirements.txt`
- Runtime/dev dependencies:
  FastAPI, uvicorn, SQLAlchemy, Alembic, psycopg, pydantic-settings, multipart,
  email-validator, PyJWT, passlib[bcrypt], boto3, pytest, httpx, ruff, pre-commit,
  numpy, Pillow, scikit-learn.

`Dockerfile`
- `python:3.12-slim`.
- Installs requirements.
- Copies backend into `/app`.
- Makes entrypoint executable.

`docker-compose.yml`
- Services:
  - `api`
  - `db` Postgres 16
  - `minio`
  - `minio-init`
- API depends on healthy DB and MinIO bucket init.

`docker-entrypoint.sh`
- `alembic upgrade head`.
- Starts uvicorn with reload on host `0.0.0.0`, port `8000`.

`.env.example`
- Example env vars for app, DB, JWT, S3/MinIO, Blender/render.

`.dockerignore`
- Ignores pycache, pytest/mypy cache, venv, `.env`, selected pycache paths.

`alembic.ini`
- Alembic script location and default DB URL.
- Actual URL is overwritten in `alembic/env.py` from settings.

## Application Entrypoint

`app/main.py`
- Defines `create_app()`.
- Creates FastAPI app with `settings.app_name`.
- Includes `api_router` under `settings.api_prefix`.
- Exposes module-level `app`.

`app/__init__.py`
- Empty package marker.

## Core

`app/core/config.py`
- Defines `BACKEND_ROOT`.
- Defines `Settings(BaseSettings)`.
- Important settings:
  - app name and API prefix;
  - database URL;
  - JWT access/refresh secrets and expirations;
  - S3/MinIO endpoints, credentials, bucket, region, presign TTL;
  - Blender binary/script/render settings.
- Instantiates global `settings`.

`app/core/security.py`
- Password hashing:
  - `hash_password`
  - `verify_password`
- Token helpers:
  - `create_access_token`
  - `create_refresh_token`
  - `decode_access_token`
  - `decode_refresh_token`
- Token payload fields:
  - `sub` as string user id;
  - `type` as `access` or `refresh`;
  - `exp`.
- Invalid token errors become HTTP 401.

`app/core/__init__.py`
- Empty package marker.

## API Router

`app/api/router.py`
- Creates top-level `APIRouter`.
- Includes:
  - health router;
  - identity router;
  - runs router.

`app/api/routes/health.py`
- `GET /health` returns `{"status": "ok"}`.

`app/api/__init__.py`, `app/api/routes/__init__.py`
- Empty package markers.

## Database

`app/db/base_class.py`
- SQLAlchemy `DeclarativeBase`.

`app/db/base.py`
- Imports all ORM models for metadata discovery.
- Used by Alembic.

`app/db/session.py`
- Creates SQLAlchemy engine from `settings.database_url`.
- Defines `SessionLocal`.
- Defines FastAPI dependency `get_db()`.

`app/db/__init__.py`
- Empty package marker.

## Models

`app/models/enums.py`
- `RunStatus`
- `ArtifactType`
- `GenerationStatus`

`app/models/mixins.py`
- `TimestampMixin` with `created_at` and `updated_at`.

`app/models/user.py`
- `User` table.
- Fields: id, email, password_hash, timestamps.
- Relationship: `runs`.

`app/models/run.py`
- `Run` table.
- Fields: id, user_id, name, status, source/selected/latest references, timestamps.
- Relationships: user, artifacts, generations, events.
- Uses helper functions for relationship foreign keys to avoid circular import issues.

`app/models/artifact.py`
- `Artifact` table.
- Stores metadata for files in S3/MinIO.
- Relationship back to run.

`app/models/run_event.py`
- `RunEvent` table.
- Stores event type, JSON payload, created_at.

`app/models/generation.py`
- `Generation` table.
- Stores input collage, output artifact, provider/model/prompt metadata, status, error,
  completed_at, timestamps.

`app/models/__init__.py`
- Empty currently.

## Infrastructure

`app/infrastructure/storage.py`
- `S3Storage` wrapper around boto3 S3 client.
- Upload/download bytes.
- Generate presigned download URL.
- `_replace_base_url` swaps internal S3 endpoint with public endpoint.

`app/infrastructure/__init__.py`
- Empty package marker.

## Identity Module

`app/modules/identity/schemas.py`
- Pydantic request/response models:
  - `RegisterRequest`
  - `LoginRequest`
  - `RefreshTokenRequest`
  - `UserResponse`
  - `TokenPairResponse`

`app/modules/identity/service.py`
- `register_user`
- `authenticate_user`
- `build_token_pair`
- `refresh_tokens`
- `get_current_user`
- Uses FastAPI dependencies and SQLAlchemy session.

`app/modules/identity/api.py`
- Routes:
  - `POST /auth/register`
  - `POST /auth/login`
  - `POST /auth/refresh`
  - `GET /users/me`

`app/modules/identity/__init__.py`
- Empty package marker.

## Runs Module

`app/modules/runs/schemas.py`
- Pydantic schemas:
  - `RunCreateRequest`
  - `CollageGenerateRequest`
  - `CollageSelectRequest`
  - `GenerationCreateRequest`
  - `ArtifactResponse`
  - `RunEventResponse`
  - `GenerationResponse`
  - `RunResponse`

`app/modules/runs/service.py`
- Run CRUD and serialization:
  - `create_run`
  - `list_runs_for_user`
  - `get_run_for_user`
  - `serialize_run`
  - `serialize_artifact`
- Upload flows:
  - `upload_source_model`
  - `upload_render_images`
- Selection helper:
  - `get_selected_collage_artifact`

`app/modules/runs/api.py`
- Main authenticated business API under `/runs`.
- Creates `S3Storage` inside each endpoint.
- Uses `get_current_user` for auth.

`app/modules/runs/__init__.py`
- Empty package marker.

## Artifacts Module

`app/modules/artifacts/service.py`
- Artifact object key builders:
  - source
  - render
  - collage
  - generated JSON
- File validators:
  - source `.obj`
  - render `.png`, `.jpg`, `.jpeg`
- `create_artifact` factory.
- `build_artifact_download_url`.

`app/modules/artifacts/__init__.py`
- Empty package marker.

## Processing Module

`app/modules/processing/service.py`
- `start_run_processing`.
- Validates source exists.
- Downloads source from S3.
- Marks run as `rendering`.
- Calls Blender rendering helper.
- Uploads render artifacts.
- Marks run as `rendered`.
- Writes render events.

`app/modules/processing/rendering.py`
- `RenderedImage` dataclass.
- `render_source_model`.
- Creates temp workspace.
- Writes source file and `object_paths.pkl`.
- Runs Blender with configured script and parameters.
- Collects PNG outputs.
- Collects image bytes before temp dir is deleted.

`app/modules/processing/blender_render_script.py`
- Vendored Blender render script used by backend container.
- Keeps backend self-contained: Docker image no longer depends on a bind-mounted root script.

`app/modules/processing/__init__.py`
- Empty package marker.

## Collages Module

`app/modules/collages/service.py`
- `generate_collages_for_run`
- `select_collage_for_run`
- Private helpers:
  - `_normalize_counts`
  - `_load_render_images`
  - `_get_farthest_indices`
  - `_build_collage_image`
  - `_image_to_png_bytes`
- Uses Pillow/numpy/Isomap.
- Supports collage sizes 3, 4, 6.

`app/modules/collages/__init__.py`
- Empty package marker.

## Generations Module

`app/modules/generations/service.py`
- `create_generation_for_run`.
- Requires selected collage.
- Creates `Generation`.
- Writes stub JSON result to S3.
- Creates generated JSON artifact.
- Marks generation `succeeded`.
- Marks run `completed`.

`app/modules/generations/__init__.py`
- Empty package marker.

## Alembic

`alembic/env.py`
- Wires Alembic to app settings and Base metadata.

`alembic/script.py.mako`
- Standard Alembic migration template.

`alembic/versions/20260321_0001_initial_schema.py`
- Initial schema for users, runs, artifacts, generations, run_events and enums.

`alembic/versions/20260412_0002_add_created_at_to_run_events.py`
- Adds `created_at` to `run_events`.

## Tests

`tests/conftest.py`
- Adds backend root to `sys.path`.

`tests/test_health_api.py`
- Health endpoint.
- OpenAPI contains core paths.

`tests/test_security.py`
- Password hash roundtrip.
- Access token roundtrip.
- Refresh token roundtrip.

`tests/test_artifact_service.py`
- Source object key scoping/sanitization.
- Source file extension validation.

## Scripts And Generated E2E Artifacts

`scripts/run_e2e_checks.py`
- Manual e2e runner using `urllib`.
- Creates user, logs in, creates runs, tests negative cases, uploads files, checks processing,
  generates/selects collages, creates generations.
- Writes text and JSON reports to `e2e-results`.

`e2e-results/latest.json`
- Last stored result from 2026-04-12.
- Shows 32 passed, 0 failed, but appears stale relative to current e2e script.

`e2e-results/latest.log`
- Text version of latest e2e report.

`e2e-results/*.json`, `e2e-results/*.log`
- Historical e2e reports.

`e2e-results/selected-collage.png`
- PNG 48x32.

`e2e-results/selected-collage-via-endpoint.png`
- PNG 48x32.

`e2e-results/tmp/*`
- Temporary test inputs and render PNGs used by e2e/smoke checks.
- Includes empty/invalid files and small render images.
