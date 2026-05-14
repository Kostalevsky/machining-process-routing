import json
import llm_benchmarks
import openai
import os
import re
import pandas as pd
import pickle
from collections import Counter


def generate_response_from_image(api_key, prompt):
    openai.api_key = api_key

    csv_path = "./example_material/equipment_iso_ru.csv"
    rag_context = llm_benchmarks.retrieve_relevant_data(prompt, csv_path)

    rag_prompt = "Use the following information about available equipment and standards:\n"
    for item in rag_context:
        rag_prompt += (
            f"- Equipment: {item.get('Equipment category', '')}, "
            f"Equipment RU: {item.get('Equipment category ru', '')}, "
            f"Operation: {item.get('Operation category', '')}, "
            f"GOST: {item.get('GOST', '')}, "
            f"Title: {item.get('Name of GOST', '')}, "
            f"Stage: {item.get('Process stage', '')}\n"
        )

    full_prompt = prompt + "\n\n" + rag_prompt

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": full_prompt},
                    ],
                }
            ],
            max_tokens=1000,
        )

        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Error when accessing the OpenAI API: {str(e)}")


def create_prompt(reference_json, generated_json):
    prompt = f"""
    Evaluate the generated JSON file against the reference file based on the following criteria.
    Respond only with a space-separated list of scores for all five criteria in the format of: 'Number Number Number Number Number'.

    1) File Structure (max. 100) – This criterion checks that the JSON structure fully matches the reference, including field names, nesting, and data types.
    2) Semantic Correctness (max. 100) – This criterion evaluates whether all steps are logically ordered and semantically equivalent to those in the reference, even if worded differently.
    3) Data Completeness (max. 100) – This criterion checks that all steps from the reference are present without omissions or unnecessary additions.
    4) Wording Accuracy (max. 100) – This criterion assesses how closely the wording matches the reference. Minor variations such as pluralization or slight rewording (e.g., “Analyze drawing” vs. “Analyze drawings”) may be acceptable and can be assessed with a maximum rating.
    5) ISO Standard Relevance & Consistency (max. 100) – This new criterion checks whether the ISO standards listed for each step are relevant, consistent with industry norms, and match those in the reference. Allow minor deviations only if they represent equally applicable standards.

    Generated JSON file:
    {generated_json}

    Reference JSON file:
    {reference_json}
    """

    return prompt


def run_model(api_key, prompt):
    try:
        response = generate_response_from_image(api_key, prompt)
        print(response)
        return response
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None


def count_quality(collages_num, generated_json_path, response, results):
    if generated_json_path.__contains__("pixtral_12b"):
        results["Pixtral 12B"][collages_num].append(response)
    elif generated_json_path.__contains__("qwen2_5_vl_72b"):
        results["Qwen2.5-VL-72B"][collages_num].append(response)
    elif generated_json_path.__contains__("qwen_vl_max"):
        results["Qwen-VL-Max"][collages_num].append(response)


def parse_judge_scores(response: str):
    if not isinstance(response, str):
        return None

    numbers = re.findall(r"\d+(?:\.\d+)?", response)

    if len(numbers) < 5:
        return None
    try:
        scores = list(map(float, numbers[:5]))
        return {
            "file_structure": scores[0],
            "semantic_correctness": scores[1],
            "data_completeness": scores[2],
            "wording_accuracy": scores[3],
            "iso_relevance": scores[4],
            "weighted_score": (
                0.2 * scores[0]
                + 0.2 * scores[1]
                + 0.1 * scores[2]
                + 0.1 * scores[3]
                + 0.4 * scores[4]
            ),
        }
    except Exception:
        return None
    

def extract_actions(process_json):
    if not isinstance(process_json, dict):
        return []

    steps = process_json.get("Steps", [])
    if not isinstance(steps, list):
        return []

    actions = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        action = str(step.get("Action", "") or "").strip()
        if action:
            actions.append(action)

    return actions


def extract_stages(process_json):
    if not isinstance(process_json, dict):
        return []

    steps = process_json.get("Steps", [])
    if not isinstance(steps, list):
        return []

    stages = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        stage = str(step.get("Stage", "") or "").strip()
        if stage:
            stages.append(stage)

    return stages


