import pytest
from app.modules.artifacts.service import build_source_object_key, validate_source_file
from fastapi import HTTPException


def test_build_source_object_key_uses_run_and_user_scope() -> None:
    object_key = build_source_object_key(user_id=12, run_id=34, file_name="../part.obj")

    assert object_key.startswith("users/12/runs/34/source/")
    assert object_key.endswith("_part.obj")
    assert ".." not in object_key


def test_validate_source_file_accepts_obj() -> None:
    validate_source_file("part.obj")
    validate_source_file("PART.OBJ")


def test_validate_source_file_rejects_non_obj() -> None:
    with pytest.raises(HTTPException) as exc_info:
        validate_source_file("part.stl")

    assert exc_info.value.status_code == 400
