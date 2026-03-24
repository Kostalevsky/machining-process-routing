import base64
import json
import os
import pickle
import re
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional
from mistralai import Mistral
from openai import OpenAI
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


prompt_path3 = "./example_material/prompts/prompt_3.txt"
prompt_path4 = "./example_material/prompts/prompt_4.txt"
prompt_path6 = "./example_material/prompts/prompt_6.txt"


ALLOWED_ACTIONS = [
    "turning", "facing", "boring", "threading", "drilling", "reaming",
    "milling", "slotting", "key-seating", "broaching", "heat-treatment",
    "deburring", "sand-blasting", "grinding", "polishing",
    "quality-inspection", "surface-coating", "packaging", "cutting-off",
    "knurling", "tapping", "lapping", "honing", "burnishing",
    "electro-discharge machining (EDM)", "laser cutting", "waterjet cutting",
    "assembly", "marking", "non-destructive testing (NDT)"
]


def validate_process_json(data: dict) -> dict:
    errors = []

    steps = data.get("Steps", [])

    if not steps:
        errors.append("No steps found")
        return {"valid": False, "errors": errors}

    actions = [str(s.get("Action", "")).lower() for s in steps]

    # 1. Проверка обязательных стадий
    required = ["rough", "finish", "inspection", "packaging"]
    for r in required:
        if not any(r in a for a in actions):
            errors.append(f"Missing stage: {r}")

    # 2. Проверка порядка (грубая)
    order_map = {
        "rough": 0,
        "semi": 1,
        "finish": 2,
        "inspection": 3,
        "packaging": 4
    }

    prev_order = -1
    for a in actions:
        for key, val in order_map.items():
            if key in a:
                if val < prev_order:
                    errors.append("Invalid operation order")
                prev_order = val

    # 3. Проверка соответствия equipment-action (простая эвристика)
    for step in steps:
        action = str(step.get("Action", "")).lower()
        equipment = str(step.get("Equipment", "")).lower()

        if "turn" in action and "lathe" not in equipment:
            errors.append(f"Turning without lathe: {equipment}")

        if "mill" in action and "mill" not in equipment:
            errors.append(f"Milling mismatch: {equipment}")

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


def _normalize_text(s):
    return str(s or "").strip().lower()


def _normalize_action(action):
    raw = _normalize_text(action)

    alias_map = {
        "rough turning": "turning",
        "finish turning": "turning",
        "semi-finish turning": "turning",
        "lathe turning": "turning",
        "turn": "turning",

        "face milling": "milling",
        "end milling": "milling",

        "inspection": "quality-inspection",
        "quality inspection": "quality-inspection",
        "quality control": "quality-inspection",

        "ndt": "non-destructive testing (NDT)",
        "non destructive testing": "non-destructive testing (NDT)",
        "non-destructive testing": "non-destructive testing (NDT)",

        "edm": "electro-discharge machining (EDM)",
    }

    if raw in alias_map:
        return alias_map[raw]

    for allowed in ALLOWED_ACTIONS:
        if raw == allowed.lower():
            return allowed

    for alias, canonical in alias_map.items():
        if alias in raw:
            return canonical

    for allowed in ALLOWED_ACTIONS:
        if allowed.lower() in raw:
            return allowed

    return raw


def _normalize_equipment(equipment):
    if isinstance(equipment, list):
        equipment = " ".join(str(x) for x in equipment)

    raw = _normalize_text(equipment)

    equipment_aliases = {
        "lathe machine": "lathe",
        "cnc lathe machine": "cnc lathe",
        "turning center": "cnc lathe",
        "turning centre": "cnc lathe",

        "milling machine": "milling machine",
        "cnc milling machine": "cnc milling machine",

        "drill press": "drilling machine",
        "inspection station": "inspection equipment",
    }

    if raw in equipment_aliases:
        return equipment_aliases[raw]

    return raw

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


