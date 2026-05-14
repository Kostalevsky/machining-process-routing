from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import BACKEND_ROOT, settings

ML_ASSETS_ROOT = BACKEND_ROOT / "app" / "modules" / "ml" / "assets"
PROMPTS_ROOT = ML_ASSETS_ROOT / "prompts"
EQUIPMENT_ISO_PATH = ML_ASSETS_ROOT / "equipment_iso_ru.csv"

ALLOWED_ACTIONS = {
    "turning",
    "facing",
    "boring",
    "threading",
    "drilling",
    "reaming",
    "milling",
    "slotting",
    "key-seating",
    "broaching",
    "heat-treatment",
    "deburring",
    "sand-blasting",
    "grinding",
    "polishing",
    "quality-inspection",
    "surface-coating",
    "packaging",
    "cutting-off",
    "knurling",
    "tapping",
    "lapping",
    "honing",
    "burnishing",
    "electro-discharge machining (EDM)",
    "laser cutting",
    "waterjet cutting",
    "assembly",
    "marking",
    "non-destructive testing (NDT)",
}

ACTION_RU_MAP = {
    "turning": "точение",
    "facing": "торцевание",
    "boring": "растачивание",
    "threading": "нарезание резьбы",
    "drilling": "сверление",
    "reaming": "развертывание",
    "milling": "фрезерование",
    "slotting": "долбление паза",
    "key-seating": "обработка шпоночного паза",
    "broaching": "протягивание",
    "heat-treatment": "термообработка",
    "deburring": "удаление заусенцев",
    "sand-blasting": "пескоструйная обработка",
    "grinding": "шлифование",
    "polishing": "полирование",
    "quality-inspection": "контроль качества",
    "surface-coating": "нанесение покрытия",
    "packaging": "упаковка",
    "cutting-off": "отрезка",
    "knurling": "накатка",
    "tapping": "нарезание внутренней резьбы",
    "lapping": "доводка",
    "honing": "хонингование",
    "burnishing": "выглаживание",
    "electro-discharge machining (EDM)": "электроэрозионная обработка",
    "laser cutting": "лазерная резка",
    "waterjet cutting": "гидроабразивная резка",
    "assembly": "сборка",
    "marking": "маркировка",
    "non-destructive testing (NDT)": "неразрушающий контроль",
}

STAGE_RU_MAP = {
    "roughing": "черновая обработка",
    "semi-finishing": "получистовая обработка",
    "finishing": "чистовая обработка",
    "quality-inspection": "контроль качества",
    "packaging": "упаковка",
}

EQUIPMENT_RU_MAP = {
    "lathe": "токарный станок",
    "cnc lathe": "токарный станок с ЧПУ",
    "milling machine": "фрезерный станок",
    "cnc milling machine": "фрезерный станок с ЧПУ",
    "machining center": "обрабатывающий центр",
    "drilling machine": "сверлильный станок",
    "cmm": "координатно-измерительная машина",
    "inspection equipment": "измерительное оборудование",
    "heat treatment furnace": "печь для термообработки",
    "grinding machine": "шлифовальный станок",
    "polishing machine": "полировальный станок",
    "deburring machine": "станок для удаления заусенцев",
    "packaging machine": "упаковочное оборудование",
    "coating machine": "оборудование для нанесения покрытия",
}

FINISHING_ACTIONS = {
    "grinding",
    "polishing",
    "lapping",
    "honing",
    "burnishing",
    "surface-coating",
    "marking",
    "non-destructive testing (NDT)",
}

SPECIAL_STAGE_ACTIONS = {
    "quality-inspection": "quality-inspection",
    "packaging": "packaging",
}

MACHINING_ACTIONS = {
    "turning",
    "facing",
    "boring",
    "threading",
    "drilling",
    "reaming",
    "milling",
    "slotting",
    "key-seating",
    "broaching",
    "heat-treatment",
    "deburring",
    "sand-blasting",
    "cutting-off",
    "knurling",
    "tapping",
    "electro-discharge machining (EDM)",
    "laser cutting",
    "waterjet cutting",
    "assembly",
}


