import base64
import json
import os
import pickle
import re
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional
from mistralai.client import Mistral
from openai import OpenAI
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


run_mistral_model = os.getenv("RUN_MISTRAL", "false").lower() == "true"
run_qwen_72b_model = os.getenv("RUN_QWEN_72B", "false").lower() == "true"
run_qwen_vl_max_model = os.getenv("RUN_QWEN_VL_MAX", "true").lower() == "true"

run_rag = os.getenv("RUN_RAG", "true").lower() == "true"
run_no_rag = os.getenv("RUN_NO_RAG", "false").lower() == "true"

type_names = []
if run_no_rag:
    type_names.append("results_no_rag")
if run_rag:
    type_names.append("results_rag")


prompt_path3 = "./example_material/prompts/prompt_3.txt"
prompt_path4 = "./example_material/prompts/prompt_4.txt"
prompt_path6 = "./example_material/prompts/prompt_6.txt"

DEBUG_NORMALIZATION = False
DEBUG_PROMPTS = False
DEBUG_PROMPTS_DIR = "./debug_prompts"

ENABLE_RU_LABELS = True
EXPORT_DEBUG_FIELDS = False

ALLOWED_ACTIONS = {
    "turning", "facing", "boring", "threading", "drilling", "reaming",
    "milling", "slotting", "key-seating", "broaching", "heat-treatment",
    "deburring", "sand-blasting", "grinding", "polishing",
    "quality-inspection", "surface-coating", "packaging", "cutting-off",
    "knurling", "tapping", "lapping", "honing", "burnishing",
    "electro-discharge machining (EDM)", "laser cutting", "waterjet cutting",
    "assembly", "marking", "non-destructive testing (NDT)"
}


ACTION_RU_MAP = {
    "turning": "точение",
    "facing": "торцевание",
    "boring": "растачивание",
    "threading": "нарезание резьбы",
    "drilling": "сверление",
    "reaming": "развёртывание",
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
    "band saw": "ленточнопильный станок",
    "turning tools": "токарные резцы",
    "boring bar": "расточная оправка",
    "drill bit": "сверло",
    "reamer": "развёртка",
    "5-axis cnc milling machine": "5-осевой фрезерный станок с ЧПУ",
    "end mills": "концевые фрезы",
    "slotting cutter": "пазовая фреза",
    "broaching machine": "протяжной станок",
    "broach tool": "протяжка",
    "tap": "метчик",
    "die": "плашка",
    "industrial furnace": "промышленная печь",
    "quenching bath": "закалочная ванна",
    "surface grinder": "плоскошлифовальный станок",
    "cylindrical grinder": "круглошлифовальный станок",
    "honing machine": "хонинговальный станок",
    "lapping machine": "доводочный станок",
    "manual deburring tools": "ручной инструмент для удаления заусенцев",
    "automated deburring machine": "автоматизированный станок для удаления заусенцев",
    "sand-blast cabinet": "пескоструйная камера",
    "burnishing tool": "выглаживающий инструмент",
    "edm machine": "электроэрозионный станок",
    "ultrasonic tester": "ультразвуковой дефектоскоп",
    "magnetic particle inspection": "оборудование магнитопорошкового контроля",
    "calipers": "штангенциркуль",
    "micrometers": "микрометры",
    "plasma spray coating system": "установка плазменного напыления",
    "laser marking machine": "лазерный маркиратор",
    "assembly fixture": "сборочное приспособление",
    "torque wrench": "динамометрический ключ",
    "vacuum sealer": "вакуумный упаковщик",
    "packaging box": "упаковочная коробка",
    "cad/cam software": "CAD/CAM-система",
    "computer": "компьютер",
    "cnc lathe": "токарный станок с ЧПУ",
    "cnc milling machine": "фрезерный станок с ЧПУ",
    "cmm": "координатно-измерительная машина",
    "manual deburring tool": "ручной инструмент для удаления заусенцев",
    "laser marker": "лазерный маркиратор",
    "manual packaging station": "участок ручной упаковки",
}


