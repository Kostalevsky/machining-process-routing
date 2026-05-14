import argparse
import os
from dotenv import load_dotenv
from llm_benchmarks import llm_benchmark
from evaluation import evaluate


load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(description="Run local ML pipeline without client and backend.")

    parser.add_argument(
        "--stage",
        choices=["benchmark", "evaluate", "full"],
        default="full",
        help="Which stage to run.",
    )

    parser.add_argument(
        "--qwen-api-key",
        type=str,
        default=os.getenv("QWEN_API_KEY", ""),
        help="Qwen API key. Can also be provided via QWEN_API_KEY env var.",
    )

    parser.add_argument(
        "--mistral-api-key",
        type=str,
        default=os.getenv("MISTRAL_API_KEY", ""),
        help="Mistral API key. Can also be provided via MISTRAL_API_KEY env var.",
    )

    parser.add_argument(
        "--openai-api-key",
        type=str,
        default=os.getenv("OPENAI_API_KEY", ""),
        help="OpenAI API key for evaluation. Can also be provided via OPENAI_API_KEY env var.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if args.stage in {"benchmark", "full"}:
        if not args.qwen_api_key or not args.mistral_api_key:
            raise ValueError(
                "Benchmark stage requires both Qwen and Mistral API keys."
            )

        print("[local-run] Starting llm_benchmark...")
        llm_benchmark(
            api_key_qwen=args.qwen_api_key,
            api_key_mistral=args.mistral_api_key,
        )
        print("[local-run] llm_benchmark finished.")

    if args.stage in {"evaluate", "full"}:
        if not args.openai_api_key:
            raise ValueError(
                "Evaluate stage requires OpenAI API key."
            )

        print("[local-run] Starting evaluation...")
        evaluate(args.openai_api_key)
        print("[local-run] evaluation finished.")


if __name__ == "__main__":
    main()