@dataclass(frozen=True)
class MlGenerationResult:
    payload: dict[str, Any]
    raw_response: str
    provider: str
    model_name: str
    prompt_version: str


def generate_process_json_from_collage(
    *,
    collage_bytes: bytes,
    collage_file_name: str,
    collage_size: int,
    provider: str,
    model_name: str,
    prompt_version: str,
) -> MlGenerationResult:
    normalized_provider = provider.strip().lower()
    if normalized_provider == "stub":
        payload = build_stub_process_json(
            collage_file_name=collage_file_name,
            provider=normalized_provider,
            model_name=model_name,
            prompt_version=prompt_version,
        )
        if settings.ml_enable_ru_labels:
            payload = add_russian_labels(payload)
        return MlGenerationResult(
            payload=payload,
            raw_response=json.dumps(payload, ensure_ascii=False),
            provider=normalized_provider,
            model_name=model_name,
            prompt_version=prompt_version,
        )

    prompt = build_generation_prompt(collage_size=collage_size, collage_file_name=collage_file_name)
    raw_response = generate_raw_response(
        collage_bytes=collage_bytes,
        prompt=prompt,
        collage_file_name=collage_file_name,
        provider=normalized_provider,
        model_name=model_name,
    )
    parsed = safe_json_loads(raw_response)
    if parsed is None:
        raise ValueError("ML provider returned a response that is not valid JSON.")

    payload = normalize_process_json(parsed, fallback_file_name=collage_file_name)
    if settings.ml_enable_ru_labels:
        payload = add_russian_labels(payload)

    validation = validate_process_json(payload)
    payload["_validation"] = validation
    payload.setdefault("_normalization_debug", {})
    payload["_normalization_debug"]["validator_valid"] = validation["valid"]
    payload["_normalization_debug"]["validator_errors_count"] = len(validation["errors"])
    payload["_normalization_debug"]["validator_warnings_count"] = len(validation["warnings"])
    payload["_normalization_debug"]["validator_errors"] = validation["errors"]
    payload["_normalization_debug"]["validator_warnings"] = validation["warnings"]
    if not settings.ml_export_debug_fields:
        payload = strip_internal_fields(payload)

    return MlGenerationResult(
        payload=payload,
        raw_response=raw_response,
        provider=normalized_provider,
        model_name=model_name,
        prompt_version=prompt_version,
    )


def build_generation_prompt(*, collage_size: int, collage_file_name: str) -> str:
    prompt_path = PROMPTS_ROOT / f"prompt_{collage_size}.txt"
    if not prompt_path.exists():
        prompt_path = PROMPTS_ROOT / "prompt_6.txt"

    prompt = prompt_path.read_text(encoding="utf-8")
    prompt += f"\n\n[Image file: {collage_file_name}]"
    return prompt


def generate_raw_response(
    *,
    collage_bytes: bytes,
    prompt: str,
    collage_file_name: str,
    provider: str,
    model_name: str,
) -> str:
    if not settings.ml_enable_rag:
        return call_vlm_provider(
            collage_bytes=collage_bytes,
            prompt=prompt,
            provider=provider,
            model_name=model_name,
        )

    draft_prompt = (
        prompt
        + "\n\nFIRST PASS TASK:\n"
        + "Return ONLY valid JSON. Create a draft process where each step contains "
        + "Action and Equipment fields. Do NOT include ISO in this first pass "
        + "(use ISO: [] or omit ISO)."
    )
    draft_response = call_vlm_provider(
        collage_bytes=collage_bytes,
        prompt=draft_prompt,
        provider=provider,
        model_name=model_name,
    )

    draft_json = safe_json_loads(draft_response)
    if draft_json is not None:
        draft_json = normalize_process_json(draft_json, fallback_file_name=collage_file_name)
    steps = extract_steps(draft_json or {})

    if steps:
        step_rag_context = build_step_level_rag_context(steps, csv_path=EQUIPMENT_ISO_PATH)
        second_pass_prompt = (
            prompt
            + "\n\nSECOND PASS TASK:\n"
            + "Return ONLY valid JSON. Produce the final process JSON and fill ISO per "
            + "step using the STEP-LEVEL RAG CONTEXT below.\n\n"
            + step_rag_context
        )
        return call_vlm_provider(
            collage_bytes=collage_bytes,
            prompt=second_pass_prompt,
            provider=provider,
            model_name=model_name,
        )

    rag_rows = retrieve_relevant_data(
        query_text=f"{prompt}\n{collage_file_name}",
        csv_path=EQUIPMENT_ISO_PATH,
        top_k=20,
        dedup_by_iso=True,
    )
    fallback_prompt = prompt + "\n\n" + format_rag_prompt(rag_rows)
    return call_vlm_provider(
        collage_bytes=collage_bytes,
        prompt=fallback_prompt,
        provider=provider,
        model_name=model_name,
    )


