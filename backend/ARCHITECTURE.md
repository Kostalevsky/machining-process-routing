# Backend Architecture

Этот файл нужен как короткая техническая карта `backend`: что за что отвечает, куда течёт
данные и в каком порядке проходит основной pipeline.

## Layers

```mermaid
flowchart LR
    Client["Client / Frontend / Scripts"]
    API["FastAPI Routers\napp/api + app/modules/*/api.py"]
    Services["Domain Services\nidentity / runs / processing / collages / generations"]
    DB["PostgreSQL\nusers / runs / artifacts / generations / run_events"]
    S3["MinIO / S3\nsource obj / renders / collages / generated json"]
    Blender["Blender + blender_render_script.py"]

    Client --> API
    API --> Services
    Services --> DB
    Services --> S3
    Services --> Blender
    Blender --> S3
```

## Main Modules

```mermaid
flowchart TD
    Main["app/main.py"]
    Router["app/api/router.py"]
    Health["health"]
    Identity["identity"]
    Runs["runs API"]
    Proc["processing.service"]
    Collages["collages.service"]
    Generations["generations.service"]
    Storage["infrastructure/storage.py"]
    Models["SQLAlchemy models"]

    Main --> Router
    Router --> Health
    Router --> Identity
    Router --> Runs

    Runs --> Proc
    Runs --> Collages
    Runs --> Generations
    Runs --> Storage
    Identity --> Models
    Proc --> Models
    Collages --> Models
    Generations --> Models
    Storage --> Models
```

## Request Flow

### 1. Auth

```mermaid
sequenceDiagram
    participant C as Client
    participant A as identity.api
    participant S as identity.service
    participant D as Postgres

    C->>A: POST /auth/register or /auth/login
    A->>S: validate payload
    S->>D: create/load user
    S->>S: hash password or verify hash
    S->>S: issue access + refresh JWT
    S-->>A: TokenPairResponse
    A-->>C: bearer tokens + user
```

### 2. OBJ Upload -> Render -> Collage

```mermaid
sequenceDiagram
    participant C as Client
    participant R as runs.api
    participant RS as runs.service
    participant PS as processing.service
    participant B as Blender
    participant CS as collages.service
    participant S3 as MinIO/S3
    participant DB as Postgres

    C->>R: POST /runs
    R->>RS: create_run()
    RS->>DB: insert run + run_created event

    C->>R: POST /runs/{id}/source-file
    R->>RS: upload_source_model()
    RS->>S3: store OBJ
    RS->>DB: insert source artifact + source_uploaded event

    C->>R: POST /runs/{id}/process
    R->>PS: start_run_processing()
    PS->>S3: download source OBJ
    PS->>DB: set status=rendering + render_started
    PS->>B: run blender_render_script.py
    B-->>PS: base PNG renders
    PS->>S3: upload render images
    PS->>DB: insert render artifacts + render_finished

    C->>R: POST /runs/{id}/collages/generate
    R->>CS: generate_collages_for_run()
    CS->>S3: download render images
    CS->>CS: Isomap + farthest-point selection
    CS->>S3: upload collage PNGs
    CS->>DB: insert collage artifacts + collage_created
```

### 3. Selected Collage -> JSON Generation

```mermaid
sequenceDiagram
    participant C as Client
    participant R as runs.api
    participant GS as generations.service
    participant S3 as MinIO/S3
    participant DB as Postgres

    C->>R: POST /runs/{id}/generations
    R->>GS: create_generation_for_run()
    GS->>DB: insert generation + generation_started
    GS->>GS: build stub JSON payload
    GS->>S3: upload generated JSON artifact
    GS->>DB: mark generation succeeded, set run.completed
    GS->>DB: write generation_completed event
    R-->>C: updated run with generation and artifact links
```

## Data Model

```mermaid
erDiagram
    USERS ||--o{ RUNS : owns
    RUNS ||--o{ ARTIFACTS : contains
    RUNS ||--o{ RUN_EVENTS : logs
    RUNS ||--o{ GENERATIONS : has
    ARTIFACTS }o--|| RUNS : source_artifact_id
    ARTIFACTS }o--|| RUNS : selected_collage_artifact_id
    GENERATIONS }o--|| RUNS : latest_generation_id

    USERS {
        int id
        string email
        string password_hash
    }

    RUNS {
        int id
        int user_id
        string name
        string status
        int source_artifact_id
        int selected_collage_artifact_id
        int latest_generation_id
    }

    ARTIFACTS {
        int id
        int run_id
        int user_id
        string type
        string bucket
        string object_key
        string file_name
    }

    RUN_EVENTS {
        int id
        int run_id
        string event_type
    }

    GENERATIONS {
        int id
        int run_id
        int user_id
        int input_collage_artifact_id
        int output_artifact_id
        string status
    }
```

## Reading Order

Если нужно быстро погрузиться:

1. `backend/ARCHITECTURE.md`
2. `backend/CODEX_BACKEND_CONTEXT.md`
3. `backend/app/modules/runs/api.py`
4. `backend/app/modules/runs/service.py`
5. `backend/app/modules/processing/service.py`
6. `backend/app/modules/collages/service.py`
7. `backend/app/modules/generations/service.py`
8. `backend/app/models/*.py`
