from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Machining Process Routing API"
    api_prefix: str = "/api/v1"
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/machining_process_routing"
    )
    jwt_secret_key: str = "change-me-access-secret-key-at-least-32-bytes"
    jwt_refresh_secret_key: str = "change-me-refresh-secret-key-at-least-32-bytes"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    s3_endpoint_url: str = "http://localhost:9000"
    s3_public_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "machining-process-routing"
    s3_region: str = "us-east-1"
    s3_presign_expire_seconds: int = 3600
    blender_binary: str = "blender"
    blender_render_script_path: str = "app/modules/processing/blender_render_script.py"
    render_num_images: int = 6
    render_light_mode: str = "uniform"
    render_camera_pose: str = "z-circular-elevated"
    render_camera_dist_min: float = 2.0
    render_camera_dist_max: float = 2.0
    render_timeout_seconds: int = 300
    ml_default_provider: str = "stub"
    ml_default_model_name: str = "mock-generator"
    ml_prompt_version: str = "v1"
    ml_enable_rag: bool = True
    ml_enable_ru_labels: bool = True
    ml_export_debug_fields: bool = False
    ml_qwen_api_key: str | None = None
    ml_qwen_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    ml_mistral_api_key: str | None = None
    ml_openai_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
