#!/bin/bash

# RAG Agent Quick Start Script

echo "=========================================="
echo "RAG AI Agent - Quick Setup"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python 3 found"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed."
    exit 1
fi

echo "✅ pip3 found"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed"

# Initialize database
echo ""
echo "Initializing database..."
python3 -c "from app import app, db; app.app_context().push(); db.create_all(); print('✅ Database initialized!')"

if [ $? -ne 0 ]; then
    echo "❌ Failed to initialize database"
    exit 1
fi

# Create documents directory
mkdir -p documents

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Start Ollama: ollama serve"
echo "2. In another terminal, pull a model: ollama pull mistral"
echo "3. Run this app: python3 app.py"
echo "4. Open http://localhost:5000"
echo ""
echo "For detailed instructions, see SETUP.md"
