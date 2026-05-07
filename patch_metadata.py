with open("/workspaces/Ai-Agent-RAG/Document from Usif Androws (1)/ProjectTemplate/src/stores/mongodb/provider/__init__.py", "r") as f:
    content = f.read()

content = content.replace("def create_metadata_repository(settings: Settings) -> MetadataRepository:", """from src.stores.sqlite_provider import SqliteMetadataRepository

def create_metadata_repository(settings: Settings) -> MetadataRepository:""")

content = content.replace("    if settings.metadata_store_provider.lower() == \"mongo\":\n        return MongoMetadataRepository(settings)", """    if settings.metadata_store_provider.lower() == "mongo":
        return MongoMetadataRepository(settings)
    if settings.metadata_store_provider.lower() == "sqlite":
        return SqliteMetadataRepository(settings)""")

with open("/workspaces/Ai-Agent-RAG/Document from Usif Androws (1)/ProjectTemplate/src/stores/mongodb/provider/__init__.py", "w") as f:
    f.write(content)
