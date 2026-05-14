import base64
import json
import llm_benchmarks
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import openai
import os
import pandas as pd
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer


def generate_response_from_image(api_key, prompt):
    openai.api_key = api_key

    # Obtain additional context from RAG
    csv_path="./example_material/equipment_iso.csv"
    rag_context = llm_benchmarks.retrieve_relevant_data(prompt, csv_path)

    # Formulate context for the model
    rag_prompt = "Use the following information about available equipment and standards:\n"
    for item in rag_context:
        rag_prompt += (
            f"- Equipment: {item['Equipment category']}, "
            f"ISO: {item['ISO']}, Name of ISO: {item['Name of ISO']}\n"
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
    Respond only with a space-separated list of scores for all five criteria in the format of: 'Number Number Number Number Number' . The answer cannot contain zeros for more than two criteria.

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

def count_quality(collages_num, generated_json_path, response, results):
    if generated_json_path.__contains__("pixtral_12b"):
        results["Pixtral 12B"][collages_num].append(response)
    elif generated_json_path.__contains__("qwen2_5_vl_72b"):
        results["Qwen2.5-VL-72B"][collages_num].append(response)
    elif generated_json_path.__contains__("qwen_vl_max"):
        results["Qwen-VL-Max"][collages_num].append(response)

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

    for reference_dirpath, generated_paths in reference_paths.items():
        for generated_dirpath in generated_paths:
            for dirpath, dirnames, filenames in os.walk(generated_dirpath):
                for file_path in filenames:
                    generated_json_path = os.path.join(dirpath, file_path)
                    part_number = file_path.split(".")[0]

                    reference_json_path = os.path.join(reference_dirpath, f"{part_number}.json")

                    try:
                        with open(generated_json_path, 'r', encoding='utf-8') as file:
                            generated_json = json.load(file)
                        with open(reference_json_path, 'r', encoding='utf-8') as file:
                            reference_json = json.load(file)

                        prompt = create_prompt(reference_json, generated_json)

                        response = run_model(api_key, prompt)

                        if dirpath.endswith("3"):
                            count_quality("3", generated_json_path, response, results)
                        elif dirpath.endswith("4"):
                            count_quality("4", generated_json_path, response, results)
                        elif dirpath.endswith("6"):
                            count_quality("6", generated_json_path, response, results)

                    except Exception as e:
                        print(f"Error:", e)
    return results


def evaluate(api_key):
    results_no_rag = quality_assessment('results_no_rag', api_key)
    results_rag = quality_assessment('results_rag', api_key)

    with open('./metrics/metrics_no_rag.pkl', 'wb') as f:
        pickle.dump(results_no_rag, f)

    with open('./metrics/metrics_rag.pkl', 'wb') as f:
        pickle.dump(results_rag, f)