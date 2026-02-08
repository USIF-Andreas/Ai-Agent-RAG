# RAG AI Agent (Flask + Ollama)

![Python](https://img.shields.io/badge/python-3.12-blue)
![Flask](https://img.shields.io/badge/flask-2.3.x-black)
![LangChain](https://img.shields.io/badge/langchain-0.1.x-2f6feb)
![Ollama](https://img.shields.io/badge/ollama-local%20LLM-16a34a)
![FAISS](https://img.shields.io/badge/vector%20store-FAISS-ef4444)

A local RAG (Retrieval-Augmented Generation) agent that indexes your documents and answers questions via a fast chat UI. Uses Ollama for local inference and FAISS for vector search.

## Features
- Local LLM via Ollama (no external API calls)
- RAG pipeline with document retrieval
- PDF and TXT ingestion
- FAISS index caching for faster restarts
- Colorful, modern chat UI

## Tech Stack
- Flask
- LangChain + langchain-community
- Ollama
- FAISS
- PyPDF

## Requirements
- Python 3.12+
- Ollama installed and running

## Setup
```bash
pip install -r requirements.txt
```

Pull the default model:
```bash
ollama pull phi3:mini
```

Start Ollama:
```bash
ollama serve
```

## Run
```bash
python app.py
```

Open the app at:
```
http://localhost:5000
```

## Add Documents
Place files in the `documents/` folder:
- `.txt`
- `.pdf`

On first run, the app builds a FAISS index. Subsequent runs load the cached index for faster startup. If you change documents, rebuild the index by deleting the cached folder:
```
documents/faiss_index_*
```

## Notes
- If you switch models, a new FAISS index is created automatically.
- Long responses may take time depending on model size and hardware.

## Troubleshooting
- Ollama must be running: `ollama serve`
- Ensure the model is pulled: `ollama pull phi3:mini`
- If you see FAISS dimension errors, remove the old cache and restart.

---
Built for local, private document QA.
![App Screenshot](Ai-Agent-RAG/Screenshot 2026-02-08 112042.png)