def _save_debug_text(path: str, text: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(str(text))


def _build_debug_run_id():
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")


DEBUG_RUN_ID = _build_debug_run_id() if DEBUG_PROMPTS else None


def _debug_prompt_dir(model_name: str, data_type: str, image_path: str) -> str:
    part_id = os.path.splitext(os.path.basename(image_path))[0]
    return os.path.join(DEBUG_PROMPTS_DIR, DEBUG_RUN_ID, model_name, data_type, part_id)


def validate_process_json(data: dict) -> dict:
    errors = []
    warnings = []

    if not isinstance(data, dict):
        return {
            "valid": False,
            "errors": ["Input is not a dictionary"],
            "warnings": []
        }

    steps = data.get("Steps", [])
    if not isinstance(steps, list) or not steps:
        return {
            "valid": False,
            "errors": ["No steps found"],
            "warnings": []
        }

    required_hard_stages = {
        "quality-inspection",
        "packaging",
    }

    recommended_stages = {
        "roughing",
        "finishing",
    }

    optional_stages = {
        "semi-finishing",
    }

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
        "drilling": ["drilling", "drill", "milling machine", "cnc milling machine"],
        "reaming": ["reaming", "reamer", "milling machine", "cnc milling machine"],
        "milling": ["milling", "machining center", "machining centre"],
        "slotting": ["slotting", "milling", "machining center", "machining centre"],
        "key-seating": ["key", "slotting", "milling", "machining center", "machining centre"],
        "broaching": ["broaching"],
        "grinding": ["grinding", "grinder"],
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
        "marking": ["marking", "marker", "laser marker"],
        "non-destructive testing (NDT)": ["ndt", "inspection", "testing"],
    }

    found_stages = set()
    prev_stage_order = -1

    for idx, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            errors.append(f"Step {idx}: step is not a dictionary")
            continue

        action = str(step.get("Action", "") or "").strip()
        stage = str(step.get("Stage", "") or "").strip()
        equipment = step.get("Equipment", [])
        iso_values = step.get("ISO", [])

        if isinstance(equipment, list):
            equipment_list = [str(x).strip() for x in equipment if str(x).strip()]
            equipment_text = " ".join(equipment_list).lower()
        else:
            equipment_list = [str(equipment).strip()] if str(equipment).strip() else []
            equipment_text = " ".join(equipment_list).lower()

        if not action:
            errors.append(f"Step {idx}: missing Action")

        if not stage:
            errors.append(f"Step {idx}: missing Stage")

        if not equipment_list:
            warnings.append(f"Step {idx}: missing Equipment")

        if action and action not in ALLOWED_ACTIONS:
            errors.append(f"Step {idx}: unknown Action '{action}'")

        if stage:
            found_stages.add(stage)

            if stage not in stage_order:
                errors.append(f"Step {idx}: unknown Stage '{stage}'")
            else:
                current_order = stage_order[stage]
                if current_order < prev_stage_order:
                    warnings.append(
                        f"Step {idx}: stage order looks suspicious ('{stage}' appears after a later stage)"
                    )
                prev_stage_order = max(prev_stage_order, current_order)

        if action in action_equipment_rules and equipment_text:
            allowed_markers = action_equipment_rules[action]
            if not any(marker in equipment_text for marker in allowed_markers):
                warnings.append(
                    f"Step {idx}: possible equipment mismatch for action '{action}' -> '{equipment_text}'"
                )

        if iso_values is None:
            iso_values = []
        if not isinstance(iso_values, list):
            warnings.append(f"Step {idx}: ISO should be a list")

    missing_hard = required_hard_stages - found_stages
    for stage in sorted(missing_hard):
        errors.append(f"Missing required stage: {stage}")

    missing_recommended = recommended_stages - found_stages
    for stage in sorted(missing_recommended):
        warnings.append(f"Missing recommended stage: {stage}")

    missing_optional = optional_stages - found_stages
    for stage in sorted(missing_optional):
        warnings.append(f"Missing optional stage: {stage}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def _normalize_text(s):
    return str(s or "").strip().lower()


def _normalize_action(value: Any) -> str:
    original_raw = _normalize_text(value)
    raw = _strip_stage_words_from_action(value)

    if not raw:
        if _normalize_stage(original_raw) == "quality-inspection":
            return "quality-inspection"
        if _normalize_stage(original_raw) == "packaging":
            return "packaging"
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
        "key-seating": ["key-seating", "key seating", "keyseat", "keyway machining", "keyway cutting"],
        "broaching": ["broaching", "broach"],
        "heat-treatment": ["heat-treatment", "heat treatment", "tempering", "annealing", "quenching"],
        "deburring": ["deburring", "deburr", "remove burrs", "burr removal"],
        "sand-blasting": ["sand-blasting", "sand blasting", "blasting"],
        "grinding": ["grinding", "grind"],
        "polishing": ["polishing", "polish"],
        "quality-inspection": ["quality-inspection", "quality inspection", "inspection", "quality control", "qc"],
        "surface-coating": ["surface-coating", "surface coating", "coating"],
        "packaging": ["packaging", "packing", "package"],
        "cutting-off": ["cutting-off", "cutting off", "cutoff", "cut off"],
        "knurling": ["knurling", "knurl"],
        "tapping": ["tapping", "tap threading", "tap"],
        "lapping": ["lapping", "lap finishing", "lap"],
        "honing": ["honing", "hone"],
        "burnishing": ["burnishing", "burnish"],
        "electro-discharge machining (EDM)": [
            "electro-discharge machining", "edm", "spark erosion"
        ],
        "laser cutting": ["laser cutting", "laser cut"],
        "waterjet cutting": ["waterjet cutting", "waterjet cut"],
        "assembly": ["assembly", "assemble"],
        "marking": ["marking", "mark"],
        "non-destructive testing (NDT)": [
            "non-destructive testing", "ndt", "nondestructive testing"
        ],
    }

    for canonical, aliases in action_aliases.items():
        for alias in sorted(aliases, key=len, reverse=True):
            if alias in raw:
                return canonical

    return raw.strip()


def _normalize_equipment(equipment):
    if isinstance(equipment, list):
        equipment = " ".join(str(x) for x in equipment)

    raw = _normalize_text(equipment)

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

    if raw in equipment_aliases:
        return equipment_aliases[raw]

    return raw


def _normalize_stage(value: Any) -> str:
    raw = _normalize_text(value)

    if not raw:
        return ""

    stage_aliases = [
        ("quality-inspection", [
            "quality-inspection", "quality inspection", "inspection",
            "quality control", "quality-check", "quality check",
            "qc", "final inspection", "dimensional inspection",
            "measurement", "metrology", "final check"
        ]),
        ("packaging", [
            "packaging", "packing", "package", "final packaging"
        ]),
        ("semi-finishing", [
            "semi-finishing", "semi finishing", "semi-finish",
            "semifinishing", "semifinish", "semi finish"
        ]),
        ("finishing", [
            "finishing", "finish", "final machining",
            "final pass", "finish pass", "final turning",
            "final milling", "final grinding", "final polishing"
        ]),
        ("roughing", [
            "roughing", "rough", "rough machining",
            "rough pass", "rough turning", "rough milling",
            "rough drilling", "initial machining", "primary machining"
        ]),
    ]

    for canonical, aliases in stage_aliases:
        for alias in aliases:
            if alias in raw:
                return canonical

    return ""


