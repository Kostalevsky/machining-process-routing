import base64
import json
import numpy as np
import os
import pandas as pd
import pickle

from mistralai import Mistral
from openai import OpenAI
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


prompt_path3 = './example_material/prompts/prompt_3.txt'
prompt_path4 = './example_material/prompts/prompt_4.txt'
prompt_path6 = './example_material/prompts/prompt_6.txt'

# Function to encode an image to base64
def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")
    

def retrieve_relevant_data(prompt_text, csv_path="./example_material/equipment_iso.csv", top_k=15):
    df = pd.read_csv(csv_path)

    # Vectorization of the query and categories
    vectorizer = TfidfVectorizer()
    categories = df["Equipment category"].unique()
    tfidf_matrix = vectorizer.fit_transform(categories)
    prompt_vec = vectorizer.transform([prompt_text])

    # Calculate similarity
    cosine_scores = cosine_similarity(prompt_vec, tfidf_matrix).flatten()
    top_indices = np.argsort(cosine_scores)[-top_k:][::-1]

    relevant_rows = df[df["Equipment category"].isin(categories[top_indices])]
    return relevant_rows.to_dict(orient='records')


def generate_response_from_image_mistral(image_path, prompt, api_key, data_type):
    model = "pixtral-12b-2409"
    base64_image = encode_image_to_base64(image_path)

    if data_type == 'RAG':
        # Obtain additional context from RAG
        csv_path="./example_material/equipment_iso.csv"
        rag_context = retrieve_relevant_data(prompt, csv_path)

        # Formulate context for the model
        rag_prompt = "Use the following information about available equipment and standards:\n"
        for item in rag_context:
            rag_prompt += (
                f"- Equipment: {item['Equipment category']}, "
                f"ISO: {item['ISO']}, Name of ISO: {item['Name of ISO']}\n"
            )

        full_prompt = prompt + "\n\n" + rag_prompt
    else:
        full_prompt = prompt
        

    client = Mistral(api_key=api_key)
    response = client.chat.complete(
        model= model,
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": full_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                ],
            },
        ]
    )
    return response.choices[0].message.content


def generate_response_from_image_qwen(image_path, model_name, prompt, my_api_key, data_type):
    client = OpenAI(
        api_key= my_api_key, # DASHSCOPE_API_KEY
        base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    )

    base64_image = encode_image_to_base64(image_path)

    if data_type == 'RAG':
        # Obtain additional context from RAG
        csv_path="equipment_iso.csv"
        rag_context = retrieve_relevant_data(prompt, csv_path)

        # Formulate context for the model
        rag_prompt = "Use the following information about available equipment and standards:\n"
        for item in rag_context:
            rag_prompt += (
                f"- Equipment: {item['Equipment category']}, "
                f"ISO: {item['ISO']}, Name of ISO: {item['Name of ISO']}\n"
            )

        full_prompt = prompt + "\n\n" + rag_prompt
    else:
        full_prompt = prompt

    completion = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user","content": [
                {"type": "text","text": full_prompt},
                {"type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}]
        )
    return completion.choices[0].message.content


def run_mistral(api_key, image_path, prompt, data_type):
    try:
        response = generate_response_from_image_mistral(image_path, prompt, api_key, data_type)
        return response
    except Exception as e:
        print(f"An error occurred: {str(e)}")


def run_qwen(api_key, model_name, image_path, prompt, data_type):
    try:
        response = generate_response_from_image_qwen(image_path, model_name, prompt, api_key, data_type)
        return response
    except Exception as e:
        print(f"An error occurred: {str(e)}")


def create_json_with_mistral(object_dirpath, prompt_path, output_path, api_key_mistral, data_type):
    json_data = {}
    api_key =api_key_mistral

    with open(prompt_path, "r", encoding="utf-8") as file:
        prompt = file.read()

    for dirpath, dirnames, filenames in os.walk(object_dirpath):
        for file_path in filenames:
          path = os.path.join(dirpath, file_path)
          part_number = file_path.split(".")[0]

          response = run_mistral(api_key, path, prompt, data_type)
          json_data[part_number] = response

    with open(output_path, 'wb') as f:
        pickle.dump(json_data, f)