def call_vlm_provider(
    *,
    collage_bytes: bytes,
    prompt: str,
    provider: str,
    model_name: str,
) -> str:
    image_url = f"data:image/png;base64,{base64.b64encode(collage_bytes).decode('ascii')}"

    if provider in {"mistral", "pixtral", "pixtral_12b"}:
        api_key = settings.ml_mistral_api_key
        if not api_key:
            raise ValueError("ML_MISTRAL_API_KEY is required for provider=mistral.")

        try:
            from mistralai import Mistral
        except ImportError:
            from mistralai.client import Mistral

        client = Mistral(api_key=api_key)
        response = client.chat.complete(
            model=model_name or "pixtral-12b-2409",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
        )
        return response.choices[0].message.content

    if provider in {"qwen", "dashscope", "qwen_vl_max", "qwen2_5_vl_72b"}:
        api_key = settings.ml_qwen_api_key
        if not api_key:
            raise ValueError("ML_QWEN_API_KEY is required for provider=qwen.")

        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=settings.ml_qwen_base_url)
        completion = client.chat.completions.create(
            model=model_name or "qwen-vl-max",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
        )
        return completion.choices[0].message.content

    if provider == "openai":
        api_key = settings.ml_openai_api_key
        if not api_key:
            raise ValueError("ML_OPENAI_API_KEY is required for provider=openai.")

        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
        )
        return completion.choices[0].message.content

    raise ValueError(f"Unsupported ML provider: {provider}.")


def retrieve_relevant_data(
    *,
    query_text: str,
    csv_path: Path,
    top_k: int,
    dedup_by_iso: bool = True,
) -> list[dict[str, Any]]:
    import numpy as np
    import pandas as pd
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    df = pd.read_csv(csv_path)

    def row_doc(row: Any) -> str:
        return " ".join(
            [
                str(row.get("Equipment category", "")),
                str(row.get("Equipment category ru", "")),
                str(row.get("Operation category", "")),
                str(row.get("Process stage", "")),
                str(row.get("Synonyms", "")),
                str(row.get("GOST", "")),
                str(row.get("Name of GOST", "")),
            ]
        )

    docs = df.apply(row_doc, axis=1).tolist()
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), lowercase=True)
    tfidf_matrix = vectorizer.fit_transform(docs)
    query_vec = vectorizer.transform([query_text + " machining manufacturing equipment"])
    cosine_scores = cosine_similarity(query_vec, tfidf_matrix).flatten()
    top_indices = np.argsort(cosine_scores)[-top_k:][::-1]
    relevant_rows = df.iloc[top_indices].copy()
    if dedup_by_iso and "ISO" in relevant_rows.columns:
        relevant_rows = relevant_rows.drop_duplicates(subset=["ISO"], keep="first")
    elif dedup_by_iso and "GOST" in relevant_rows.columns:
        relevant_rows = relevant_rows.drop_duplicates(subset=["GOST"], keep="first")
    return relevant_rows.to_dict(orient="records")


