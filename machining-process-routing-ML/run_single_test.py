import os
from llm_benchmarks import create_json_with_qwen, save_jsons

QWEN_API_KEY = os.getenv("QWEN_API_KEY")

input_dir = "./example_material/test_collage_6"
prompt_path = "./example_material/prompts/prompt_6.txt"

pkl_path = "./single_test/json_responses/json_qwen_vl_max_test.pkl"
json_out_dir = "./single_test/json_responses/qwen_vl_max/collages_6"

create_json_with_qwen(
    api_key=QWEN_API_KEY,
    model="qwen-vl-max",
    object_dirpath=input_dir,
    prompt_path=prompt_path,
    output_path=pkl_path,
    data_type="RAG",
)

save_jsons(
    [pkl_path],
    [json_out_dir],
)

print(f"Saved JSON to: {json_out_dir}")