def create_json_with_qwen(api_key, model, object_dirpath, prompt_path, output_path, data_type):
    json_data = {}

    with open(prompt_path, "r", encoding="utf-8") as file:
        prompt = file.read()

    for dirpath, dirnames, filenames in os.walk(object_dirpath):
        for file_path in filenames:
          path = os.path.join(dirpath, file_path)
          part_number = file_path.split(".")[0]

          response = run_qwen(api_key, model, path, prompt, data_type)
          json_data[part_number] = response

    with open(output_path, 'wb') as f:
        pickle.dump(json_data, f)


def save_jsons(json_pkl_paths, json_collages_paths):
    for i in range(len(json_pkl_paths)):
        json_data = pickle.load(open(json_pkl_paths[i], 'rb'))
        for key, value in json_data.items():
            cleaned_json = value.strip().replace('json', '').replace('```', '').strip()
            json_data = json.loads(cleaned_json)
            output_path = os.path.join(json_collages_paths[i], f"{key}.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)


def llm_benchmark(api_key_qwen, api_key_mistral):
    object_path3, object_path4, object_path6 = './example_material/collages_3', './example_material/collages_4', './example_material/collages_6'

    for type in ['results_no_rag', 'results_rag']:
        data_type = 'RAG' if type == 'results_rag' else 'NO_RAG'
        
        mistral_pkl_path3 = f"./{type}/json_responses/json_mistral_3.pkl"
        mistral_pkl_path4 = f"./{type}/json_responses/json_mistral_4.pkl"
        mistral_pkl_path6 = f"./{type}/json_responses/json_mistral_6.pkl"

        vl_max_pkl_path3 = f"./{type}/json_responses/json_qwen_vl_max_3.pkl"
        vl_max_pkl_path4 = f"./{type}/json_responses/json_qwen_vl_max_4.pkl"
        vl_max_pkl_path6 = f"./{type}/json_responses/json_qwen_vl_max_6.pkl"

        qwen_72b_pkl_path3 = f"./{type}/json_responses/json_qwen2_vl_72b_instruct_3.pkl"
        qwen_72b_pkl_path4 = f"./{type}/json_responses/json_qwen2_vl_72b_instruct_4.pkl"
        qwen_72b_pkl_path6 = f"./{type}/json_responses/json_qwen2_vl_72b_instruct_6.pkl"

        create_json_with_mistral(object_path3, prompt_path3, mistral_pkl_path3, api_key_mistral, data_type)
        create_json_with_mistral(object_path4, prompt_path4, mistral_pkl_path4, api_key_mistral, data_type)
        create_json_with_mistral(object_path6, prompt_path6, mistral_pkl_path6, api_key_mistral, data_type)

        create_json_with_qwen(api_key_qwen, "qwen-vl-max", object_path3, prompt_path3, vl_max_pkl_path3, data_type)
        create_json_with_qwen(api_key_qwen, "qwen-vl-max", object_path4, prompt_path4, vl_max_pkl_path4, data_type)
        create_json_with_qwen(api_key_qwen, "qwen-vl-max", object_path6, prompt_path6, vl_max_pkl_path6, data_type)


        create_json_with_qwen(api_key_qwen, "qwen2.5-vl-72b-instruct", object_path3, prompt_path3, qwen_72b_pkl_path3, data_type)
        create_json_with_qwen(api_key_qwen, "qwen2.5-vl-72b-instruct", object_path4, prompt_path4, qwen_72b_pkl_path4, data_type)
        create_json_with_qwen(api_key_qwen, "qwen2.5-vl-72b-instruct", object_path6, prompt_path6, qwen_72b_pkl_path6, data_type)

        save_jsons([qwen_72b_pkl_path3, qwen_72b_pkl_path4, qwen_72b_pkl_path6], [f"./{type}/json_responses/qwen2_5_vl_72b/collages_3", 
                                                                                f"./{type}/json_responses/qwen2_5_vl_72b/collages_4", 
                                                                                f"./{type}/json_responses/qwen2_5_vl_72b/collages_6"])

        save_jsons([vl_max_pkl_path3, vl_max_pkl_path4, vl_max_pkl_path6], [f"./{type}/json_responses/qwen_vl_max/collages_3", 
                                                                            f"./{type}/json_responses/qwen_vl_max/collages_4", 
                                                                            f"./{type}/json_responses/qwen_vl_max/collages_6"])

        save_jsons([mistral_pkl_path3, mistral_pkl_path4, mistral_pkl_path6], [f"./{type}/json_responses/pixtral_12b/collages_3", 
                                                                            f"./{type}/json_responses/pixtral_12b/collages_4",
                                                                            f"./{type}/json_responses/pixtral_12b/collages_6"])