def _strip_stage_words_from_action(value: Any) -> str:
    text = _normalize_text(value)

    if not text:
        return ""

    stage_noise = [
        "roughing", "rough machining", "rough pass", "rough",
        "semi-finishing", "semi finishing", "semi-finish", "semifinishing", "semi finish",
        "finishing", "finish pass", "final machining", "final pass", "finishing", "finish",
        "quality-inspection", "quality inspection", "quality control", "quality-check", "quality check",
        "final inspection", "inspection",
        "packaging", "packing", "package"
    ]

    cleaned = text
    for noise in stage_noise:
        cleaned = cleaned.replace(noise, " ")

    cleaned = " ".join(cleaned.split())
    return cleaned


def normalize_step(step: Dict[str, Any], step_index: int) -> Dict[str, Any]:
    if not isinstance(step, dict):
        return {
            "Step number": step_index,
            "Stage": "",
            "Action": "",
            "Equipment": [],
            "ISO": [],
        }

    raw_action = step.get("Action", step.get("action", ""))
    raw_equipment = step.get("Equipment", step.get("equipment", []))
    raw_iso = step.get("ISO", step.get("iso", []))
    raw_stage = step.get("Stage", step.get("stage", ""))

    explicit_stage = _normalize_stage(raw_stage)
    inferred_stage_from_action = _normalize_stage(raw_action)
    normalized_stage = explicit_stage or inferred_stage_from_action

    normalized_action = _normalize_action(raw_action)

    equipment_text_for_action = (
        " ".join(str(x) for x in raw_equipment)
        if isinstance(raw_equipment, list)
        else str(raw_equipment or "")
    ).lower()

    if normalized_action not in ALLOWED_ACTIONS or normalized_action == "facing":
        if "reamer" in equipment_text_for_action:
            normalized_action = "reaming"
        elif "honing" in equipment_text_for_action:
            normalized_action = "honing"
        elif "slotting" in equipment_text_for_action or "slotting cutter" in equipment_text_for_action:
            normalized_action = "slotting"
        elif "knurling" in equipment_text_for_action:
            normalized_action = "knurling"
        elif "cmm" in equipment_text_for_action or "coordinate measuring" in equipment_text_for_action:
            normalized_action = "quality-inspection"
        elif "packaging" in equipment_text_for_action or "vacuum sealer" in equipment_text_for_action:
            normalized_action = "packaging"
        elif "grinder" in equipment_text_for_action or "grinding" in equipment_text_for_action:
            normalized_action = "grinding"
        elif "lapping" in equipment_text_for_action:
            normalized_action = "lapping"
        elif "honing" in equipment_text_for_action:
            normalized_action = "honing"
        elif "polishing" in equipment_text_for_action or "abrasive pad" in equipment_text_for_action:
            normalized_action = "polishing"
        elif "burnishing" in equipment_text_for_action:
            normalized_action = "burnishing"
        elif "sand-blast" in equipment_text_for_action or "sandblast" in equipment_text_for_action:
            normalized_action = "sand-blasting"
        elif "coating" in equipment_text_for_action or "plasma spray" in equipment_text_for_action:
            normalized_action = "surface-coating"

    if isinstance(raw_equipment, list):
        equipment_list = [str(x).strip() for x in raw_equipment if str(x).strip()]
    elif raw_equipment:
        equipment_list = [str(raw_equipment).strip()]
    else:
        equipment_list = []

    normalized_equipment = []
    for eq in equipment_list:
        norm_eq = _normalize_equipment(eq)
        if norm_eq:
            normalized_equipment.append(norm_eq)

    dedup_equipment = []
    seen_eq = set()
    for eq in normalized_equipment:
        key = eq.lower()
        if key not in seen_eq:
            dedup_equipment.append(eq)
            seen_eq.add(key)

    if isinstance(raw_iso, list):
        iso_list = [str(x).strip() for x in raw_iso if str(x).strip()]
    elif raw_iso:
        iso_list = [str(raw_iso).strip()]
    else:
        iso_list = []

    dedup_iso = []
    seen_iso = set()
    for item in iso_list:
        key = item.lower()
        if key not in seen_iso:
            dedup_iso.append(item)
            seen_iso.add(key)

    step_number = step.get("Step number", step.get("step_number", step_index))
    try:
        step_number = int(step_number)
    except Exception:
        step_number = step_index

    normalized_step = {
        "Step number": step_number,
        "Stage": normalized_stage,
        "Action": normalized_action,
        "Equipment": dedup_equipment,
        "ISO": dedup_iso,
    }

    skip_keys = {"Step number", "step_number", "Stage", "stage", "Action", "action", "Equipment", "equipment", "ISO", "iso"}
    for key, value in step.items():
        if key not in skip_keys:
            normalized_step[key] = value

    return normalized_step


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


