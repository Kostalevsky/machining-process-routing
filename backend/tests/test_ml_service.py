from app.core.config import settings
from app.modules.ml.service import (
    add_russian_labels,
    build_generation_prompt,
    generate_process_json_from_collage,
    normalize_process_json,
    safe_json_loads,
)


def test_safe_json_loads_accepts_fenced_json() -> None:
    payload = safe_json_loads('```json\n{"Steps": []}\n```')

    assert payload == {"Steps": []}


def test_build_generation_prompt_uses_collage_size_prompt(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ml_enable_rag", False)

    prompt = build_generation_prompt(collage_size=3, collage_file_name="collage_3.png")

    assert "providing 3 dimensions" in prompt
    assert "[Image file: collage_3.png]" in prompt


def test_stub_generation_returns_process_json() -> None:
    result = generate_process_json_from_collage(
        collage_bytes=b"not-used-for-stub",
        collage_file_name="collage_6.png",
        collage_size=6,
        provider="stub",
        model_name="mock-generator",
        prompt_version="v1",
    )

    assert result.payload["File name"] == "collage_6.png"
    assert result.payload["Steps"][0]["Action"] == "milling"
    assert result.payload["Name of operation RU"] == "Технологический маршрут обработки"
    assert result.payload["Steps"][0]["Action RU"] == "фрезерование"
    assert "\\u0422" not in result.raw_response
    assert result.provider == "stub"


def test_add_russian_labels_adds_localized_step_fields() -> None:
    payload = add_russian_labels(
        {
            "Name of operation": "Manufacturing Process",
            "Steps": [
                {
                    "Step number": 1,
                    "Stage": "roughing",
                    "Action": "milling",
                    "Equipment": ["machining center"],
                    "ISO": [],
                }
            ],
        }
    )

    assert payload["Name of operation RU"] == "Технологический маршрут обработки"
    assert payload["Steps"][0]["Action RU"] == "фрезерование"
    assert payload["Steps"][0]["Stage RU"] == "черновая обработка"
    assert payload["Steps"][0]["Equipment RU"] == ["обрабатывающий центр"]


def test_normalize_process_json_repairs_missing_stages() -> None:
    payload = normalize_process_json(
        {
            "Steps": [
                {"Action": "milling", "Equipment": ["machining center"], "ISO": []},
            ]
        },
        fallback_file_name="collage.png",
    )

    assert [step["Stage"] for step in payload["Steps"]] == [
        "finishing",
        "quality-inspection",
        "packaging",
    ]