def extract_iso_codes(process_json):
    if not isinstance(process_json, dict):
        return []

    steps = process_json.get("Steps", [])
    if not isinstance(steps, list):
        return []

    iso_codes = []
    for step in steps:
        if not isinstance(step, dict):
            continue

        iso_list = step.get("ISO", [])
        if iso_list is None:
            continue

        if not isinstance(iso_list, list):
            iso_list = [iso_list]

        for iso in iso_list:
            iso_str = str(iso).strip()
            if iso_str:
                iso_codes.append(iso_str)

    return iso_codes


def infer_model_name(path: str) -> str:
    path = path.lower()
    if "pixtral_12b" in path:
        return "Pixtral 12B"
    if "qwen2_5_vl_72b" in path:
        return "Qwen2.5-VL-72B"
    if "qwen_vl_max" in path:
        return "Qwen-VL-Max"
    return "Unknown"


def extract_per_part_metrics(
    generated_json_path,
    generated_json,
    reference_json,
    judge_response,
    rag_mode
):
    model_name = infer_model_name(generated_json_path)
    collage_size = infer_collage_size(generated_json_path)
    part_number = os.path.basename(generated_json_path).split(".")[0]

    generated_steps = generated_json.get("Steps", []) if isinstance(generated_json, dict) else []
    reference_steps = reference_json.get("Steps", []) if isinstance(reference_json, dict) else []

    generated_actions = extract_actions(generated_json)
    reference_actions = extract_actions(reference_json)

    generated_stages = extract_stages(generated_json)
    reference_stages = extract_stages(reference_json)

    generated_iso = extract_iso_codes(generated_json)
    reference_iso = extract_iso_codes(reference_json)

    action_scores = precision_recall_f1(generated_actions, reference_actions)
    stage_scores = precision_recall_f1(generated_stages, reference_stages)
    iso_scores = precision_recall_f1(generated_iso, reference_iso)

    action_sequence_match = exact_sequence_match(generated_actions, reference_actions)

    validation = generated_json.get("_validation", {})
    debug_block = generated_json.get("_normalization_debug", {})

    judge_scores = parse_judge_scores(judge_response) or {
        "file_structure": None,
        "semantic_correctness": None,
        "data_completeness": None,
        "wording_accuracy": None,
        "iso_relevance": None,
        "weighted_score": None,
    }

    row = {
        "part_number": part_number,
        "model_name": model_name,
        "collage_size": collage_size,
        "rag_mode": rag_mode,

        "steps_count_generated": len(generated_steps) if isinstance(generated_steps, list) else 0,
        "steps_count_reference": len(reference_steps) if isinstance(reference_steps, list) else 0,
        "steps_diff": (
            (len(generated_steps) if isinstance(generated_steps, list) else 0)
            - (len(reference_steps) if isinstance(reference_steps, list) else 0)
        ),

        "has_validation": bool(validation or debug_block),
        "validator_valid": debug_block.get("validator_valid", validation.get("valid")),
        "validator_errors_count": debug_block.get(
            "validator_errors_count",
            len(validation.get("errors", [])) if isinstance(validation, dict) else 0
        ),
        "validator_warnings_count": debug_block.get(
            "validator_warnings_count",
            len(validation.get("warnings", [])) if isinstance(validation, dict) else 0
        ),

        "judge_file_structure": judge_scores["file_structure"],
        "judge_semantic_correctness": judge_scores["semantic_correctness"],
        "judge_data_completeness": judge_scores["data_completeness"],
        "judge_wording_accuracy": judge_scores["wording_accuracy"],
        "judge_iso_relevance": judge_scores["iso_relevance"],
        "judge_weighted_score": judge_scores["weighted_score"],

        "action_precision": action_scores["precision"],
        "action_recall": action_scores["recall"],
        "action_f1": action_scores["f1"],

        "stage_precision": stage_scores["precision"],
        "stage_recall": stage_scores["recall"],
        "stage_f1": stage_scores["f1"],

        "iso_precision": iso_scores["precision"],
        "iso_recall": iso_scores["recall"],
        "iso_f1": iso_scores["f1"],

        "exact_action_sequence_match": action_sequence_match,
    }

    return row


def infer_collage_size(path: str) -> str:
    path = path.lower()
    if path.endswith("3") or "collages_3" in path:
        return "3"
    if path.endswith("4") or "collages_4" in path:
        return "4"
    if path.endswith("6") or "collages_6" in path:
        return "6"
    return "unknown"


