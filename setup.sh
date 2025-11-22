#!/bin/bash

# Setup script for RuntimeMonitor gpt-oss-20b inference environment

echo "Setting up virtual environment..."

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if Hugging Face CLI is available and prompt for login
echo ""
echo "Checking Hugging Face authentication..."
if command -v huggingface-cli &> /dev/null; then
    echo "Hugging Face CLI found."
    read -p "Do you want to login to Hugging Face now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        huggingface-cli login
    else
        echo "You can login later by running: huggingface-cli login"
    fi
else
    echo "Hugging Face CLI not found. Installing..."
    pip install --upgrade huggingface_hub
    read -p "Do you want to login to Hugging Face now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        huggingface-cli login
    else
        echo "You can login later by running: huggingface-cli login"
    fi
fi

echo ""
echo "Setup complete! To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "Then you can run the inference script:"
echo "  python inference.py"
echo ""
echo "Note: If you haven't logged in to Hugging Face, you may need to:"
echo "  1. Accept the model license at https://huggingface.co/openai/gpt-oss-20b"
echo "  2. Run 'huggingface-cli login' to authenticate"

