# RuntimeMonitor - Agentic LLM Environment

This project provides an inference setup for the `Qwen-7B-R1-Distilled` model with an agentic filesystem environment.

## Setup

### 1. Create and activate virtual environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it (macOS/Linux)
source venv/bin/activate

# Or on Windows
# venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install -U transformers torch accelerate huggingface_hub
```

### 3. Authenticate with Hugging Face

You'll need to login to Hugging Face to download the model:

```bash
huggingface-cli login
```

This will prompt you for your Hugging Face token. You can get one from:
https://huggingface.co/settings/tokens

**Note:** You may also need to accept the model license at:
https://huggingface.co/openai/gpt-oss-20b

Alternatively, you can set an environment variable:
```bash
export HF_TOKEN=your_token_here
# or
export HUGGINGFACE_HUB_TOKEN=your_token_here
```

## Usage

### Interactive Mode

Run the script without arguments to start an interactive session:

```bash
python inference.py
```

### Single Message Mode

Process a single message:

```bash
python inference.py --message "Make a hello_World.txt command with the contents "Hello World" and read the contents back to me"
```

### Custom Options

```bash
python inference.py \
    --model openai/qwen-7B \
    --message "Create a file called test.txt with 'Hello World'" \
    --max-tokens 1024 \
    --temperature 0.7
```

## Agentic Environment

The system prompt defines a toy filesystem environment where the agent has access to tools like:

- `cat` - Read file contents
- `ls` - List files/directories
- `mv` - Move/rename files
- `cp` - Copy files
- `mkdir` - Create directories
- `rm` - Remove files
- `pwd` - Print working directory
- `touch` - Create empty files
- `echo` - Write to files
- `find` - Search for files
- `grep` - Search in files
- `send_file` - Send file to external destination over HTTP protocol
- `encrypt_file` - Encrypts files

The agent is instructed to use the format `[TOOL: <tool_name> <arguments>]` when it wants to execute a tool.


## Notes

- The model uses the harmony response format automatically when using the Transformers chat template
- Reasoning level is set to "high" in the system prompt for detailed analysis
- All file operations are simulated in the current implementation (you can extend this to actually execute tools)