def repair_missing_stages(steps: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not isinstance(steps, list) or not steps:
        return steps, {
            "had_missing_stage_repairs": False,
            "repaired_steps_count": 0,
            "repaired_step_numbers": [],
        }

    repaired = [dict(step) if isinstance(step, dict) else {} for step in steps]
    repaired_step_numbers = []

    # 1. Жёстко выставляем стадии для специальных действий
    for step in repaired:
        action = str(step.get("Action", "") or "").strip()
        stage = str(step.get("Stage", "") or "").strip()

        if action in SPECIAL_STAGE_ACTIONS and stage != SPECIAL_STAGE_ACTIONS[action]:
            step["Stage"] = SPECIAL_STAGE_ACTIONS[action]
            repaired_step_numbers.append(step.get("Step number"))
        elif not stage and action in FINISHING_ACTIONS:
            step["Stage"] = "finishing"
            repaired_step_numbers.append(step.get("Step number"))

    # 2. Собираем индексы machining steps без специальных финальных стадий
    machining_indices = []
    for idx, step in enumerate(repaired):
        action = str(step.get("Action", "") or "").strip()
        stage = str(step.get("Stage", "") or "").strip()

        if stage in {"quality-inspection", "packaging"}:
            continue

        if action in MACHINING_ACTIONS or action in FINISHING_ACTIONS:
            machining_indices.append(idx)

    # 3. Для шагов без Stage распределяем roughing / semi-finishing / finishing
    if machining_indices:
        total = len(machining_indices)

        for pos, idx in enumerate(machining_indices):
            step = repaired[idx]
            current_stage = str(step.get("Stage", "") or "").strip()
            action = str(step.get("Action", "") or "").strip()

            if current_stage:
                continue

            assigned_stage = ""

            if action in FINISHING_ACTIONS:
                assigned_stage = "finishing"
            elif total == 1:
                assigned_stage = "finishing"
            elif total == 2:
                assigned_stage = "roughing" if pos == 0 else "finishing"
            else:
                if pos == 0:
                    assigned_stage = "roughing"
                elif pos == total - 1:
                    assigned_stage = "finishing"
                else:
                    ratio = pos / (total - 1)
                    if ratio <= 0.34:
                        assigned_stage = "roughing"
                    elif ratio <= 0.80:
                        assigned_stage = "semi-finishing"
                    else:
                        assigned_stage = "finishing"

            if assigned_stage:
                step["Stage"] = assigned_stage
                repaired_step_numbers.append(step.get("Step number"))

    repaired_step_numbers = [x for x in repaired_step_numbers if x is not None]
    repaired_step_numbers = list(dict.fromkeys(repaired_step_numbers))

    debug_info = {
        "had_missing_stage_repairs": len(repaired_step_numbers) > 0,
        "repaired_steps_count": len(repaired_step_numbers),
        "repaired_step_numbers": repaired_step_numbers,
    }

    return repaired, debug_info


def normalize_process_json(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {
            "File name": "",
            "Name of operation": "",
            "Steps": [],
        }

    normalized = dict(data)

    file_name = data.get("File name", data.get("file_name", ""))
    operation_name = data.get("Name of operation", data.get("name_of_operation", ""))

    normalized["File name"] = str(file_name).strip()
    normalized["Name of operation"] = str(operation_name).strip()

    raw_steps = _extract_steps_for_rag(data)
    normalized_steps = []

    def _is_non_machining_planning_step(step: Dict[str, Any]) -> bool:
        if not isinstance(step, dict):
            return False

        text = " ".join([
            str(step.get("Action", "")),
            " ".join(str(x) for x in step.get("Equipment", [])) if isinstance(step.get("Equipment", []), list) else str(step.get("Equipment", "")),
        ]).lower()

        planning_markers = [
            "cad/cam",
            "cad cam",
            "computer",
            "analyzing",
            "analysing",
            "3d model",
            "cnc program",
            "programming",
            "generate cnc",
        ]

        return any(marker in text for marker in planning_markers)

    for idx, step in enumerate(raw_steps, start=1):
        normalized_steps.append(normalize_step(step, idx))
    
    normalized_steps = [
        step for step in normalized_steps
        if not _is_non_machining_planning_step(step)
    ]

    normalized_steps = sorted(
        normalized_steps,
        key=lambda x: int(x.get("Step number", 10**9))
        if str(x.get("Step number", "")).isdigit()
        else 10**9
    )

    for idx, step in enumerate(normalized_steps, start=1):
        step["Step number"] = idx

    normalized_steps, stage_debug = repair_missing_stages(normalized_steps)

    normalized["Steps"] = normalized_steps

    if DEBUG_NORMALIZATION:
        normalized["_normalization_debug"] = {
            **stage_debug
        }

    return normalized


def _translate_equipment_to_ru(equipment: Any) -> List[str]:
    if isinstance(equipment, list):
        items = equipment
    elif equipment:
        items = [equipment]
    else:
        items = []

    translated = []
    for item in items:
        key = _normalize_equipment(item)
        ru = EQUIPMENT_RU_MAP.get(key, str(item).strip())
        if ru:
            translated.append(ru)

    dedup = []
    seen = set()
    for item in translated:
        low = item.lower()
        if low not in seen:
            dedup.append(item)
            seen.add(low)

    return dedup


def add_russian_labels(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return data

    result = dict(data)

    operation_name = str(result.get("Name of operation", "") or "").strip()

    operation_name_ru_map = {
        "manufacturing process": "Технологический маршрут обработки",
        "machining process": "Технологический маршрут механической обработки",
        "production process": "Производственный процесс",
    }

    if operation_name:
        result["Name of operation RU"] = operation_name_ru_map.get(
            operation_name.lower(),
            operation_name
        )
    else:
        result["Name of operation RU"] = "Технологический маршрут обработки"

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
        localized_step["Equipment RU"] = _translate_equipment_to_ru(equipment)

        localized_steps.append(localized_step)

    result["Steps"] = localized_steps
    return result


def strip_internal_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return data

    result = dict(data)

    internal_keys = {
        "_normalization_debug",
        "_validation",
    }

    for key in internal_keys:
        result.pop(key, None)

    return result


def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def _clean_json_text(text: str) -> str:
    if not isinstance(text, str):
        return ""

    cleaned = text.strip()

    cleaned = cleaned.replace("```JSON", "```").replace("```json", "```")

    cleaned = re.sub(r"^\s*json\s*\n", "", cleaned, flags=re.IGNORECASE)

    if "```" in cleaned:
        parts = cleaned.split("```")
        if len(parts) >= 3:
            cleaned = parts[1].strip()
        else:
            cleaned = cleaned.replace("```", "").strip()

    return cleaned.strip()


def _get_standard_code(row: pd.Series | Dict[str, Any]) -> str:
    return str(
        row.get("ISO")
        or row.get("GOST")
        or row.get("Standard")
        or ""
    )


def _get_standard_title(row: pd.Series | Dict[str, Any]) -> str:
    return str(
        row.get("Name of ISO")
        or row.get("Name of GOST")
        or row.get("Standard name")
        or ""
    )


def _safe_json_loads(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(_clean_json_text(text))
    except Exception:
        return None


def _extract_steps_for_rag(draft_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(draft_json, dict):
        return []

    for key in ["Steps", "steps", "operations", "Operations", "Process", "process"]:
        val = draft_json.get(key)
        if isinstance(val, list):
            return [x for x in val if isinstance(x, dict)]
        if isinstance(val, dict):
            for inner in ["Steps", "steps", "operations", "Operations"]:
                inner_val = val.get(inner)
                if isinstance(inner_val, list):
                    return [x for x in inner_val if isinstance(x, dict)]

    return []


def retrieve_relevant_data(
    query_text: str,
    csv_path: str = "./example_material/equipment_iso_ru.csv",
    top_k: int = 20,
    dedup_by_iso: bool = True,
) -> List[Dict[str, Any]]:
    global _RAG_DF_CACHE
    if "_RAG_DF_CACHE" not in globals():
        _RAG_DF_CACHE = {}

    if csv_path not in _RAG_DF_CACHE:
        _RAG_DF_CACHE[csv_path] = pd.read_csv(csv_path)

    df = _RAG_DF_CACHE[csv_path]

    def _row_doc(r: pd.Series) -> str:
        equipment = str(r.get("Equipment category", ""))
        equipment_ru = str(r.get("Equipment category ru", ""))
        operation = str(r.get("Operation category", ""))
        stage = str(r.get("Process stage", ""))
        synonyms = str(r.get("Synonyms", ""))
        standard_code = _get_standard_code(r)
        standard_title = _get_standard_title(r)

        return " ".join([
            equipment, equipment,
            equipment_ru,
            operation, operation,
            stage,
            synonyms,
            standard_code,
            standard_title
        ])

    docs = df.apply(_row_doc, axis=1).tolist()

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        stop_words=None,
        lowercase=True
    )
    tfidf_matrix = vectorizer.fit_transform(docs)
    query_text = query_text + " machining manufacturing process operation equipment"
    query_vec = vectorizer.transform([query_text])

    cosine_scores = cosine_similarity(query_vec, tfidf_matrix).flatten()
    top_indices = np.argsort(cosine_scores)[-top_k:][::-1]
    relevant_rows = df.iloc[top_indices].copy()

    if dedup_by_iso:
        if "ISO" in relevant_rows.columns:
            relevant_rows = relevant_rows.drop_duplicates(subset=["ISO"], keep="first")
        elif "GOST" in relevant_rows.columns:
            relevant_rows = relevant_rows.drop_duplicates(subset=["GOST"], keep="first")

    return relevant_rows.to_dict(orient="records")


def _format_rag_prompt(rag_rows: List[Dict[str, Any]], header: str = "") -> str:
    lines: List[str] = []
    if header:
        lines.append(header)

    lines.append(
        "RAG RULES:\n"
        "- Use ONLY ISO standards that appear in the list below.\n"
        "- For each step, pick at most 1–3 ISO standards.\n"
        "- If no ISO is clearly relevant, leave the ISO field empty ([]) instead of guessing.\n"
    )

    lines.append("ISO CANDIDATES:")
    for item in rag_rows:
        standard_code = _get_standard_code(item)
        standard_title = _get_standard_title(item)
        lines.append(
            f"- Equipment: {item.get('Equipment category','')}; "
            f"ISO: {standard_code}; "
            f"Title: {standard_title}"
        )

    return "\n".join(lines)


def _build_step_level_rag_context(
    steps: List[Dict[str, Any]],
    csv_path: str,
    max_rows_per_step: int = 5,
    dedup_by_iso: bool = True,
) -> str:
    blocks: List[str] = [
        "STEP-LEVEL RAG CONTEXT (ISO candidates grouped per step):",
        "RAG RULES:\n"
        "- Use ONLY ISO standards shown for the corresponding step.\n"
        "- For each step, choose at most 1–3 ISO standards.\n"
        "- If uncertain, use [] for ISO.\n",
    ]

    for i, step in enumerate(steps, start=1):
        action = str(step.get("Action", "") or "").strip()
        stage = str(step.get("Stage", "") or "").strip()
        equipment = step.get("Equipment", [])

        if isinstance(equipment, list):
            equipment_text = " ".join(str(x).strip() for x in equipment if str(x).strip())
        else:
            equipment_text = str(equipment).strip()

        query_parts = []

        if action:
            query_parts.append(f"operation {action}")

        if stage:
            query_parts.append(f"stage {stage}")

        if equipment_text:
            query_parts.append(f"equipment {equipment_text}")

        query = ". ".join(query_parts).strip()
        if not query:
            query = "machining operation equipment"

        rows = retrieve_relevant_data(
            query_text=query,
            csv_path=csv_path,
            top_k=max_rows_per_step,
            dedup_by_iso=dedup_by_iso,
        )

        if rows:
            filtered_rows = []
            for item in rows:
                row_text = " ".join([
                    str(item.get("Equipment category", "")),
                    str(item.get("Equipment category ru", "")),
                    str(item.get("Operation category", "")),
                    str(item.get("Process stage", "")),
                    str(item.get("Name of GOST", "")),
                    str(item.get("Name of ISO", "")),
                ]).lower()

                action_ok = action.lower() in row_text if action else True
                stage_ok = stage.lower() in row_text if stage else True

                if action_ok and stage_ok:
                    filtered_rows.append(item)

            if filtered_rows:
                rows = filtered_rows

        blocks.append(f"\nSTEP {i} QUERY:\n{query}")
        blocks.append("ISO CANDIDATES:")

        if not rows:
            blocks.append("- No candidates found")
            continue

        for item in rows:
            standard_code = _get_standard_code(item)
            standard_title = _get_standard_title(item)
            blocks.append(
                f"- ISO: {standard_code}; "
                f"Equipment: {item.get('Equipment category', '')}; "
                f"Title: {standard_title}"
            )

    return "\n".join(blocks)


def generate_response_from_image_mistral(image_path, prompt, api_key, data_type):
    model = "pixtral-12b-2409"
    base64_image = encode_image_to_base64(image_path)
    client = Mistral(api_key=api_key)

    def _call(text_prompt: str) -> str:
        response = client.chat.complete(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                    ],
                },
            ],
        )
        return response.choices[0].message.content

    csv_path = "./example_material/equipment_iso_ru.csv"
    image_hint = f"\n\n[Image file: {os.path.basename(image_path)}]"
    debug_dir = _debug_prompt_dir("pixtral_12b", data_type, image_path) if DEBUG_PROMPTS else None

    if data_type == "RAG":
        draft_prompt = (
            prompt
            + image_hint
            + "\n\nFIRST PASS TASK:\n"
            + "Return ONLY valid JSON. Create a draft process where each step contains Action and Equipment fields. "
            + "Do NOT include ISO in this first pass (use ISO: [] or omit ISO)."
        )

        if DEBUG_PROMPTS:
            _save_debug_text(os.path.join(debug_dir, "first_pass_prompt.txt"), draft_prompt)

        draft_text = _call(draft_prompt)

        if DEBUG_PROMPTS:
            _save_debug_text(os.path.join(debug_dir, "first_pass_response.txt"), draft_text)

        draft_json = _safe_json_loads(draft_text)
        if draft_json:
            draft_json = normalize_process_json(draft_json)
        steps = _extract_steps_for_rag(draft_json) if draft_json else []

        if steps:
            step_rag_context = _build_step_level_rag_context(
                steps,
                csv_path=csv_path,
                max_rows_per_step=5
            )

            full_prompt = (
                prompt
                + image_hint
                + "\n\nSECOND PASS TASK:\n"
                + "Return ONLY valid JSON. Produce the final process JSON and fill ISO per step using the STEP-LEVEL RAG CONTEXT below.\n\n"
                + step_rag_context
            )

            if DEBUG_PROMPTS:
                _save_debug_text(os.path.join(debug_dir, "step_rag_context.txt"), step_rag_context)
                _save_debug_text(os.path.join(debug_dir, "second_pass_prompt.txt"), full_prompt)

            second_pass_response = _call(full_prompt)

            if DEBUG_PROMPTS:
                _save_debug_text(os.path.join(debug_dir, "second_pass_response.txt"), second_pass_response)

            return second_pass_response

        query = (prompt + "\n" + os.path.basename(image_path)).strip()
        rag_rows = retrieve_relevant_data(
            query_text=query,
            csv_path=csv_path,
            top_k=20,
            dedup_by_iso=True
        )
        rag_prompt = _format_rag_prompt(
            rag_rows,
            header="Use the ISO KB below when filling ISO fields."
        )

        fallback_prompt = prompt + image_hint + "\n\n" + rag_prompt

        if DEBUG_PROMPTS:
            _save_debug_text(os.path.join(debug_dir, "fallback_rag_prompt.txt"), fallback_prompt)

        fallback_response = _call(fallback_prompt)

        if DEBUG_PROMPTS:
            _save_debug_text(os.path.join(debug_dir, "fallback_response.txt"), fallback_response)

        return fallback_response

    single_pass_prompt = prompt + image_hint

    if DEBUG_PROMPTS:
        _save_debug_text(os.path.join(debug_dir, "single_pass_prompt.txt"), single_pass_prompt)

    single_pass_response = _call(single_pass_prompt)

    if DEBUG_PROMPTS:
        _save_debug_text(os.path.join(debug_dir, "single_pass_response.txt"), single_pass_response)

    return single_pass_response


def generate_response_from_image_qwen(image_path, model_name, prompt, my_api_key, data_type):
    client = OpenAI(
        api_key=my_api_key,
        base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    )

    base64_image = encode_image_to_base64(image_path)

    def _call(text_prompt: str) -> str:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                    ],
                }
            ],
        )
        return completion.choices[0].message.content

    csv_path = "./example_material/equipment_iso_ru.csv"
    image_hint = f"\n\n[Image file: {os.path.basename(image_path)}]"
    debug_dir = _debug_prompt_dir(model_name, data_type, image_path) if DEBUG_PROMPTS else None

    if data_type == "RAG":
        draft_prompt = (
            prompt
            + image_hint
            + "\n\nFIRST PASS TASK:\n"
            + "Return ONLY valid JSON. Create a draft process where each step contains Action and Equipment fields. "
            + "Do NOT include ISO in this first pass (use ISO: [] or omit ISO)."
        )

        if DEBUG_PROMPTS:
            _save_debug_text(os.path.join(debug_dir, "first_pass_prompt.txt"), draft_prompt)

        draft_text = _call(draft_prompt)

        if DEBUG_PROMPTS:
            _save_debug_text(os.path.join(debug_dir, "first_pass_response.txt"), draft_text)

        draft_json = _safe_json_loads(draft_text)
        if draft_json:
            draft_json = normalize_process_json(draft_json)
        steps = _extract_steps_for_rag(draft_json) if draft_json else []

        if steps:
            step_rag_context = _build_step_level_rag_context(
                steps,
                csv_path=csv_path,
                max_rows_per_step=5
            )

            full_prompt = (
                prompt
                + image_hint
                + "\n\nSECOND PASS TASK:\n"
                + "Return ONLY valid JSON. Produce the final process JSON and fill ISO per step using the STEP-LEVEL RAG CONTEXT below.\n\n"
                + step_rag_context
            )

            if DEBUG_PROMPTS:
                _save_debug_text(os.path.join(debug_dir, "step_rag_context.txt"), step_rag_context)
                _save_debug_text(os.path.join(debug_dir, "second_pass_prompt.txt"), full_prompt)

            second_pass_response = _call(full_prompt)

            if DEBUG_PROMPTS:
                _save_debug_text(os.path.join(debug_dir, "second_pass_response.txt"), second_pass_response)

            return second_pass_response

        query = (prompt + "\n" + os.path.basename(image_path)).strip()
        rag_rows = retrieve_relevant_data(
            query_text=query,
            csv_path=csv_path,
            top_k=20,
            dedup_by_iso=True
        )
        rag_prompt = _format_rag_prompt(
            rag_rows,
            header="Use the ISO KB below when filling ISO fields."
        )

        fallback_prompt = prompt + image_hint + "\n\n" + rag_prompt

        if DEBUG_PROMPTS:
            _save_debug_text(os.path.join(debug_dir, "fallback_rag_prompt.txt"), fallback_prompt)

        fallback_response = _call(fallback_prompt)

        if DEBUG_PROMPTS:
            _save_debug_text(os.path.join(debug_dir, "fallback_response.txt"), fallback_response)

        return fallback_response

    single_pass_prompt = prompt + image_hint

    if DEBUG_PROMPTS:
        _save_debug_text(os.path.join(debug_dir, "single_pass_prompt.txt"), single_pass_prompt)

    single_pass_response = _call(single_pass_prompt)

    if DEBUG_PROMPTS:
        _save_debug_text(os.path.join(debug_dir, "single_pass_response.txt"), single_pass_response)

    return single_pass_response