def precision_recall_f1(pred_items, gold_items):
    pred_counter = Counter(pred_items)
    gold_counter = Counter(gold_items)

    if sum(pred_counter.values()) == 0 and sum(gold_counter.values()) == 0:
        return {
            "precision": 1.0,
            "recall": 1.0,
            "f1": 1.0,
        }

    if sum(pred_counter.values()) == 0:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
        }

    if sum(gold_counter.values()) == 0:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
        }

    overlap = 0
    for key in pred_counter:
        overlap += min(pred_counter[key], gold_counter.get(key, 0))

    precision = overlap / sum(pred_counter.values()) if pred_counter else 0.0
    recall = overlap / sum(gold_counter.values()) if gold_counter else 0.0

    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)

    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }


def exact_sequence_match(pred_items, gold_items):
    return float(pred_items == gold_items)


def quality_assessment(data_type, api_key):
    reference_paths = {
        "./example_material/json_standard/json_collages_3": [
            f"./{data_type}/json_responses/pixtral_12b/collages_3",
            f"./{data_type}/json_responses/qwen2_5_vl_72b/collages_3",
            f"./{data_type}/json_responses/qwen_vl_max/collages_3"
        ],
        "./example_material/json_standard/json_collages_4": [
            f"./{data_type}/json_responses/pixtral_12b/collages_4",
            f"./{data_type}/json_responses/qwen2_5_vl_72b/collages_4",
            f"./{data_type}/json_responses/qwen_vl_max/collages_4"
        ],
        "./example_material/json_standard/json_collages_6": [
            f"./{data_type}/json_responses/pixtral_12b/collages_6",
            f"./{data_type}/json_responses/qwen2_5_vl_72b/collages_6",
            f"./{data_type}/json_responses/qwen_vl_max/collages_6"
        ]
    }

    results = {
        "Pixtral 12B": {"3": [], "4": [], "6": []},
        "Qwen2.5-VL-72B": {"3": [], "4": [], "6": []},
        "Qwen-VL-Max": {"3": [], "4": [], "6": []},
    }

    per_part_rows = []

    rag_mode = "RAG" if data_type == "results_rag" else "NO_RAG"

    for reference_dirpath, generated_paths in reference_paths.items():
        for generated_dirpath in generated_paths:
            for dirpath, dirnames, filenames in os.walk(generated_dirpath):
                for file_path in filenames:
                    if not file_path.endswith(".json"):
                        continue
                    generated_json_path = os.path.join(dirpath, file_path)
                    part_number = file_path.split(".")[0]
                    reference_json_path = os.path.join(reference_dirpath, f"{part_number}.json")

                    try:
                        with open(generated_json_path, 'r', encoding='utf-8') as file:
                            generated_json = json.load(file)
                        
                        if not os.path.exists(reference_json_path):
                            print(f"Missing reference JSON: {reference_json_path}")
                            continue

                        with open(reference_json_path, 'r', encoding='utf-8') as file:
                            reference_json = json.load(file)

                        run_llm_judge = os.getenv("RUN_LLM_JUDGE", "false").lower() == "true"

                        if run_llm_judge:
                            prompt = create_prompt(reference_json, generated_json)
                            response = run_model(api_key, prompt)
                        else:
                            response = None

                        if dirpath.endswith("3"):
                            count_quality("3", generated_json_path, response, results)
                        elif dirpath.endswith("4"):
                            count_quality("4", generated_json_path, response, results)
                        elif dirpath.endswith("6"):
                            count_quality("6", generated_json_path, response, results)

                        per_part_rows.append(
                            extract_per_part_metrics(
                                generated_json_path=generated_json_path,
                                generated_json=generated_json,
                                reference_json=reference_json,
                                judge_response=response,
                                rag_mode=rag_mode,
                            )
                        )

                    except Exception as e:
                        print(f"Error: {e}")

    return results, per_part_rows


