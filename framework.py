import dim_reduction_solved_3d_model
import llm_benchmarks
import evaluation

DASHSCOPE_API_KEY = "DASHSCOPE_API_KEY"
MISTRAL_API_KEY = "MISTRAL_API_KEY"
OPENAI_API_KEY = "OPENAI_API_KEY"

dim_reduction_solved_3d_model.dim_reduction()
llm_benchmarks.llm_benchmark(DASHSCOPE_API_KEY, MISTRAL_API_KEY)
evaluation.evaluate(OPENAI_API_KEY)