def _build_step_level_rag_context(
    steps: List[Dict[str, Any]],
    csv_path: str,
    max_rows_per_step: int = 5,
) -> str:
    blocks: List[str] = [
        "STEP-LEVEL RAG CONTEXT (ISO candidates grouped per step):",
        "RAG RULES:\n"
        "- Use ONLY ISO standards shown for the corresponding step.\n"
        "- For each step, choose at most 1–3 ISO standards.\n"
        "- If uncertain, use [] for ISO.\n",
    ]

    for i, step in enumerate(steps, start=1):
        action = step.get("Action", "")
        equipment = step.get("Equipment", "")

        norm_action = _normalize_action(action)
        norm_equipment = _normalize_equipment(equipment)

        query_parts = []
        if norm_action:
            query_parts.append(f"operation {norm_action}")
        if norm_equipment:
            query_parts.append(f"equipment {norm_equipment}")

        query = ". ".join(query_parts).strip()
        if not query:
            query = "machining operation equipment"

        rows = retrieve_relevant_data(
            query=query,
            csv_path=csv_path,
            top_n=top_n,
            dedup_by_iso=dedup_by_iso
        )

        if rows and norm_action:
            filtered_rows = []
            for item in rows:
                row_text = " ".join([
                    str(item.get("Equipment category", "")),
                    str(item.get("Equipment category ru", "")),
                    str(item.get("Operation category", "")),
                    str(item.get("Process stage", "")),
                    str(item.get("Name of GOST", "")),
                ]).lower()

                if norm_action.lower() in row_text:
                    filtered_rows.append(item)

            if filtered_rows:
                rows = filtered_rows

        blocks.append(f"\nSTEP {i} QUERY:\n{query}")
        blocks.append("ISO CANDIDATES:")
        for item in rows:
            standard_code = _get_standard_code(item)
            standard_title = _get_standard_title(item)
            blocks.append(
                f"- ISO: {standard_code}; "
                f"Equipment: {item.get('Equipment category','')}; "
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

    if data_type == "RAG":
        draft_prompt = (
            prompt
            + image_hint
            + "\n\nFIRST PASS TASK:\n"
            + "Return ONLY valid JSON. Create a draft process where each step contains Action and Equipment fields. "
            + "Do NOT include ISO in this first pass (use ISO: [] or omit ISO)."
        )
        draft_text = _call(draft_prompt)

        draft_json = _safe_json_loads(draft_text)
        steps = _extract_steps_for_rag(draft_json) if draft_json else []

        if steps:
            step_rag_context = _build_step_level_rag_context(steps, csv_path=csv_path, max_rows_per_step=5)
            full_prompt = (
                prompt
                + image_hint
                + "\n\nSECOND PASS TASK:\n"
                + "Return ONLY valid JSON. Produce the final process JSON and fill ISO per step using the STEP-LEVEL RAG CONTEXT below.\n\n"
                + step_rag_context
            )
            return _call(full_prompt)

        query = (prompt + "\n" + os.path.basename(image_path)).strip()
        rag_rows = retrieve_relevant_data(query_text=query, csv_path=csv_path, top_k=20, dedup_by_iso=True)
        rag_prompt = _format_rag_prompt(rag_rows, header="Use the ISO KB below when filling ISO fields.")
        return _call(prompt + image_hint + "\n\n" + rag_prompt)

    return _call(prompt + image_hint)


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

    if data_type == "RAG":
        draft_prompt = (
            prompt
            + image_hint
            + "\n\nFIRST PASS TASK:\n"
            + "Return ONLY valid JSON. Create a draft process where each step contains Action and Equipment fields. "
            + "Do NOT include ISO in this first pass (use ISO: [] or omit ISO)."
        )
        draft_text = _call(draft_prompt)

        draft_json = _safe_json_loads(draft_text)
        steps = _extract_steps_for_rag(draft_json) if draft_json else []

        if steps:
            step_rag_context = _build_step_level_rag_context(steps, csv_path=csv_path, max_rows_per_step=5)
            full_prompt = (
                prompt
                + image_hint
                + "\n\nSECOND PASS TASK:\n"
                + "Return ONLY valid JSON. Produce the final process JSON and fill ISO per step using the STEP-LEVEL RAG CONTEXT below.\n\n"
                + step_rag_context
            )
            return _call(full_prompt)

        query = (prompt + "\n" + os.path.basename(image_path)).strip()
        rag_rows = retrieve_relevant_data(query_text=query, csv_path=csv_path, top_k=20, dedup_by_iso=True)
        rag_prompt = _format_rag_prompt(rag_rows, header="Use the ISO KB below when filling ISO fields.")
        return _call(prompt + image_hint + "\n\n" + rag_prompt)

    return _call(prompt + image_hint)


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

        raw_map = pickle.load(open(pkl_path, "rb"))

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
            if parsed:
                validation = validate_process_json(parsed)
                parsed["_validation"] = validation

            output_path = os.path.join(out_dir, f"{key}.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=4)


def llm_benchmark(api_key_qwen, api_key_mistral):
    object_path3, object_path4, object_path6 = (
        "./example_material/collages_3",
        "./example_material/collages_4",
        "./example_material/collages_6",
    )

    for type_name in ["results_no_rag", "results_rag"]:
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

        create_json_with_mistral(object_path3, prompt_path3, mistral_pkl_path3, api_key_mistral, data_type)
        create_json_with_mistral(object_path4, prompt_path4, mistral_pkl_path4, api_key_mistral, data_type)
        create_json_with_mistral(object_path6, prompt_path6, mistral_pkl_path6, api_key_mistral, data_type)

        create_json_with_qwen(api_key_qwen, "qwen-vl-max", object_path3, prompt_path3, vl_max_pkl_path3, data_type)
        create_json_with_qwen(api_key_qwen, "qwen-vl-max", object_path4, prompt_path4, vl_max_pkl_path4, data_type)
        create_json_with_qwen(api_key_qwen, "qwen-vl-max", object_path6, prompt_path6, vl_max_pkl_path6, data_type)

        create_json_with_qwen(
            api_key_qwen, "qwen2.5-vl-72b-instruct", object_path3, prompt_path3, qwen_72b_pkl_path3, data_type
        )
        create_json_with_qwen(
            api_key_qwen, "qwen2.5-vl-72b-instruct", object_path4, prompt_path4, qwen_72b_pkl_path4, data_type
        )
        create_json_with_qwen(
            api_key_qwen, "qwen2.5-vl-72b-instruct", object_path6, prompt_path6, qwen_72b_pkl_path6, data_type
        )

        save_jsons(
            [qwen_72b_pkl_path3, qwen_72b_pkl_path4, qwen_72b_pkl_path6],
            [
                f"./{type_name}/json_responses/qwen2_5_vl_72b/collages_3",
                f"./{type_name}/json_responses/qwen2_5_vl_72b/collages_4",
                f"./{type_name}/json_responses/qwen2_5_vl_72b/collages_6",
            ],
        )

        save_jsons(
            [vl_max_pkl_path3, vl_max_pkl_path4, vl_max_pkl_path6],
            [
                f"./{type_name}/json_responses/qwen_vl_max/collages_3",
                f"./{type_name}/json_responses/qwen_vl_max/collages_4",
                f"./{type_name}/json_responses/qwen_vl_max/collages_6",
            ],
        )

        save_jsons(
            [mistral_pkl_path3, mistral_pkl_path4, mistral_pkl_path6],
            [
                f"./{type_name}/json_responses/pixtral_12b/collages_3",
                f"./{type_name}/json_responses/pixtral_12b/collages_4",
                f"./{type_name}/json_responses/pixtral_12b/collages_6",
            ],
        )