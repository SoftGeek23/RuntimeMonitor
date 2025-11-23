"""
Extract tool-call activations from stored model generations.

This script loads raw generations, teacher-forces them through the model,
and captures the final-token activations for each `[TOOL: ...]` call.
"""

import argparse
import json
import os
import re
from typing import Dict, Iterable, List, Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from huggingface_hub import HfFolder

# Tool call syntax is defined in inference.py's system prompt
TOOL_PATTERN = re.compile(r"\[TOOL:\s*[^]]+\]")


def resolve_hf_token(use_auth_token: bool) -> Optional[str]:
    """Resolve the Hugging Face token similarly to inference.py."""
    if not use_auth_token:
        return None

    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
    if token:
        return token

    try:
        return HfFolder.get_token()
    except Exception:
        return None


def load_generations(path: str) -> List[str]:
    """
    Load raw generations from disk.

    Supports:
    - JSONL: each line is a JSON object containing one of the keys
      ["generation", "generated_text", "text", "response"].
    - JSON: list of strings or list of dicts with the same keys as above.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Generation file not found: {path}")

    def extract_from_record(record: Dict) -> Optional[str]:
        for key in ("generation", "generated_text", "text", "response"):
            if key in record:
                return record[key]
        return None

    generations: List[str] = []
    if path.endswith(".jsonl"):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                text = extract_from_record(record)
                if text is not None:
                    generations.append(text)
    else:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, str):
                    generations.append(item)
                elif isinstance(item, dict):
                    text = extract_from_record(item)
                    if text is not None:
                        generations.append(text)
        elif isinstance(payload, dict):
            text = extract_from_record(payload)
            if text is not None:
                generations.append(text)

    if not generations:
        raise ValueError(f"No generations loaded from {path}")

    return generations


def find_tool_calls(text: str) -> Iterable[re.Match]:
    """Yield regex matches for `[TOOL: ...]` spans."""
    return TOOL_PATTERN.finditer(text)


def locate_token_for_char(offsets: List[List[int]], char_index: int) -> Optional[int]:
    """
    Map a character index to the token position using tokenizer offsets.

    We choose the first token whose span covers the character.
    """
    for idx, (start, end) in enumerate(offsets):
        if start <= char_index < end:
            return idx
    return None


def collect_tool_activations(
    text: str,
    tokenizer: AutoTokenizer,
    model: AutoModelForCausalLM,
    layer_index: int,
) -> List[Dict]:
    """
    Teacher-force the text and collect activations at the end of each tool call.

    Returns a list of dicts with tool_call text and activation vector.
    """
    matches = list(find_tool_calls(text))
    if not matches:
        return []

    encoded = tokenizer(
        text,
        return_tensors="pt",
        return_offsets_mapping=True,
        add_special_tokens=False,
    )
    offsets = encoded.pop("offset_mapping")[0].tolist()

    device = getattr(model, "device", torch.device("cpu"))
    encoded = {k: v.to(device) if torch.is_tensor(v) else v for k, v in encoded.items()}

    model.eval()
    with torch.no_grad():
        outputs = model(**encoded, output_hidden_states=True, use_cache=False)
    hidden_states = outputs.hidden_states
    if layer_index >= len(hidden_states) or layer_index < -len(hidden_states):
        raise ValueError(
            f"Requested layer {layer_index} but model returned {len(hidden_states)} hidden states."
        )
    hidden = hidden_states[layer_index][0].cpu()

    activations = []
    for match in matches:
        start_char_index = match.start()  # beginning of "[TOOL:"
        token_idx = locate_token_for_char(offsets, start_char_index)
        if token_idx is None:
            continue
        activations.append(
            {
                "tool_call": match.group(),
                "token_index": token_idx,
                "char_range": [match.start(), match.end()],
                "layer_index": layer_index,
                "activation": hidden[token_idx].tolist(),
            }
        )

    return activations


def main():
    parser = argparse.ArgumentParser(
        description="Collect tool-call activations from stored generations."
    )
    parser.add_argument(
        "--model",
        type=str,
        default="deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
        help="Model identifier to load for teacher forcing.",
    )
    parser.add_argument(
        "--input",
        type=str,
        default="data/generations/generations.jsonl",
        help="Path to stored generations.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/activations/activations.jsonl",
        help="Destination for tool-call activations.",
    )
    parser.add_argument(
        "--layer",
        type=int,
        default=20,
        help="Hidden state layer index to store (0-based, can be negative).",
    )
    parser.add_argument(
        "--no-auth-token",
        action="store_true",
        help="Disable Hugging Face authentication token usage.",
    )

    args = parser.parse_args()
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    generations = load_generations(args.input)
    print(f"Loaded {len(generations)} generations from {args.input}")

    hf_token = resolve_hf_token(not args.no_auth_token)
    print(f"Loading model {args.model}...")
    tokenizer = AutoTokenizer.from_pretrained(args.model, token=hf_token)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype="auto",
        device_map="auto",
        token=hf_token,
    )
    print("Model loaded. Collecting activations...")

    total_pairs = 0
    with open(args.output, "w", encoding="utf-8") as writer:
        for idx, text in enumerate(generations):
            tool_activations = collect_tool_activations(
                text, tokenizer, model, layer_index=args.layer
            )
            for entry in tool_activations:
                entry["generation_index"] = idx
                writer.write(json.dumps(entry) + "\n")
            total_pairs += len(tool_activations)

    print(f"Stored {total_pairs} tool-call activations to {args.output}")


if __name__ == "__main__":
    main()