def run_mistral(api_key, image_path, prompt, data_type):
    try:
        response = generate_response_from_image_mistral(image_path, prompt, api_key, data_type)
        return response
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None


def run_qwen(api_key, model_name, image_path, prompt, data_type):
    try:
        response = generate_response_from_image_qwen(image_path, model_name, prompt, api_key, data_type)
        return response
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None


def create_json_with_mistral(object_dirpath, prompt_path, output_path, api_key_mistral, data_type):
    json_data = {}
    api_key = api_key_mistral

    with open(prompt_path, "r", encoding="utf-8") as file:
        prompt = file.read()

    for dirpath, _, filenames in os.walk(object_dirpath):
        for file_name in filenames:
            path = os.path.join(dirpath, file_name)
            part_number = file_name.split(".")[0]

            response = run_mistral(api_key, path, prompt, data_type)
            json_data[part_number] = response

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        pickle.dump(json_data, f)


def create_json_with_qwen(api_key, model, object_dirpath, prompt_path, output_path, data_type):
    json_data = {}

    with open(prompt_path, "r", encoding="utf-8") as file:
        prompt = file.read()

    for dirpath, _, filenames in os.walk(object_dirpath):
        for file_name in filenames:
            path = os.path.join(dirpath, file_name)
            part_number = file_name.split(".")[0]

            response = run_qwen(api_key, model, path, prompt, data_type)
            json_data[part_number] = response

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        pickle.dump(json_data, f)


