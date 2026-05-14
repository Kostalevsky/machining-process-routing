import os
from dotenv import load_dotenv
import dim_reduction_solved_3d_model
import llm_benchmarks
import evaluation


load_dotenv()

DASHSCOPE_API_KEY = os.getenv("QWEN_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DASHSCOPE_API_KEY:
    raise ValueError("Missing QWEN_API_KEY in .env")

if not MISTRAL_API_KEY:
    raise ValueError("Missing MISTRAL_API_KEY in .env")

if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY in .env")


dim_reduction_solved_3d_model.dim_reduction()
llm_benchmarks.llm_benchmark(DASHSCOPE_API_KEY, MISTRAL_API_KEY)
evaluation.evaluate(OPENAI_API_KEY)