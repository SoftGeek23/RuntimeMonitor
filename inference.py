"""
Inference script for gpt-oss-20b with agentic filesystem environment.

This script sets up an agentic environment where the model has access to
filesystem tools like cat, mv, cp, ls, mkdir, etc.
"""

from transformers import pipeline
import torch
import json
import os
from typing import List, Dict, Optional
from huggingface_hub import login as hf_login

# Set PyTorch CUDA memory allocation configuration to reduce fragmentation
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

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
- Provide clear, natural language responses"""


class AgenticInference:
    """Wrapper for running agentic inference with gpt-oss-20b."""
    
    def __init__(
        self, 
        model_id: str = "openai/gpt-oss-20b", 
        use_auth_token: bool = True,
        max_memory: Optional[Dict] = None,
        offload_buffers: bool = True,
        low_cpu_mem_usage: bool = True
    ):
        """
        Initialize the inference pipeline.
        
        Args:
            model_id: Hugging Face model identifier
            use_auth_token: Whether to use Hugging Face authentication token
            max_memory: Maximum memory to use per device (e.g., {0: "40GiB", "cpu": "100GiB"})
            offload_buffers: Whether to offload buffers to CPU to save GPU memory
            low_cpu_mem_usage: Whether to use low CPU memory usage mode
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
        
        # Clear GPU cache to free up memory and check available memory
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            total_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
            allocated_memory = torch.cuda.memory_allocated(0) / (1024**3)  # GB
            reserved_memory = torch.cuda.memory_reserved(0) / (1024**3)  # GB
            free_memory = total_memory - reserved_memory
            
            print(f"GPU Memory Status:")
            print(f"  Total: {total_memory:.2f} GB")
            print(f"  Reserved: {reserved_memory:.2f} GB")
            print(f"  Free: {free_memory:.2f} GB")
            
            # Warn if memory is low
            if free_memory < 5.0:
                print(f"\n⚠️  WARNING: Low GPU memory detected ({free_memory:.2f} GB free)")
                print("   Consider:")
                print("   1. Closing other GPU processes (check with: nvidia-smi)")
                print("   2. Using CPU offloading (already enabled)")
                print("   3. Restarting to clear GPU memory\n")
        
        # Configure memory settings if not provided
        if max_memory is None:
            # Try to get available GPU memory and set a conservative limit
            if torch.cuda.is_available():
                # Use actual free memory, not total memory
                total_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
                reserved_memory = torch.cuda.memory_reserved(0) / (1024**3)  # GB
                free_memory = total_memory - reserved_memory
                
                # If there's significant memory already in use, be very conservative
                # Dequantization needs extra memory (typically 1-2GB), so we need to reserve that
                if reserved_memory > 1.0:  # More than 1GB already reserved
                    # Reserve 2GB for dequantization operations, use only 60% of remaining free memory
                    dequantization_buffer = 2.0  # GB
                    available_for_model = max(0, free_memory - dequantization_buffer)
                    max_gpu_memory = f"{int(available_for_model * 0.60)}GiB"
                    print(f"⚠️  GPU memory already in use ({reserved_memory:.2f} GB).")
                    print(f"   Using very conservative limit: {max_gpu_memory} (reserving {dequantization_buffer} GB for dequantization)")
                    if available_for_model < 5.0:
                        print(f"   ⚠️  Very little GPU memory available. Model will be heavily offloaded to CPU.")
                else:
                    # Use 80% of total memory if GPU is mostly free (reserve 20% for dequantization)
                    max_gpu_memory = f"{int(total_memory * 0.80)}GiB"
                    print(f"GPU is mostly free. Using limit: {max_gpu_memory}")
                
                max_memory = {0: max_gpu_memory, "cpu": "100GiB"}
                print(f"Auto-configured max_memory: GPU={max_gpu_memory}, CPU=100GiB")
        
        pipeline_kwargs = {
            "task": "text-generation",
            "model": model_id,
            "torch_dtype": "auto",
            "device_map": "auto",
            "token": hf_token if use_auth_token else None,
            "model_kwargs": {
                "low_cpu_mem_usage": low_cpu_mem_usage,
                "offload_buffers": offload_buffers,
            }
        }
        
        if max_memory:
            pipeline_kwargs["model_kwargs"]["max_memory"] = max_memory
        
        try:
            print("Initializing pipeline (this may take a while for large models)...")
            self.pipe = pipeline(**pipeline_kwargs)
            print("Model loaded successfully!")
        except torch.cuda.OutOfMemoryError as e:
            print("\n❌ CUDA Out of Memory Error!")
            print("\nTroubleshooting steps:")
            print("1. Check GPU memory usage: nvidia-smi")
            print("2. Kill other processes using GPU: kill <PID>")
            print("3. Try reducing max_memory limit")
            print("4. Restart Python to clear GPU memory")
            print(f"\nError details: {e}")
            raise
        except Exception as e:
            print(f"\n❌ Error loading model: {e}")
            if "out of memory" in str(e).lower() or "OOM" in str(e):
                print("\nMemory-related error detected. Try:")
                print("1. Freeing GPU memory (check with: nvidia-smi)")
                print("2. Using a smaller model or more aggressive CPU offloading")
            raise
    
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
        max_new_tokens: int = 2048,
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
        
        # Extract the generated text
        generated = outputs[0]["generated_text"]
        
        # When using messages format, the pipeline returns a list of messages
        # We need to extract the assistant's response (last message with role="assistant")
        if isinstance(generated, list):
            # Find the last assistant message
            assistant_messages = [msg for msg in generated if msg.get("role") == "assistant"]
            if assistant_messages:
                response = assistant_messages[-1].get("content", "")
            else:
                # If no assistant message found, try to get the last message's content
                response = generated[-1].get("content", "") if generated else ""
        elif isinstance(generated, str):
            # Already a string, use it directly
            response = generated
        elif isinstance(generated, dict):
            # If it's a dict, get the content field
            response = generated.get("content", generated.get("generated_text", str(generated)))
        else:
            # Fallback to string conversion
            response = str(generated) if generated else ""
        
        # Clean up weird formatting artifacts from the model output
        response = response.strip() if response else ""
        
        # Remove "analysis" prefix if present
        if response.startswith("analysis"):
            response = response[8:].strip()  # Remove "analysis" (8 chars)
        
        # Remove artifacts like "assistantcommentary", "repo_browser.exec", JSON structures
        # Find where the useful text ends (before artifacts start)
        artifact_markers = [
            "assistantcommentary",
            "repo_browser",
            "exec code",
            "json{",
            "to=tool.",
            "to=repo_browser"
        ]
        
        # Find the earliest artifact marker
        earliest_artifact_pos = len(response)
        for marker in artifact_markers:
            pos = response.find(marker)
            if pos != -1 and pos < earliest_artifact_pos:
                earliest_artifact_pos = pos
        
        # If we found artifacts, truncate at that position
        if earliest_artifact_pos < len(response):
            response = response[:earliest_artifact_pos].strip()
        
        # Clean up any remaining artifacts on each line
        if response:
            lines = response.split('\n')
            cleaned_lines = []
            for line in lines:
                # Skip lines that are purely artifacts
                if any(x in line.lower() for x in ["assistantcommentary", "repo_browser", "exec code", "json{", "to=tool", "to=repo"]):
                    # Check if this line has any actual content before the artifact
                    for marker in artifact_markers:
                        if marker in line:
                            # Extract content before the marker
                            before_marker = line[:line.find(marker)].strip()
                            if before_marker:
                                cleaned_lines.append(before_marker)
                            break
                else:
                    cleaned_lines.append(line)
            response = '\n'.join(cleaned_lines).strip()
        
        # Final cleanup: remove any trailing punctuation artifacts
        response = response.rstrip('.,;:')
        
        print(response)
        print(f"\n{'='*60}\n")
        
        return response
    
    def interactive_mode(self, include_system: bool = True):
        """Run an interactive chat session."""
        print("\n" + "="*60)
        print("Interactive Mode")
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
                
                self.run_inference(user_input, include_system=include_system)
                
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
        default=2048,
        help="Maximum number of tokens to generate"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature"
    )
    parser.add_argument(
        "--no-system-prompt",
        action="store_true",
        help="Disable system prompt for pure inference"
    )
    
    args = parser.parse_args()
    
    # Initialize the inference wrapper with memory optimizations
    # The constructor will auto-configure max_memory based on available GPU
    agent = AgenticInference(
        model_id=args.model,
        offload_buffers=True,  # Offload buffers to CPU to save GPU memory
        low_cpu_mem_usage=True  # Use low CPU memory mode
    )
    
    if args.message:
        # Single message mode
        agent.run_inference(
            args.message,
            max_new_tokens=args.max_tokens,
            temperature=args.temperature,
            include_system=not args.no_system_prompt
        )
    else:
        # Interactive mode
        agent.interactive_mode(include_system=not args.no_system_prompt)


if __name__ == "__main__":
    main()


