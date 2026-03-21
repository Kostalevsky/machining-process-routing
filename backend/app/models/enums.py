import enum


class RunStatus(str, enum.Enum):
    CREATED = "created"
    SOURCE_UPLOADED = "source_uploaded"
    RENDERING = "rendering"
    RENDERED = "rendered"
    COLLAGES_READY = "collages_ready"
    GENERATING_JSON = "generating_json"
    COMPLETED = "completed"
    FAILED = "failed"


class ArtifactType(str, enum.Enum):
    SOURCE_OBJ = "source_obj"
    RENDER = "render"
    COLLAGE = "collage"
    GENERATED_JSON = "generated_json"


class GenerationStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