def build_quality_report(per_part_rows):
    if not per_part_rows:
        return {
            "overall": {},
            "by_model": {},
            "by_collage_size": {},
            "by_rag_mode": {},
            "top_validator_failures": {}
        }

    df = pd.DataFrame(per_part_rows)

    def safe_mean(series):
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.notna().sum() == 0:
            return None
        return float(numeric.mean())
    
    def safe_bool_mean(series):
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.notna().sum() == 0:
            return None
        return float(numeric.mean())

    report = {
        "overall": {
            "rows": int(len(df)),
            "mean_weighted_score": safe_mean(df["judge_weighted_score"]),
            "mean_validator_errors": safe_mean(df["validator_errors_count"]),
            "mean_validator_warnings": safe_mean(df["validator_warnings_count"]),
            "valid_rate": safe_bool_mean(df["validator_valid"]),
            "mean_steps_generated": safe_mean(df["steps_count_generated"]),
            "mean_steps_reference": safe_mean(df["steps_count_reference"]),

            "mean_action_precision": safe_mean(df["action_precision"]),
            "mean_action_recall": safe_mean(df["action_recall"]),
            "mean_action_f1": safe_mean(df["action_f1"]),

            "mean_stage_precision": safe_mean(df["stage_precision"]),
            "mean_stage_recall": safe_mean(df["stage_recall"]),
            "mean_stage_f1": safe_mean(df["stage_f1"]),

            "mean_iso_precision": safe_mean(df["iso_precision"]),
            "mean_iso_recall": safe_mean(df["iso_recall"]),
            "mean_iso_f1": safe_mean(df["iso_f1"]),

            "mean_exact_action_sequence_match": safe_mean(df["exact_action_sequence_match"]),
        },
        "by_model": {},
        "by_collage_size": {},
        "by_rag_mode": {},
        "top_validator_failures": {}
    }

    for model_name, group in df.groupby("model_name"):
        report["by_model"][model_name] = {
            "rows": int(len(group)),
            "mean_weighted_score": safe_mean(group["judge_weighted_score"]),
            "valid_rate": safe_bool_mean(group["validator_valid"]),
            "mean_validator_errors": safe_mean(group["validator_errors_count"]),
            "mean_validator_warnings": safe_mean(group["validator_warnings_count"]),
            "mean_steps_generated": safe_mean(group["steps_count_generated"]),

            "mean_action_f1": safe_mean(group["action_f1"]),
            "mean_stage_f1": safe_mean(group["stage_f1"]),
            "mean_iso_f1": safe_mean(group["iso_f1"]),
            "mean_exact_action_sequence_match": safe_mean(group["exact_action_sequence_match"]),
        }

    for collage_size, group in df.groupby("collage_size"):
        report["by_collage_size"][str(collage_size)] = {
            "rows": int(len(group)),
            "mean_weighted_score": safe_mean(group["judge_weighted_score"]),
            "valid_rate": safe_bool_mean(group["validator_valid"]),
            "mean_validator_errors": safe_mean(group["validator_errors_count"]),

            "mean_action_f1": safe_mean(group["action_f1"]),
            "mean_stage_f1": safe_mean(group["stage_f1"]),
            "mean_iso_f1": safe_mean(group["iso_f1"]),
            "mean_exact_action_sequence_match": safe_mean(group["exact_action_sequence_match"]),
        }

    for rag_mode, group in df.groupby("rag_mode"):
        report["by_rag_mode"][str(rag_mode)] = {
            "rows": int(len(group)),
            "mean_weighted_score": safe_mean(group["judge_weighted_score"]),
            "valid_rate": safe_bool_mean(group["validator_valid"]),
            "mean_validator_errors": safe_mean(group["validator_errors_count"]),

            "mean_action_f1": safe_mean(group["action_f1"]),
            "mean_stage_f1": safe_mean(group["stage_f1"]),
            "mean_iso_f1": safe_mean(group["iso_f1"]),
            "mean_exact_action_sequence_match": safe_mean(group["exact_action_sequence_match"]),
        }

    return report


def evaluate(api_key):
    os.makedirs("./metrics", exist_ok=True)

    results_no_rag, rows_no_rag = quality_assessment('results_no_rag', api_key)
    results_rag, rows_rag = quality_assessment('results_rag', api_key)

    with open('./metrics/metrics_no_rag.pkl', 'wb') as f:
        pickle.dump(results_no_rag, f)

    with open('./metrics/metrics_rag.pkl', 'wb') as f:
        pickle.dump(results_rag, f)

    all_rows = rows_no_rag + rows_rag
    per_part_df = pd.DataFrame(all_rows)
    per_part_df.to_csv("./metrics/per_part_metrics.csv", index=False, encoding="utf-8")

    aggregate_report = build_quality_report(all_rows)
    with open("./metrics/aggregate_metrics.json", "w", encoding="utf-8") as f:
        json.dump(aggregate_report, f, ensure_ascii=False, indent=4)

    print("Saved developer quality reports:")
    print("- ./metrics/per_part_metrics.csv")
    print("- ./metrics/aggregate_metrics.json")