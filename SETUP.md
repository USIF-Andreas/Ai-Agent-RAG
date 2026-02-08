# LangChain RAG AI Agent with Local LLM

A Flask-based AI Agent that uses LangChain to read from local documents and generate responses using locally-hosted language models (no external APIs).

## Features

✅ **User Authentication** - Register and login required to use the agent
✅ **Local LLM** - Uses Ollama for running models locally
✅ **RAG (Retrieval Augmented Generation)** - Reads from local documents
✅ **Vector Database** - Uses ChromaDB for document embeddings
✅ **Web Interface** - Beautiful chat interface
✅ **No API Keys** - Everything runs locally

## Architecture

```
Flask App
├── User Authentication (SQLAlchemy)
├── API Endpoints
└── LangChain RAG Agent
    ├── Document Loader (from /documents)
    ├── Text Splitter
    ├── Ollama Embeddings
    ├── ChromaDB Vector Store
    └── Local LLM (Ollama)
```

## Prerequisites

1. **Python 3.8+**
2. **Ollama** - Download from https://ollama.ai
3. **pip** - Python package manager

## Setup Instructions

### 1. Install Ollama

Download and install Ollama from https://ollama.ai

After installation, start Ollama in a terminal:
```bash
ollama serve
```

By default, Ollama runs on `http://localhost:11434`

### 2. Pull a Language Model

In another terminal, pull a model (Mistral is recommended for speed):
```bash
ollama pull mistral
```

Other available models:
- `ollama pull llama2` - Meta's Llama 2 (larger, more capable)
- `ollama pull neural-chat` - Intel's Neural Chat (smaller, faster)
- `ollama pull orca-mini` - Small and fast

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize the Database

```bash
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database initialized!')"
```

### 5. Add Documents

Place your text documents in the `documents/` directory:
```bash
# Example: Add a document
echo "Your content here" > documents/sample.txt
```

The system automatically loads all `.txt` files from the `documents/` folder.

### 6. Run the Application

```bash
python app.py
```

The app will be available at: `http://localhost:5000`

## Usage

1. **Register** - Create a new account
2. **Login** - Use your credentials to log in
3. **Chat** - Ask questions about your documents
4. **Add Documents** - Add more `.txt` files to `documents/` folder

## Adding Documents

### Method 1: Add Text Files Directly
```bash
cp your_document.txt documents/
```

### Method 2: Create Documents via Python
```python
from app import rag_agent

# Add a document
content = """
Your document content here...
"""
rag_agent.add_document(content, filename="my_doc.txt")
```

## API Endpoints

### Authentication
- `GET /` - Redirect to login/chat
- `GET /login` - Login page
- `POST /login` - Submit login
- `GET /register` - Register page
- `POST /register` - Submit registration
- `GET /logout` - Logout

### Chat (Requires Login)
- `GET /chat` - Chat interface
- `POST /api/query` - Query the RAG agent

## Configuration

Edit the model name in `agent.py`:
```python
rag_agent = RAGAgent(docs_dir="documents", model_name="mistral")
```

Environment variables (optional):
```bash
export SECRET_KEY="your-secret-key-for-production"
```

## Troubleshooting

### Ollama Connection Error
- Make sure Ollama is running: `ollama serve`
- Check if it's accessible: `curl http://localhost:11434`

### Model Not Found
```bash
# List available models
ollama list

# Pull a model
ollama pull mistral
```

### Database Issues
```bash
# Reset database
rm users.db
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### ChromaDB Cache Issues
```bash
# Clear vector store cache
rm -rf chroma_db/
```

## Performance Tips

1. **Use smaller models for speed**: neural-chat, orca-mini
2. **Use larger models for accuracy**: llama2, mistral
3. **Adjust chunk size** in `agent.py` for better context
4. **Increase search k** for more relevant results

## File Structure

```
codespaces-flask/
├── app.py                 # Main Flask application
├── agent.py              # LangChain RAG Agent
├── requirements.txt      # Python dependencies
├── documents/            # Your documents go here
├── chroma_db/            # Vector database (auto-created)
├── users.db              # SQLite user database (auto-created)
├── templates/
│   ├── login.html        # Login page
│   ├── register.html     # Registration page
│   └── chat.html         # Chat interface
└── static/
    └── main.css          # Stylesheet
```

## Security Notes

⚠️ **For Production:**
- Change the `SECRET_KEY` in app.py
- Use a production database (PostgreSQL)
- Enable HTTPS
- Validate and sanitize user inputs
- Set up rate limiting

## License

MIT

## Support

For issues or questions, check:
1. Ollama is running on localhost:11434
2. Models are installed with `ollama list`
3. Documents are in the `documents/` folder as `.txt` files
4. Database is properly initialized
