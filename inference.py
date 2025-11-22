"""
Inference script for gpt-oss-20b with agentic filesystem environment.

This script sets up an agentic environment where the model has access to
filesystem tools like cat, mv, cp, ls, mkdir, etc.
"""

from transformers import pipeline
import torch
import json
import os
from typing import List, Dict
from huggingface_hub import login as hf_login

# System prompt defining the agentic filesystem environment
SYSTEM_PROMPT = """You are an AI agent operating in a controlled filesystem environment. You have access to the following tools:

**Available Filesystem Tools:**
- `cat <file>` - Read and display the contents of a file
- `ls [directory]` - List files and directories (defaults to current directory)
- `mv <source> <destination>` - Move or rename files/directories
- `cp <source> <destination>` - Copy files/directories
- `mkdir <directory>` - Create a new directory
- `rm <file>` - Remove a file
- `rmdir <directory>` - Remove an empty directory
- `pwd` - Print the current working directory
- `touch <file>` - Create an empty file or update its timestamp
- `echo <text> > <file>` - Write text to a file
- `find <directory> -name <pattern>` - Find files matching a pattern
- `grep <pattern> <file>` - Search for patterns in a file

**Environment Rules:**
1. You operate in a sandboxed filesystem environment at `/workspace`
2. All file operations are simulated and safe
3. When you want to use a tool, format your response as: `[TOOL: <tool_name> <arguments>]`
4. After tool execution, you'll receive the result and can continue reasoning
5. You can chain multiple tool calls in sequence
6. Always verify file operations before executing them
7. Use reasoning to plan your actions before executing tools

**Response Format:**
- Use chain-of-thought reasoning to plan your actions
- Clearly indicate when you're using a tool with the `[TOOL: ...]` format
- Explain your reasoning process before and after tool usage

Reasoning: high"""


class AgenticInference:
    """Wrapper for running agentic inference with gpt-oss-20b."""
    
    def __init__(self, model_id: str = "openai/gpt-oss-20b", use_auth_token: bool = True):
        """
        Initialize the inference pipeline.
        
        Args:
            model_id: Hugging Face model identifier
            use_auth_token: Whether to use Hugging Face authentication token
        """
        # Check for Hugging Face token
        hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
        
        if use_auth_token and not hf_token:
            # Try to get token from Hugging Face cache
            try:
                from huggingface_hub import HfFolder
                hf_token = HfFolder.get_token()
            except:
                pass
        
        print(f"Loading model {model_id}...")
        print("Note: The model will be downloaded from Hugging Face Hub on first run.")
        
        self.pipe = pipeline(
            "text-generation",
            model=model_id,
            torch_dtype="auto",
            device_map="auto",
            token=hf_token if use_auth_token else None,
        )
        print("Model loaded successfully!")
    
    def format_messages(self, user_message: str, include_system: bool = True) -> List[Dict]:
        """
        Format messages for the model with system prompt.
        
        Args:
            user_message: The user's message/query
            include_system: Whether to include the system prompt
            
        Returns:
            Formatted messages list
        """
        messages = []
        
        if include_system:
            messages.append({
                "role": "system",
                "content": SYSTEM_PROMPT
            })
        
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        return messages
    
    def run_inference(
        self,
        user_message: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        include_system: bool = True
    ) -> str:
        """
        Run inference on a user message.
        
        Args:
            user_message: The user's query
            max_new_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            include_system: Whether to include the system prompt
            
        Returns:
            Generated response text
        """
        messages = self.format_messages(user_message, include_system)
        
        print(f"\n{'='*60}")
        print("USER MESSAGE:")
        print(f"{'='*60}")
        print(user_message)
        print(f"\n{'='*60}")
        print("AGENT RESPONSE:")
        print(f"{'='*60}\n")
        
        outputs = self.pipe(
            messages,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            return_full_text=False,
        )
        
        response = outputs[0]["generated_text"]
        
        # Extract the assistant's response (last message)
        if isinstance(response, list):
            response = response[-1].get("content", str(response))
        elif isinstance(response, dict):
            response = response.get("content", str(response))
        
        print(response)
        print(f"\n{'='*60}\n")
        
        return response
    
    def interactive_mode(self):
        """Run an interactive chat session."""
        print("\n" + "="*60)
        print("Agentic Filesystem Environment - Interactive Mode")
        print("Type 'exit' or 'quit' to end the session")
        print("="*60 + "\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("\nExiting interactive mode. Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                self.run_inference(user_input)
                
            except KeyboardInterrupt:
                print("\n\nExiting interactive mode. Goodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}\n")


def main():
    """Main function to run inference."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run inference with gpt-oss-20b in an agentic filesystem environment"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="openai/gpt-oss-20b",
        help="Hugging Face model identifier"
    )
    parser.add_argument(
        "--message",
        type=str,
        help="Single message to process (if not provided, runs in interactive mode)"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Maximum number of tokens to generate"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature"
    )
    
    args = parser.parse_args()
    
    # Initialize the inference wrapper
    agent = AgenticInference(model_id=args.model)
    
    if args.message:
        # Single message mode
        agent.run_inference(
            args.message,
            max_new_tokens=args.max_tokens,
            temperature=args.temperature
        )
    else:
        # Interactive mode
        agent.interactive_mode()


if __name__ == "__main__":
    main()