def format_rag_prompt(rows: list[dict[str, Any]]) -> str:
    lines = [
        "Use the GOST/ISO KB below when filling ISO fields.",
        "RAG RULES:",
        "- Use ONLY standards that appear in the list below.",
        "- Prefer Russian GOST/ISO titles from the KB when they are available.",
        "- For each step, pick at most 1-3 standards.",
        "- If no ISO is clearly relevant, leave the ISO field empty ([]) instead of guessing.",
        "STANDARD CANDIDATES:",
    ]
    for item in rows:
        lines.append(
            f"- Equipment: {item.get('Equipment category', '')}; "
            f"Equipment RU: {item.get('Equipment category ru', '')}; "
            f"Standard: {get_standard_code(item)}; "
            f"Title: {get_standard_title(item)}"
        )
    return "\n".join(lines)


def build_step_level_rag_context(
    steps: list[dict[str, Any]],
    *,
    csv_path: Path,
    max_rows_per_step: int = 5,
) -> str:
    blocks = [
        "STEP-LEVEL RAG CONTEXT (GOST/ISO candidates grouped per step):",
        "RAG RULES:",
        "- Use ONLY standards shown for the corresponding step.",
        "- Prefer Russian GOST/ISO titles from the KB when they are available.",
        "- For each step, choose at most 1-3 standards.",
        "- If uncertain, use [] for ISO.",
    ]

    for index, step in enumerate(steps, start=1):
        action = str(step.get("Action", "") or "").strip()
        stage = str(step.get("Stage", "") or "").strip()
        equipment = step.get("Equipment", [])
        if isinstance(equipment, list):
            equipment_text = " ".join(str(item).strip() for item in equipment if item)
        else:
            equipment_text = str(equipment).strip()

        query_parts = []
        if action:
            query_parts.append(f"operation {action}")
        if stage:
            query_parts.append(f"stage {stage}")
        if equipment_text:
            query_parts.append(f"equipment {equipment_text}")
        query = ". ".join(query_parts) or "machining operation equipment"

        rows = retrieve_relevant_data(
            query_text=query,
            csv_path=csv_path,
            top_k=max_rows_per_step,
            dedup_by_iso=True,
        )
        filtered_rows = filter_rag_rows(rows, action=action, stage=stage)
        if filtered_rows:
            rows = filtered_rows

        blocks.append(f"\nSTEP {index} QUERY:\n{query}")
        blocks.append("STANDARD CANDIDATES:")
        if not rows:
            blocks.append("- No candidates found")
            continue

        for item in rows:
            blocks.append(
                f"- Standard: {get_standard_code(item)}; "
                f"Equipment: {item.get('Equipment category', '')}; "
                f"Equipment RU: {item.get('Equipment category ru', '')}; "
                f"Title: {get_standard_title(item)}"
            )

    return "\n".join(blocks)


def filter_rag_rows(
    rows: list[dict[str, Any]],
    *,
    action: str,
    stage: str,
) -> list[dict[str, Any]]:
    filtered = []
    for item in rows:
        row_text = " ".join(
            [
                str(item.get("Equipment category", "")),
                str(item.get("Equipment category ru", "")),
                str(item.get("Operation category", "")),
                str(item.get("Process stage", "")),
                str(item.get("Name of GOST", "")),
                str(item.get("Name of ISO", "")),
            ]
        ).lower()
        action_ok = action.lower() in row_text if action else True
        stage_ok = stage.lower() in row_text if stage else True
        if action_ok and stage_ok:
            filtered.append(item)
    return filtered


def get_standard_code(row: dict[str, Any]) -> str:
    return str(row.get("ISO") or row.get("GOST") or row.get("Standard") or "")


def get_standard_title(row: dict[str, Any]) -> str:
    return str(
        row.get("Name of ISO")
        or row.get("Name of GOST")
        or row.get("Standard name")
        or ""
    )


