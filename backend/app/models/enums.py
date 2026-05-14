import enum


class RunStatus(enum.StrEnum):
    CREATED = "created"
    SOURCE_UPLOADED = "source_uploaded"
    RENDERING = "rendering"
    RENDERED = "rendered"
    COLLAGES_READY = "collages_ready"
    GENERATING_JSON = "generating_json"
    COMPLETED = "completed"
    FAILED = "failed"


class ArtifactType(enum.StrEnum):
    SOURCE_OBJ = "source_obj"
    RENDER = "render"
    COLLAGE = "collage"
    GENERATED_JSON = "generated_json"


class GenerationStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
