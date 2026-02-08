# Quick Start Guide - RAG AI Agent

## 5-Minute Setup

### Step 1: Install Ollama (2 minutes)
Download and install from https://ollama.ai

### Step 2: Start Services in Terminal 1
```bash
cd /workspaces/codespaces-flask
chmod +x setup.sh
./setup.sh
```

This will install all dependencies and initialize the database.

### Step 3: Start Ollama in Terminal 2
```bash
ollama serve
```

### Step 4: Pull a Model in Terminal 3
```bash
ollama pull mistral
```

Wait for it to complete (will download ~4GB)

### Step 5: Run the App in Terminal 1 (after setup.sh completes)
```bash
python app.py
```

### Step 6: Access the App
Open browser and go to: **http://localhost:5000**

## First Time Using

1. **Register** - Create an account
2. **Login** - Use your credentials
3. **Ask Questions** - The agent can answer questions about documents in the `documents/` folder
4. **Try This**: "What documents are available?"

## Add Your Own Documents

1. Create a `.txt` file with your content
2. Save it to `documents/` folder
3. Restart the app or let it reload
4. The agent will now have access to your documents

## Troubleshooting

**"Connection refused at localhost:11434"**
- Make sure `ollama serve` is running in another terminal

**"No such file: mistral"**
- Run: `ollama pull mistral` (wait for download to complete)

**Database error**
- Delete `users.db` file and restart app

**Empty responses**
- Make sure you have documents in the `documents/` folder
- Check the console for error messages

## Default Credentials for Testing

Already registered user: (Register a new account on first use)

## Model Options

Fast (recommended for testing):
```bash
ollama pull neural-chat
```

Balanced:
```bash
ollama pull mistral
```

Advanced:
```bash
ollama pull llama2
```

## Next Steps

- Add your documents to `documents/` folder
- Customize model in `agent.py` (change `model_name`)
- Adjust chunk size for different document types
- Deploy to production with proper security

## Architecture

```
You (Chat Interface) 
    ↓
Flask API
    ↓
LangChain Agent
    ↓
Document Loader → Vector Store (ChromaDB) → Ollama LLM (Local)
    ↓
Your Documents
```

All processing happens locally - no cloud services, no API keys needed!

See SETUP.md for detailed information.
