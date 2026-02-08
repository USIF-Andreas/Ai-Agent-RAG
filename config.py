"""
Configuration file for RAG Agent
Customize settings here
"""

# LLM Settings
LLM_MODEL = "phi3:mini"  # Model to use: phi3:mini (fast), mistral (slow but accurate), llama2, neural-chat
EMBEDDINGS_MODEL = "nomic-embed-text"  # Model for embeddings (fast, optimized for this task)
OLLAMA_BASE_URL = "http://localhost:11434"

# Document Settings
DOCUMENTS_DIR = "documents"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# Search Settings
SEARCH_K = 3  # Number of documents to retrieve for each query

# Flask Settings
FLASK_ENV = "development"
DEBUG = True

# Database Settings
DATABASE_URL = "sqlite:///users.db"

# RAG Settings
USE_SOURCE_DOCUMENTS = True  # Show source documents in responses
MAX_RESPONSE_LENGTH = 700  # Maximum response length
