"""
LangChain RAG Agent using local LLM (Ollama)
Reads from local documents and generates responses
"""
import os

try:
    import config
except Exception:
    config = None

from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate


class RAGAgent:
    def __init__(self, docs_dir="documents", model_name="phi3:mini", base_url=None, embeddings_model=None):
        """
        Initialize RAG Agent with local documents and Ollama LLM
        
        Args:
            docs_dir: Directory containing documents to load
            model_name: Ollama model to use for generation (default: phi3:mini - faster)
                       Run: ollama pull phi3:mini
            embeddings_model: Ollama model to use for embeddings (default: nomic-embed-text - fast)
                            Run: ollama pull nomic-embed-text
        """
        self.docs_dir = docs_dir
        self.model_name = model_name
        self.embeddings_model = embeddings_model or getattr(config, "EMBEDDINGS_MODEL", "nomic-embed-text")
        self.base_url = base_url or os.getenv(
            "OLLAMA_BASE_URL",
            getattr(config, "OLLAMA_BASE_URL", "http://localhost:11434")
        )
        self.vector_store = None
        self.qa_chain = None
        safe_embeddings_name = self.embeddings_model.replace(":", "_")
        self.faiss_index_path = os.path.join(docs_dir, f"faiss_index_{safe_embeddings_name}")
        
        # Create documents directory if it doesn't exist
        if not os.path.exists(docs_dir):
            os.makedirs(docs_dir)
        
        self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize the RAG agent with documents and Ollama LLM"""
        try:
            # Initialize embeddings (needed for loading or creating vector store)
            # Use dedicated embeddings model for faster processing
            embeddings = OllamaEmbeddings(
                model=self.embeddings_model,
                base_url=self.base_url
            )
            
            # Try to load existing vector store
            if os.path.exists(self.faiss_index_path):
                print("⚡ Loading cached vector store...")
                self.vector_store = FAISS.load_local(
                    self.faiss_index_path, 
                    embeddings
                )
                print("✅ Vector store loaded from cache")
            else:
                # Create new vector store
                print("📚 Creating new vector store...")
                
                # Load documents from the documents directory
                text_loader = DirectoryLoader(
                    self.docs_dir,
                    glob="**/*.txt",
                    loader_cls=TextLoader
                )
                pdf_loader = DirectoryLoader(
                    self.docs_dir,
                    glob="**/*.pdf",
                    loader_cls=PyPDFLoader
                )
                documents = text_loader.load() + pdf_loader.load()
                
                if not documents:
                    print(f"Warning: No documents found in {self.docs_dir}")
                    # Create a sample document for testing
                    self._create_sample_document()
                    documents = text_loader.load() + pdf_loader.load()
                
                # Split documents into chunks
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=700,  # Smaller chunks = faster embeddings
                    chunk_overlap=20   # Reduced overlap = fewer chunks
                )
                docs = text_splitter.split_documents(documents)
                
                # Create embeddings and vector store
                print("Creating embeddings (this may take a minute)...")
                self.vector_store = FAISS.from_documents(docs, embeddings)
                
                # Save the vector store for next time
                print("💾 Saving vector store to cache...")
                self.vector_store.save_local(self.faiss_index_path)
                print("✅ Vector store cached")
            
            # Initialize LLM
            # Initialize LLM - phi3:mini is much faster than mistral
            print(f"Loading LLM: {self.model_name}")
            llm = Ollama(
                model=self.model_name,
                base_url=self.base_url,
                timeout=600,  # 10 minute timeout for slow inference
                temperature=0.3  # Lower temperature for faster, focused responses
            )
            self.llm = llm
            
            # Create prompt template
            prompt_template = """Context: {context}

