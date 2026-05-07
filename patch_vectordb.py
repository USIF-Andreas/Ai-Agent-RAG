with open("/workspaces/Ai-Agent-RAG/Document from Usif Androws (1)/ProjectTemplate/src/stores/vectordb/provider/__init__.py", "r") as f:
    content = f.read()

content = content.replace("def create_vector_store_provider(settings: Settings) -> VectorStoreProvider:", """from src.stores.vectordb.provider.faiss_provider import FaissVectorStoreProvider

def create_vector_store_provider(settings: Settings) -> VectorStoreProvider:""")

content = content.replace("    if settings.vector_store_provider.lower() == \"qdrant\":\n        return QdrantVectorStoreProvider(settings)", """    if settings.vector_store_provider.lower() == "qdrant":
        return QdrantVectorStoreProvider(settings)
    if settings.vector_store_provider.lower() == "faiss":
        return FaissVectorStoreProvider(settings)""")

with open("/workspaces/Ai-Agent-RAG/Document from Usif Androws (1)/ProjectTemplate/src/stores/vectordb/provider/__init__.py", "w") as f:
    f.write(content)
