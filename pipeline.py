"""
End-to-end pipeline: load prompts, run generation, and cache tool-call activations.

Prompts are loaded from data/prompts (good/bad). For each prompt, we:
1) Run inference and store generation JSONL under data/generations/{category}/generations.jsonl
2) Teacher-force the generation to extract tool-call activations and store them under
   data/activations/{category}/activations.jsonl
"""

import argparse
import csv
import json
import os
from typing import Dict, List, Optional, Tuple

from inference import AgenticInference
from activations import collect_tool_activations, resolve_hf_token
from transformers import AutoModelForCausalLM, AutoTokenizer

DEFAULT_PROMPT_CANDIDATES = {
    "good": [
        "data/prompts/good.jsonl",
        "data/prompts/good.csv",
        "data/prompts/good.txt",
    ],
    "bad": [
        "data/prompts/bad.jsonl",
        "data/prompts/bad.csv",
        "data/prompts/bad.txt",
    ],
}


def choose_prompt_file(category: str, override: Optional[str]) -> Optional[str]:
    """Pick the prompt file to use for a category."""
    if override:
        return override if os.path.exists(override) else None
    for candidate in DEFAULT_PROMPT_CANDIDATES.get(category, []):
        if os.path.exists(candidate):
            return candidate
    return None


def extract_prompt(record) -> Optional[str]:
    """Extract prompt text from a record."""
    if isinstance(record, str):
        return record.strip() or None
    if not isinstance(record, dict):
        return None
    for key in ("prompt", "text", "message", "content"):
        if key in record and isinstance(record[key], str):
            return record[key]
    return None


def load_prompts(path: str) -> List[str]:
    """Load prompts from jsonl, json, csv, or txt."""
    prompts: List[str] = []
    _, ext = os.path.splitext(path.lower())

    if ext == ".jsonl":
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                prompt = extract_prompt(record)
                if prompt:
                    prompts.append(prompt)
    elif ext == ".json":
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, list):
            for item in payload:
                prompt = extract_prompt(item)
                if prompt:
                    prompts.append(prompt)
        else:
            prompt = extract_prompt(payload)
            if prompt:
                prompts.append(prompt)
    elif ext == ".csv":
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames:
                preferred = [c for c in reader.fieldnames if c.lower() in ("prompt", "text", "message", "content")]
                target_col = preferred[0] if preferred else reader.fieldnames[0]
                for row in reader:
                    val = row.get(target_col, "")
                    if val:
                        prompts.append(val)
            else:
                # No header; fallback to first column
                f.seek(0)
                raw_reader = csv.reader(f)
                for row in raw_reader:
                    if row and row[0]:
                        prompts.append(row[0])
    else:
        # Treat as plain text, one prompt per line
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    prompts.append(line.strip())

    return prompts


def ensure_dirs(*paths: str):
    for path in paths:
        os.makedirs(path, exist_ok=True)


def write_jsonl(path: str, record: Dict):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def run_pipeline(
    prompts_by_category: Dict[str, List[str]],
    model_id: str,
    layer_index: int,
    max_tokens: int,
    temperature: float,
):
    """Run generation then activations for each prompt."""
    # Reuse the same model/tokenizer for activations
    hf_token = resolve_hf_token(True)
    tokenizer = AutoTokenizer.from_pretrained(model_id, token=hf_token)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype="auto",
        device_map="auto",
        token=hf_token,
    )

    agent = AgenticInference(model_id=model_id)

    for category, prompts in prompts_by_category.items():
        if not prompts:
            continue

        gen_dir = os.path.join("data", "generations", category)
        act_dir = os.path.join("data", "activations", category)
        ensure_dirs(gen_dir, act_dir)

        gen_path = os.path.join(gen_dir, "generations.jsonl")
        act_path = os.path.join(act_dir, "activations.jsonl")
        prompt_path = os.path.join("data", "prompts", f"{category}_used.jsonl")
        ensure_dirs(os.path.dirname(prompt_path))

        for idx, prompt in enumerate(prompts):
            print(f"\n[{category}] Prompt {idx+1}/{len(prompts)}")
            generation = agent.run_inference(
                prompt,
                max_new_tokens=max_tokens,
                temperature=temperature,
                save_path=None,  # We write our own structured record below
            )

            gen_record = {
                "category": category,
                "prompt_index": idx,
                "prompt": prompt,
                "generation": generation,
            }
            write_jsonl(gen_path, gen_record)
            write_jsonl(prompt_path, {"category": category, "prompt_index": idx, "prompt": prompt})

            tool_activations = collect_tool_activations(
                generation, tokenizer, model, layer_index=layer_index
            )
            for entry in tool_activations:
                entry.update(
                    {
                        "category": category,
                        "prompt_index": idx,
                        "prompt": prompt,
                        "generation": generation,
                    }
                )
                write_jsonl(act_path, entry)

        print(f"[{category}] Saved generations to {gen_path} and activations to {act_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline: run inference and cache tool-call activations for good/bad prompt sets."
    )
    parser.add_argument(
        "--model",
        type=str,
        default="deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
        help="Model identifier to load.",
    )
    parser.add_argument(
        "--layer",
        type=int,
        default=20,
        help="Hidden state layer index to store (0-based, can be negative).",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Maximum number of tokens to generate per prompt.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature.",
    )
    parser.add_argument(
        "--good-file",
        type=str,
        help="Override path for good prompts file.",
    )
    parser.add_argument(
        "--bad-file",
        type=str,
        help="Override path for bad prompts file.",
    )
    parser.add_argument(
        "--num-good",
        type=int,
        help="Limit number of good prompts to run (default: all).",
    )
    parser.add_argument(
        "--num-bad",
        type=int,
        help="Limit number of bad prompts to run (default: all).",
    )

    args = parser.parse_args()

    prompts_by_category: Dict[str, List[str]] = {}
    for category, override, limit in (
        ("good", args.good_file, args.num_good),
        ("bad", args.bad_file, args.num_bad),
    ):
        prompt_file = choose_prompt_file(category, override)
        if prompt_file:
            prompts_by_category[category] = load_prompts(prompt_file)
            if limit is not None:
                prompts_by_category[category] = prompts_by_category[category][:limit]
            print(f"Loaded {len(prompts_by_category[category])} {category} prompts from {prompt_file}")
        else:
            prompts_by_category[category] = []
            print(f"No {category} prompt file found. Skipping category.")

    # Ensure we have at least one prompt
    total_prompts = sum(len(v) for v in prompts_by_category.values())
    if total_prompts == 0:
        raise ValueError("No prompts loaded. Provide good/bad prompt files under data/prompts or via CLI.")

    run_pipeline(
        prompts_by_category=prompts_by_category,
        model_id=args.model,
        layer_index=args.layer,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
    )


if __name__ == "__main__":
    main()