def safe_json_loads(text: str) -> dict[str, Any] | None:
    cleaned = clean_json_text(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def clean_json_text(text: str) -> str:
    cleaned = str(text or "").strip()
    cleaned = cleaned.replace("```JSON", "```").replace("```json", "```")
    cleaned = re.sub(r"^\s*json\s*\n", "", cleaned, flags=re.IGNORECASE)
    if "```" in cleaned:
        parts = cleaned.split("```")
        if len(parts) >= 3:
            cleaned = parts[1].strip()
        else:
            cleaned = cleaned.replace("```", "").strip()
    return cleaned.strip()


def normalize_process_json(data: dict[str, Any], *, fallback_file_name: str) -> dict[str, Any]:
    normalized = dict(data)
    normalized["File name"] = str(
        data.get("File name") or data.get("file_name") or fallback_file_name
    ).strip()
    normalized["Name of operation"] = str(
        data.get("Name of operation") or data.get("name_of_operation") or "Manufacturing Process"
    ).strip()

    raw_steps = extract_steps(data)
    steps = []
    for index, step in enumerate(raw_steps, start=1):
        steps.append(normalize_step(step, index))
    steps = repair_missing_stages(steps)
    normalized["Steps"] = steps
    return normalized


def extract_steps(data: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("Steps", "steps", "operations", "Operations"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def normalize_step(step: dict[str, Any], index: int) -> dict[str, Any]:
    try:
        step_number = int(step.get("Step number", step.get("step_number", index)))
    except (TypeError, ValueError):
        step_number = index

    raw_action = step.get("Action", step.get("action", ""))
    raw_stage = step.get("Stage", step.get("stage", ""))
    equipment = step.get("Equipment", step.get("equipment", []))
    if not isinstance(equipment, list):
        equipment = [equipment] if equipment else []

    iso = step.get("ISO", step.get("iso", []))
    if not isinstance(iso, list):
        iso = [iso] if iso else []

    return {
        "Step number": step_number,
        "Stage": normalize_stage(raw_stage) or normalize_stage(raw_action),
        "Action": normalize_action(raw_action),
        "Equipment": deduplicate([normalize_equipment(item) for item in equipment]),
        "ISO": [str(item).strip() for item in iso if str(item).strip()],
    }


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_action(value: Any) -> str:
    original_raw = normalize_text(value)
    raw = strip_stage_words_from_action(value)
    if not raw:
        stage = normalize_stage(original_raw)
        if stage in {"quality-inspection", "packaging"}:
            return stage
        return ""

    action_aliases = {
        "turning": ["turning", "turn", "turning operation"],
        "facing": ["facing", "face machining", "face"],
        "boring": ["boring", "bore machining", "bore"],
        "threading": ["threading", "thread cutting", "thread"],
        "drilling": ["drilling", "drill", "drilling operation"],
        "reaming": ["reaming", "ream"],
        "milling": ["milling", "mill", "milling operation"],
        "slotting": ["slotting", "slot cutting", "slot machining"],
        "key-seating": ["key-seating", "key seating", "keyseat", "keyway machining"],
        "broaching": ["broaching", "broach"],
        "heat-treatment": ["heat-treatment", "heat treatment", "tempering", "annealing"],
        "deburring": ["deburring", "deburr", "remove burrs", "burr removal"],
        "sand-blasting": ["sand-blasting", "sand blasting", "blasting"],
        "grinding": ["grinding", "grind"],
        "polishing": ["polishing", "polish"],
        "quality-inspection": ["quality-inspection", "quality inspection", "inspection", "qc"],
        "surface-coating": ["surface-coating", "surface coating", "coating"],
        "packaging": ["packaging", "packing", "package"],
        "cutting-off": ["cutting-off", "cutting off", "cutoff", "cut off"],
        "knurling": ["knurling", "knurl"],
        "tapping": ["tapping", "tap threading", "tap"],
        "lapping": ["lapping", "lap finishing", "lap"],
        "honing": ["honing", "hone"],
        "burnishing": ["burnishing", "burnish"],
        "electro-discharge machining (EDM)": ["electro-discharge machining", "edm"],
        "laser cutting": ["laser cutting", "laser cut"],
        "waterjet cutting": ["waterjet cutting", "waterjet cut"],
        "assembly": ["assembly", "assemble"],
        "marking": ["marking", "mark"],
        "non-destructive testing (NDT)": ["non-destructive testing", "ndt"],
    }
    for canonical, aliases in action_aliases.items():
        for alias in sorted(aliases, key=len, reverse=True):
            if alias in raw:
                return canonical
    return raw.strip()


def normalize_equipment(equipment: Any) -> str:
    if isinstance(equipment, list):
        equipment = " ".join(str(item) for item in equipment)

    raw = normalize_text(equipment)
    equipment_aliases = {
        "lathe machine": "lathe",
        "cnc lathe machine": "cnc lathe",
        "turning center": "cnc lathe",
        "turning centre": "cnc lathe",
        "cnc turning center": "cnc lathe",
        "cnc turning centre": "cnc lathe",
        "milling machine": "milling machine",
        "cnc milling machine": "cnc milling machine",
        "machining center": "machining center",
        "machining centre": "machining center",
        "cnc machining center": "machining center",
        "cnc machining centre": "machining center",
        "drill press": "drilling machine",
        "drill press machine": "drilling machine",
        "drilling machine": "drilling machine",
        "coordinate measuring machine": "cmm",
        "coordinate measuring machine (cmm)": "cmm",
        "cmm": "cmm",
        "inspection station": "inspection equipment",
        "inspection equipment": "inspection equipment",
        "heat treatment furnace": "heat treatment furnace",
        "heat-treatment furnace": "heat treatment furnace",
        "grinding machine": "grinding machine",
        "polishing machine": "polishing machine",
        "deburring machine": "deburring machine",
        "packaging machine": "packaging machine",
        "coating machine": "coating machine",
    }
    return equipment_aliases.get(raw, raw)


def normalize_stage(value: Any) -> str:
    raw = normalize_text(value)
    if not raw:
        return ""

    stage_aliases = [
        ("quality-inspection", ["quality-inspection", "quality inspection", "inspection", "qc"]),
        ("packaging", ["packaging", "packing", "package", "final packaging"]),
        ("semi-finishing", ["semi-finishing", "semi finishing", "semi-finish"]),
        ("finishing", ["finishing", "finish", "final machining", "final pass"]),
        ("roughing", ["roughing", "rough", "rough machining", "initial machining"]),
    ]
    for canonical, aliases in stage_aliases:
        if any(alias in raw for alias in aliases):
            return canonical
    return ""


def strip_stage_words_from_action(value: Any) -> str:
    text = normalize_text(value)
    stage_noise = [
        "roughing",
        "rough machining",
        "rough pass",
        "rough",
        "semi-finishing",
        "semi finishing",
        "semi-finish",
        "finishing",
        "finish pass",
        "final machining",
        "final pass",
        "finish",
        "quality-inspection",
        "quality inspection",
        "quality control",
        "inspection",
        "packaging",
        "packing",
        "package",
    ]
    for noise in stage_noise:
        text = text.replace(noise, " ")
    return " ".join(text.split())


def deduplicate(items: list[str]) -> list[str]:
    result = []
    seen = set()
    for item in items:
        item = str(item or "").strip()
        key = item.lower()
        if item and key not in seen:
            result.append(item)
            seen.add(key)
    return result


def repair_missing_stages(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not steps:
        return steps

    repaired = [dict(step) for step in steps]
    machining_indices: list[int] = []

    for step in repaired:
        action = str(step.get("Action", "") or "").strip()
        stage = str(step.get("Stage", "") or "").strip()
        if action in SPECIAL_STAGE_ACTIONS and stage != SPECIAL_STAGE_ACTIONS[action]:
            step["Stage"] = SPECIAL_STAGE_ACTIONS[action]
        elif not stage and action in FINISHING_ACTIONS:
            step["Stage"] = "finishing"

    for index, step in enumerate(repaired):
        action = str(step.get("Action", "") or "").strip()
        stage = str(step.get("Stage", "") or "").strip()
        if stage in {"quality-inspection", "packaging"}:
            continue
        if action in MACHINING_ACTIONS or action in FINISHING_ACTIONS:
            machining_indices.append(index)

    total = len(machining_indices)
    for position, index in enumerate(machining_indices):
        if repaired[index].get("Stage"):
            continue
        action = str(repaired[index].get("Action", "") or "").strip()
        if action in FINISHING_ACTIONS or total == 1:
            assigned_stage = "finishing"
        elif total == 2:
            assigned_stage = "roughing" if position == 0 else "finishing"
        elif position == 0:
            assigned_stage = "roughing"
        elif position == total - 1:
            assigned_stage = "finishing"
        elif position / max(total - 1, 1) <= 0.34:
            assigned_stage = "roughing"
        elif position / max(total - 1, 1) <= 0.80:
            assigned_stage = "semi-finishing"
        else:
            assigned_stage = "finishing"
        repaired[index]["Stage"] = assigned_stage

    if not any(step.get("Stage") == "quality-inspection" for step in repaired):
        repaired.append(
            {
                "Step number": len(repaired) + 1,
                "Stage": "quality-inspection",
                "Action": "quality-inspection",
                "Equipment": ["inspection equipment"],
                "ISO": [],
            }
        )

    if not any(step.get("Stage") == "packaging" for step in repaired):
        repaired.append(
            {
                "Step number": len(repaired) + 1,
                "Stage": "packaging",
                "Action": "packaging",
                "Equipment": ["packaging equipment"],
                "ISO": [],
            }
        )

    for index, step in enumerate(repaired, start=1):
        step["Step number"] = index

    return repaired


def validate_process_json(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    steps = data.get("Steps", [])
    if not isinstance(steps, list) or not steps:
        errors.append("No steps found")
        return {"valid": False, "errors": errors, "warnings": warnings}

    stage_order = {
        "roughing": 0,
        "semi-finishing": 1,
        "finishing": 2,
        "quality-inspection": 3,
        "packaging": 4,
    }
    action_equipment_rules = {
        "turning": ["lathe"],
        "facing": ["lathe"],
        "threading": ["lathe"],
        "knurling": ["lathe"],
        "boring": ["boring", "lathe"],
        "drilling": ["drilling", "drill"],
        "reaming": ["reaming", "drilling", "drill"],
        "milling": ["milling", "machining center", "machining centre"],
        "slotting": ["slotting", "milling", "machining center", "machining centre"],
        "key-seating": ["key", "slotting", "milling", "machining center", "machining centre"],
        "broaching": ["broaching"],
        "grinding": ["grinding"],
        "polishing": ["polishing"],
        "deburring": ["deburring"],
        "heat-treatment": ["heat"],
        "quality-inspection": ["inspection", "measuring", "cmm", "coordinate"],
        "surface-coating": ["coating"],
        "packaging": ["packaging", "packing"],
        "cutting-off": ["cutting", "saw", "lathe"],
        "tapping": ["tapping", "drilling", "drill"],
        "lapping": ["lapping"],
        "honing": ["honing"],
        "burnishing": ["burnishing"],
        "electro-discharge machining (EDM)": ["edm", "electro-discharge"],
        "laser cutting": ["laser"],
        "waterjet cutting": ["waterjet"],
        "assembly": ["assembly"],
        "marking": ["marking"],
        "non-destructive testing (NDT)": ["ndt", "inspection", "testing"],
    }

    found_stages = set()
    prev_stage_order = -1
    for index, step in enumerate(steps, start=1):
        action = str(step.get("Action", "") or "").strip()
        stage = str(step.get("Stage", "") or "").strip()
        equipment = step.get("Equipment", [])
        equipment_list = equipment if isinstance(equipment, list) else [equipment]
        equipment_text = " ".join(str(item).strip() for item in equipment_list).lower()

        if not action:
            errors.append(f"Step {index}: missing Action")
        elif action not in ALLOWED_ACTIONS:
            errors.append(f"Step {index}: unknown Action '{action}'")

        if not stage:
            errors.append(f"Step {index}: missing Stage")
        else:
            found_stages.add(stage)
            if stage not in stage_order:
                errors.append(f"Step {index}: unknown Stage '{stage}'")
            else:
                current_order = stage_order[stage]
                if current_order < prev_stage_order:
                    warnings.append(f"Step {index}: stage order looks suspicious")
                prev_stage_order = max(prev_stage_order, current_order)

        if not equipment:
            warnings.append(f"Step {index}: missing Equipment")

        if action in action_equipment_rules and equipment_text:
            allowed_markers = action_equipment_rules[action]
            if not any(marker in equipment_text for marker in allowed_markers):
                warnings.append(f"Step {index}: possible equipment mismatch for action '{action}'")

    for required_stage in ("quality-inspection", "packaging"):
        if required_stage not in found_stages:
            errors.append(f"Missing required stage: {required_stage}")

    for recommended_stage in ("roughing", "finishing"):
        if recommended_stage not in found_stages:
            warnings.append(f"Missing recommended stage: {recommended_stage}")

    if "semi-finishing" not in found_stages:
        warnings.append("Missing optional stage: semi-finishing")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def add_russian_labels(data: dict[str, Any]) -> dict[str, Any]:
    result = dict(data)
    operation_name = str(result.get("Name of operation", "") or "").strip()
    operation_name_ru_map = {
        "manufacturing process": "Технологический маршрут обработки",
        "machining process": (
            "Технологический маршрут механической обработки"
        ),
        "production process": "Производственный процесс",
    }
    result["Name of operation RU"] = operation_name_ru_map.get(
        operation_name.lower(),
        operation_name or "Технологический маршрут обработки",
    )

    steps = result.get("Steps", [])
    if not isinstance(steps, list):
        return result

    localized_steps = []
    for step in steps:
        if not isinstance(step, dict):
            localized_steps.append(step)
            continue

        localized_step = dict(step)
        action = str(localized_step.get("Action", "") or "").strip()
        stage = str(localized_step.get("Stage", "") or "").strip()
        equipment = localized_step.get("Equipment", [])

        localized_step["Action RU"] = ACTION_RU_MAP.get(action, action)
        localized_step["Stage RU"] = STAGE_RU_MAP.get(stage, stage)
        localized_step["Equipment RU"] = translate_equipment_to_ru(equipment)
        localized_steps.append(localized_step)

    result["Steps"] = localized_steps
    return result


def translate_equipment_to_ru(equipment: Any) -> list[str]:
    items = equipment if isinstance(equipment, list) else ([equipment] if equipment else [])
    translated = []
    for item in items:
        key = normalize_equipment(item)
        ru = EQUIPMENT_RU_MAP.get(key, str(item).strip())
        if ru:
            translated.append(ru)
    return deduplicate(translated)


def strip_internal_fields(data: dict[str, Any]) -> dict[str, Any]:
    result = dict(data)
    result.pop("_normalization_debug", None)
    result.pop("_validation", None)
    return result


def build_stub_process_json(
    *,
    collage_file_name: str,
    provider: str,
    model_name: str,
    prompt_version: str,
) -> dict[str, Any]:
    return {
        "File name": collage_file_name,
        "Name of operation": "Manufacturing Process",
        "Steps": [
            {
                "Step number": 1,
                "Stage": "roughing",
                "Action": "milling",
                "Equipment": ["machining center"],
                "ISO": [],
            },
            {
                "Step number": 2,
                "Stage": "quality-inspection",
                "Action": "quality-inspection",
                "Equipment": ["inspection equipment"],
                "ISO": [],
            },
            {
                "Step number": 3,
                "Stage": "packaging",
                "Action": "packaging",
                "Equipment": ["packaging equipment"],
                "ISO": [],
            },
        ],
        "_meta": {
            "provider": provider,
            "model_name": model_name,
            "prompt_version": prompt_version,
            "status": "stub_generated",
        },
    }