Question: {question}
Answer concisely:"""
            
            PROMPT = PromptTemplate(
                template=prompt_template,
                input_variables=["context", "question"]
            )
            
            # Create QA chain
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=self.vector_store.as_retriever(search_kwargs={"k": 1}),  # Reduced to 1 for faster responses
                chain_type_kwargs={"prompt": PROMPT},
                return_source_documents=True
            )
            
            print("✅ RAG Agent initialized successfully!")
            
        except Exception as e:
            print(f"❌ Error initializing RAG Agent: {e}")
            if "Connection refused" in str(e) or "Max retries exceeded" in str(e):
                print(f"Ollama is unreachable at {self.base_url}")
                print("Start Ollama: ollama serve")
            else:
                print("Make sure Ollama is running: ollama serve")
                print(f"And model is installed: ollama pull {self.model_name}")
            raise

    def _summarize_text(self, text: str, max_length: int) -> str:
        """Summarize text to fit within max_length characters."""
        if not text or max_length <= 0:
            return ""
        if len(text) <= max_length:
            return text
        if not getattr(self, "llm", None):
            return text[:max_length].rstrip() + "..."

        prompt = (
            "Summarize the following answer to be at most "
            f"{max_length} characters. Keep key facts and be concise.\n\n"
            f"Answer:\n{text}\n\nSummary:"
        )
        try:
            summary = self.llm.invoke(prompt)
            summary = summary.strip()
            if len(summary) <= max_length:
                return summary
            return summary[:max_length].rstrip() + "..."
        except Exception:
            return text[:max_length].rstrip() + "..."
    
    def _create_sample_document(self):
        """Create a sample document for testing"""
        sample_content = """Sample Document - About Artificial Intelligence

Artificial Intelligence (AI) is the simulation of human intelligence processes by machines,
especially computer systems. These processes include:

1. Learning - AI systems can learn from data and improve their performance
2. Reasoning - AI can use logic to solve problems and make decisions
3. Problem-solving - AI can identify and solve complex problems
4. Language Processing - AI can understand and generate human language

Types of AI:
- Narrow AI: Designed for specific tasks
- General AI: Hypothetical AI with human-level intelligence
- Super AI: Theoretical AI surpassing human intelligence

Applications of AI:
- Natural Language Processing
- Computer Vision
- Robotics
- Healthcare
- Finance
- Education

Machine Learning is a subset of AI that enables systems to learn and improve from experience.
Deep Learning uses artificial neural networks with multiple layers.

AI is transforming industries and society with both opportunities and challenges."""
        
        os.makedirs(self.docs_dir, exist_ok=True)
        with open(os.path.join(self.docs_dir, "sample.txt"), "w") as f:
            f.write(sample_content)
    
    def query(self, question: str) -> str:
        """
        Query the RAG agent
        
        Args:
            question: User question
            
        Returns:
            Response from the agent
        """
        try:
            if not self.qa_chain:
                return "Agent not properly initialized. Make sure Ollama is running."

            result = self.qa_chain.invoke({"query": question})
            answer = result.get("result", "No answer found")
            max_length = getattr(config, "MAX_RESPONSE_LENGTH", None) or 0
            if max_length and len(answer) > max_length:
                return self._summarize_text(answer, max_length)
            return answer

        except Exception as e:
            import traceback
            print(f"❌ Query error: {type(e).__name__}: {e!r}")
            traceback.print_exc()
            if "Connection refused" in str(e) or "Max retries exceeded" in str(e):
                return (
                    "Error: Ollama is unreachable. Start it with `ollama serve` "
                    "or set OLLAMA_BASE_URL to the correct endpoint."
                )
            return f"Error processing query: {type(e).__name__}: {str(e)}"
    
    def add_document(self, content: str, filename: str = None) -> bool:
        """
        Add a new document to the knowledge base
        
        Args:
            content: Document content
            filename: Optional filename (defaults to auto-generated)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not filename:
                import time
                filename = f"document_{int(time.time())}.txt"
            
            filepath = os.path.join(self.docs_dir, filename)
            with open(filepath, "w") as f:
                f.write(content)
            
            # Remove cached index to force rebuild
            if os.path.exists(self.faiss_index_path):
                import shutil
                shutil.rmtree(self.faiss_index_path)
            
            # Reinitialize agent to include new document
            self._initialize_agent()
            return True
        
        except Exception as e:
            print(f"Error adding document: {e}")
            return False
    
    def rebuild_index(self):
        """Force rebuild of the vector store index"""
        try:
            if os.path.exists(self.faiss_index_path):
                import shutil
                shutil.rmtree(self.faiss_index_path)
            self._initialize_agent()
            print("✅ Index rebuilt successfully")
            return True
        except Exception as e:
            print(f"Error rebuilding index: {e}")
            return False