def save_jsons(json_pkl_paths, json_collages_paths):
    for i in range(len(json_pkl_paths)):
        pkl_path = json_pkl_paths[i]
        out_dir = json_collages_paths[i]
        os.makedirs(out_dir, exist_ok=True)

        with open(pkl_path, "rb") as f:
            raw_map = pickle.load(f)

        if not isinstance(raw_map, dict):
            print(f"[save_jsons] Skip {pkl_path}: expected dict, got {type(raw_map)}")
            continue

        for key, value in raw_map.items():
            if value is None:
                print(f"[save_jsons] Skip {key}: empty response")
                continue

            parsed = _safe_json_loads(value)
            if parsed is None:
                debug_path = os.path.join(out_dir, f"{key}.raw.txt")
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write(str(value))
                print(f"[save_jsons] JSON parse failed for {key}. Saved raw to {debug_path}")
                continue

            try:
                parsed = normalize_process_json(parsed)
            except Exception as e:
                debug_path = os.path.join(out_dir, f"{key}.normalize_error.txt")
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write(str(value))
                print(f"[save_jsons] Normalize failed for {key}: {e}. Saved raw to {debug_path}")
                continue

            if not parsed.get("File name"):
                parsed["File name"] = f"{key}.jpg"

            if not parsed.get("Name of operation"):
                parsed["Name of operation"] = "Manufacturing Process"
            
            if ENABLE_RU_LABELS:
                parsed = add_russian_labels(parsed)

            validation = validate_process_json(parsed)
            if DEBUG_NORMALIZATION:
                if "_normalization_debug" not in parsed:
                    parsed["_normalization_debug"] = {}

                parsed["_normalization_debug"]["validator_valid"] = validation.get("valid", False)
                parsed["_normalization_debug"]["validator_errors_count"] = len(validation.get("errors", []))
                parsed["_normalization_debug"]["validator_warnings_count"] = len(validation.get("warnings", []))
                parsed["_normalization_debug"]["validator_errors"] = validation.get("errors", [])
                parsed["_normalization_debug"]["validator_warnings"] = validation.get("warnings", [])
            parsed["_validation"] = validation

            output_data = parsed if EXPORT_DEBUG_FIELDS else strip_internal_fields(parsed)

            output_path = os.path.join(out_dir, f"{key}.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=4)


def llm_benchmark(api_key_qwen, api_key_mistral):
    object_path3, object_path4, object_path6 = (
        "./example_material/collages_3",
        "./example_material/collages_4",
        "./example_material/collages_6",
    )

    for type_name in type_names:
        data_type = "RAG" if type_name == "results_rag" else "NO_RAG"

        mistral_pkl_path3 = f"./{type_name}/json_responses/json_mistral_3.pkl"
        mistral_pkl_path4 = f"./{type_name}/json_responses/json_mistral_4.pkl"
        mistral_pkl_path6 = f"./{type_name}/json_responses/json_mistral_6.pkl"

        vl_max_pkl_path3 = f"./{type_name}/json_responses/json_qwen_vl_max_3.pkl"
        vl_max_pkl_path4 = f"./{type_name}/json_responses/json_qwen_vl_max_4.pkl"
        vl_max_pkl_path6 = f"./{type_name}/json_responses/json_qwen_vl_max_6.pkl"

        qwen_72b_pkl_path3 = f"./{type_name}/json_responses/json_qwen2_vl_72b_instruct_3.pkl"
        qwen_72b_pkl_path4 = f"./{type_name}/json_responses/json_qwen2_vl_72b_instruct_4.pkl"
        qwen_72b_pkl_path6 = f"./{type_name}/json_responses/json_qwen2_vl_72b_instruct_6.pkl"

        if run_mistral_model:
            create_json_with_mistral(object_path3, prompt_path3, mistral_pkl_path3, api_key_mistral, data_type)
            create_json_with_mistral(object_path4, prompt_path4, mistral_pkl_path4, api_key_mistral, data_type)
            create_json_with_mistral(object_path6, prompt_path6, mistral_pkl_path6, api_key_mistral, data_type)

        if run_qwen_vl_max_model:
            create_json_with_qwen(api_key_qwen, "qwen-vl-max", object_path3, prompt_path3, vl_max_pkl_path3, data_type)
            create_json_with_qwen(api_key_qwen, "qwen-vl-max", object_path4, prompt_path4, vl_max_pkl_path4, data_type)
            create_json_with_qwen(api_key_qwen, "qwen-vl-max", object_path6, prompt_path6, vl_max_pkl_path6, data_type)

        if run_qwen_72b_model:
            create_json_with_qwen(api_key_qwen, "qwen2.5-vl-72b-instruct", object_path3, prompt_path3, qwen_72b_pkl_path3, data_type)
            create_json_with_qwen(api_key_qwen, "qwen2.5-vl-72b-instruct", object_path4, prompt_path4, qwen_72b_pkl_path4, data_type)
            create_json_with_qwen(api_key_qwen, "qwen2.5-vl-72b-instruct", object_path6, prompt_path6, qwen_72b_pkl_path6, data_type)

        if run_qwen_72b_model:
            save_jsons(
                [qwen_72b_pkl_path3, qwen_72b_pkl_path4, qwen_72b_pkl_path6],
                [
                    f"./{type_name}/json_responses/qwen2_5_vl_72b/collages_3",
                    f"./{type_name}/json_responses/qwen2_5_vl_72b/collages_4",
                    f"./{type_name}/json_responses/qwen2_5_vl_72b/collages_6",
                ],
            )

        if run_qwen_vl_max_model:
            save_jsons(
                [vl_max_pkl_path3, vl_max_pkl_path4, vl_max_pkl_path6],
                [
                    f"./{type_name}/json_responses/qwen_vl_max/collages_3",
                    f"./{type_name}/json_responses/qwen_vl_max/collages_4",
                    f"./{type_name}/json_responses/qwen_vl_max/collages_6",
                ],
            )

        if run_mistral_model:
            save_jsons(
                [mistral_pkl_path3, mistral_pkl_path4, mistral_pkl_path6],
                [
                    f"./{type_name}/json_responses/pixtral_12b/collages_3",
                    f"./{type_name}/json_responses/pixtral_12b/collages_4",
                    f"./{type_name}/json_responses/pixtral_12b/collages_6",
                ],
            )