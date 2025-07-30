"""
AI Service Module

This module contains the AIService class that handles all AI-related operations
including LangChain integration, vector store management, and LLM interactions.
Extracted from the monolithic chatbot.py to follow microservices architecture.
"""

import json
import os
import pickle
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain.chains import ConversationalRetrievalChain
from langchain.schema import Document
from langchain.schema.messages import SystemMessage, HumanMessage, AIMessage
from langchain.memory import ConversationBufferWindowMemory
from core.exceptions import AIProcessingError, ServiceUnavailableError


class AIService:
    """
    AI Service for handling LangChain integration, embeddings, and LLM operations.
    
    This service encapsulates all AI-related functionality including:
    - Vector store creation and management
    - Embedding generation
    - Similarity search
    - LLM conversation chains
    - Context management
    """
    
    def __init__(self, embedding_model_name: str = "all-MiniLM-L6-v2", llm_model: str = "llama3", 
                 vectorstore_path: str = "./data/vectorstore", max_retries: int = 3, 
                 retry_delay: float = 1.0, conversation_memory_size: int = 10):
        """
        Initialize the AI service with specified models.
        
        Args:
            embedding_model_name: Name of the HuggingFace embedding model
            llm_model: Name of the Ollama LLM model
            vectorstore_path: Path to store/load vector store data
            max_retries: Maximum number of retries for LLM calls
            retry_delay: Delay between retries in seconds
            conversation_memory_size: Number of conversation turns to remember
        """
        self.embedding_model_name = embedding_model_name
        self.llm_model = llm_model
        self.vectorstore_path = Path(vectorstore_path)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.conversation_memory_size = conversation_memory_size
        
        # Core components
        self.embedding_model = None
        self.vectorstore = None
        self.qa_chain = None
        self.llm = None
        self.context = None
        self.vectorstore_metadata = {}
        
        # Conversation management
        self.conversation_sessions = {}  # session_id -> conversation history
        self.memory = None
        
        self._initialize_models()
        self._ensure_vectorstore_directory()
    
    def _initialize_models(self) -> None:
        """Initialize the embedding model and LLM."""
        try:
            self.embedding_model = HuggingFaceEmbeddings(model_name=self.embedding_model_name)
            self.llm = ChatOllama(model=self.llm_model)
            self.context = self._initialize_assistant_context()
        except Exception as e:
            raise AIProcessingError(f"Failed to initialize AI models: {str(e)}")
    
    def _ensure_vectorstore_directory(self) -> None:
        """Ensure the vector store directory exists."""
        try:
            self.vectorstore_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise AIProcessingError(f"Failed to create vectorstore directory: {str(e)}")
    
    def _initialize_assistant_context(self) -> str:
        """
        Initialize the assistant context for security analysis.
        
        Returns:
            System context string for the AI assistant
        """
        return """You are a security analyst performing threat hunting.
Your task is to analyze logs from Wazuh. You have access to the logs stored in the vector store.
The objective is to identify potential security threats or any other needs from the user.
All queries should be interpreted as asking about security events, patterns or other request from the user using the vectorized logs."""
    
    def create_vectorstore(self, logs: List[Dict[str, Any]]) -> FAISS:
        """
        Create a FAISS vector store from log data.
        
        Args:
            logs: List of log dictionaries containing log data
            
        Returns:
            FAISS vector store instance
            
        Raises:
            AIProcessingError: If vector store creation fails
        """
        if not logs:
            raise AIProcessingError("Cannot create vector store: no logs provided")
        
        if not self.embedding_model:
            raise AIProcessingError("Embedding model not initialized")
        
        try:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500, 
                chunk_overlap=50
            )
            documents = []
            
            for log in logs:
                full_log = log.get('full_log', '')
                if full_log:
                    splits = text_splitter.split_text(full_log)
                    for chunk in splits:
                        documents.append(Document(page_content=chunk))
            
            if not documents:
                raise AIProcessingError("No valid documents found in logs")
            
            self.vectorstore = FAISS.from_documents(documents, self.embedding_model)
            return self.vectorstore
            
        except Exception as e:
            raise AIProcessingError(f"Failed to create vector store: {str(e)}")
    
    def generate_embeddings(self, text: str) -> List[float]:
        """
        Generate embeddings for the given text.
        
        Args:
            text: Input text to generate embeddings for
            
        Returns:
            List of embedding values
            
        Raises:
            AIProcessingError: If embedding generation fails
        """
        if not self.embedding_model:
            raise AIProcessingError("Embedding model not initialized")
        
        try:
            embeddings = self.embedding_model.embed_query(text)
            return embeddings
        except Exception as e:
            raise AIProcessingError(f"Failed to generate embeddings: {str(e)}")
    
    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        """
        Perform similarity search in the vector store.
        
        Args:
            query: Search query string
            k: Number of similar documents to return
            
        Returns:
            List of similar documents
            
        Raises:
            AIProcessingError: If similarity search fails
        """
        if not self.vectorstore:
            raise AIProcessingError("Vector store not initialized")
        
        try:
            similar_docs = self.vectorstore.similarity_search(query, k=k)
            return similar_docs
        except Exception as e:
            raise AIProcessingError(f"Similarity search failed: {str(e)}")
    
    def setup_qa_chain(self, logs: List[Dict[str, Any]]) -> ConversationalRetrievalChain:
        """
        Set up the conversational retrieval chain with the provided logs.
        
        Args:
            logs: List of log dictionaries to create vector store from
            
        Returns:
            Configured ConversationalRetrievalChain instance
            
        Raises:
            AIProcessingError: If QA chain setup fails
        """
        try:
            # Create vector store from logs
            vectorstore = self.create_vectorstore(logs)
            
            # Create conversation memory
            self.memory = ConversationBufferWindowMemory(
                k=self.conversation_memory_size,
                memory_key="chat_history",
                return_messages=True
            )
            
            # Create the QA chain with memory
            self.qa_chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=vectorstore.as_retriever(),
                memory=self.memory,
                return_source_documents=False,
                verbose=False
            )
            
            return self.qa_chain
            
        except Exception as e:
            raise AIProcessingError(f"Failed to setup QA chain: {str(e)}")
    
    def _call_llm_with_retry(self, query: str, chat_history: List) -> Dict[str, Any]:
        """
        Call the LLM with retry logic and error handling.
        
        Args:
            query: User query string
            chat_history: List of previous chat messages
            
        Returns:
            LLM response dictionary
            
        Raises:
            AIProcessingError: If all retry attempts fail
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = self.qa_chain.invoke({
                    "question": query, 
                    "chat_history": chat_history
                })
                return response
                
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                    continue
                else:
                    break
        
        raise AIProcessingError(f"LLM call failed after {self.max_retries} attempts: {str(last_error)}")
    
    def create_conversation_session(self, session_id: str) -> None:
        """
        Create a new conversation session.
        
        Args:
            session_id: Unique identifier for the conversation session
        """
        self.conversation_sessions[session_id] = {
            "history": [SystemMessage(content=self.context)],
            "created_at": datetime.now(),
            "last_activity": datetime.now()
        }
    
    def get_conversation_history(self, session_id: str) -> List:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Unique identifier for the conversation session
            
        Returns:
            List of conversation messages
        """
        if session_id not in self.conversation_sessions:
            self.create_conversation_session(session_id)
        
        return self.conversation_sessions[session_id]["history"]
    
    def add_to_conversation_history(self, session_id: str, message: Any) -> None:
        """
        Add a message to conversation history.
        
        Args:
            session_id: Unique identifier for the conversation session
            message: Message to add to history
        """
        if session_id not in self.conversation_sessions:
            self.create_conversation_session(session_id)
        
        session = self.conversation_sessions[session_id]
        session["history"].append(message)
        session["last_activity"] = datetime.now()
        
        # Limit conversation history size
        if len(session["history"]) > self.conversation_memory_size * 2 + 1:  # +1 for system message
            # Keep system message and recent messages
            system_msg = session["history"][0]
            recent_messages = session["history"][-(self.conversation_memory_size * 2):]
            session["history"] = [system_msg] + recent_messages
    
    def clear_conversation_history(self, session_id: str) -> None:
        """
        Clear conversation history for a session.
        
        Args:
            session_id: Unique identifier for the conversation session
        """
        if session_id in self.conversation_sessions:
            self.conversation_sessions[session_id]["history"] = [SystemMessage(content=self.context)]
            self.conversation_sessions[session_id]["last_activity"] = datetime.now()
    
    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """
        Clean up old conversation sessions.
        
        Args:
            max_age_hours: Maximum age of sessions to keep in hours
            
        Returns:
            Number of sessions cleaned up
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        sessions_to_remove = []
        
        for session_id, session in self.conversation_sessions.items():
            if session["last_activity"] < cutoff_time:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.conversation_sessions[session_id]
        
        return len(sessions_to_remove)
    
    def generate_response(self, query: str, session_id: str = "default") -> str:
        """
        Generate a response to the user query using the QA chain with conversation context.
        
        Args:
            query: User query string
            session_id: Unique identifier for the conversation session
            
        Returns:
            Generated response string
            
        Raises:
            AIProcessingError: If response generation fails
            ServiceUnavailableError: If QA chain is not available
        """
        if not self.qa_chain:
            raise ServiceUnavailableError("QA chain not initialized")
        
        try:
            # Get conversation history for this session
            chat_history = self.get_conversation_history(session_id)
            
            # Add user message to history
            self.add_to_conversation_history(session_id, HumanMessage(content=query))
            
            # Call LLM with retry logic
            response = self._call_llm_with_retry(query, chat_history)
            
            # Extract and format answer
            answer = response.get("answer", "").replace("\\n", "\n").strip()
            
            if not answer:
                answer = "⚠️ Sorry, I couldn't generate a response."
            
            # Add AI response to history
            self.add_to_conversation_history(session_id, AIMessage(content=answer))
            
            return answer
            
        except Exception as e:
            if isinstance(e, (AIProcessingError, ServiceUnavailableError)):
                raise
            raise AIProcessingError(f"Failed to generate response: {str(e)}")
    
    def generate_response_with_context(self, query: str, context_docs: List[Document], 
                                     session_id: str = "default") -> str:
        """
        Generate a response with specific context documents.
        
        Args:
            query: User query string
            context_docs: List of context documents to use
            session_id: Unique identifier for the conversation session
            
        Returns:
            Generated response string
        """
        try:
            # Format context from documents
            context_text = "\n\n".join([doc.page_content for doc in context_docs])
            
            # Create a prompt with context
            prompt = f"""Based on the following context, please answer the question:

Context:
{context_text}

Question: {query}

Answer:"""
            
            # Get conversation history
            chat_history = self.get_conversation_history(session_id)
            
            # Add user message to history
            self.add_to_conversation_history(session_id, HumanMessage(content=prompt))
            
            # Generate response using LLM directly
            response = self._call_llm_with_retry(prompt, chat_history)
            
            answer = response.get("answer", "").replace("\\n", "\n").strip()
            
            if not answer:
                answer = "⚠️ Sorry, I couldn't generate a response."
            
            # Add AI response to history
            self.add_to_conversation_history(session_id, AIMessage(content=answer))
            
            return answer
            
        except Exception as e:
            raise AIProcessingError(f"Failed to generate response with context: {str(e)}")
    
    def validate_response(self, response: str) -> bool:
        """
        Validate the generated response.
        
        Args:
            response: Generated response string
            
        Returns:
            True if response is valid, False otherwise
        """
        if not response or not response.strip():
            return False
        
        # Check for common error patterns
        error_patterns = [
            "I don't know",
            "I cannot",
            "I'm not sure",
            "No information",
            "Unable to"
        ]
        
        response_lower = response.lower()
        for pattern in error_patterns:
            if pattern.lower() in response_lower:
                return False
        
        # Check minimum length
        if len(response.strip()) < 10:
            return False
        
        return True
    
    def update_vectorstore(self, new_logs: List[Dict[str, Any]], 
                          identifier: str = "default") -> None:
        """
        Update the existing vector store with new logs.
        
        Args:
            new_logs: List of new log dictionaries to add
            identifier: Identifier for the vector store to update
            
        Raises:
            AIProcessingError: If vector store update fails
        """
        # Use the incremental update method
        self.incremental_update_vectorstore(new_logs, identifier)
    
    def get_context(self) -> str:
        """
        Get the current assistant context.
        
        Returns:
            Current context string
        """
        return self.context or ""
    
    def check_llm_health(self) -> Dict[str, Any]:
        """
        Check the health of the LLM connection.
        
        Returns:
            Dictionary containing health status information
        """
        try:
            # Simple test query
            test_response = self.llm.invoke("Hello, are you working?")
            
            return {
                "status": "healthy",
                "model": self.llm_model,
                "response_received": bool(test_response),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "model": self.llm_model,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_llm_config(self) -> Dict[str, Any]:
        """
        Get current LLM configuration.
        
        Returns:
            Dictionary containing LLM configuration
        """
        return {
            "llm_model": self.llm_model,
            "embedding_model": self.embedding_model_name,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "conversation_memory_size": self.conversation_memory_size,
            "active_sessions": len(self.conversation_sessions)
        }
    
    def update_llm_config(self, **kwargs) -> None:
        """
        Update LLM configuration parameters.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        if "max_retries" in kwargs:
            self.max_retries = kwargs["max_retries"]
        
        if "retry_delay" in kwargs:
            self.retry_delay = kwargs["retry_delay"]
        
        if "conversation_memory_size" in kwargs:
            self.conversation_memory_size = kwargs["conversation_memory_size"]
            # Update existing memory if it exists
            if self.memory:
                self.memory.k = self.conversation_memory_size
    
    def is_ready(self) -> bool:
        """
        Check if the AI service is ready to process requests.
        
        Returns:
            True if service is ready, False otherwise
        """
        return (
            self.embedding_model is not None and 
            self.llm is not None and 
            self.context is not None
        )
    
    def save_vectorstore(self, identifier: str = "default") -> bool:
        """
        Save the current vector store to disk.
        
        Args:
            identifier: Unique identifier for the vector store
            
        Returns:
            True if save was successful, False otherwise
            
        Raises:
            AIProcessingError: If save operation fails
        """
        if not self.vectorstore:
            raise AIProcessingError("No vector store to save")
        
        try:
            vectorstore_dir = self.vectorstore_path / identifier
            vectorstore_dir.mkdir(parents=True, exist_ok=True)
            
            # Save FAISS index
            faiss_path = str(vectorstore_dir / "faiss_index")
            self.vectorstore.save_local(faiss_path)
            
            # Save metadata
            metadata = {
                "identifier": identifier,
                "created_at": datetime.now().isoformat(),
                "embedding_model": self.embedding_model_name,
                "llm_model": self.llm_model,
                "document_count": self.vectorstore.index.ntotal if hasattr(self.vectorstore, 'index') else 0
            }
            
            metadata_path = vectorstore_dir / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self.vectorstore_metadata[identifier] = metadata
            return True
            
        except Exception as e:
            raise AIProcessingError(f"Failed to save vector store: {str(e)}")
    
    def load_vectorstore(self, identifier: str = "default") -> bool:
        """
        Load a vector store from disk.
        
        Args:
            identifier: Unique identifier for the vector store to load
            
        Returns:
            True if load was successful, False otherwise
            
        Raises:
            AIProcessingError: If load operation fails
        """
        try:
            vectorstore_dir = self.vectorstore_path / identifier
            faiss_path = vectorstore_dir / "faiss_index"
            metadata_path = vectorstore_dir / "metadata.json"
            
            if not faiss_path.exists() or not metadata_path.exists():
                return False
            
            # Load metadata
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Verify model compatibility
            if metadata.get("embedding_model") != self.embedding_model_name:
                raise AIProcessingError(
                    f"Embedding model mismatch: expected {self.embedding_model_name}, "
                    f"found {metadata.get('embedding_model')}"
                )
            
            # Load FAISS index
            self.vectorstore = FAISS.load_local(
                str(faiss_path), 
                self.embedding_model,
                allow_dangerous_deserialization=True
            )
            
            self.vectorstore_metadata[identifier] = metadata
            return True
            
        except Exception as e:
            raise AIProcessingError(f"Failed to load vector store: {str(e)}")
    
    def list_saved_vectorstores(self) -> List[Dict[str, Any]]:
        """
        List all saved vector stores.
        
        Returns:
            List of dictionaries containing vector store information
        """
        vectorstores = []
        
        try:
            if not self.vectorstore_path.exists():
                return vectorstores
            
            for item in self.vectorstore_path.iterdir():
                if item.is_dir():
                    metadata_path = item / "metadata.json"
                    if metadata_path.exists():
                        try:
                            with open(metadata_path, 'r') as f:
                                metadata = json.load(f)
                            vectorstores.append(metadata)
                        except Exception as e:
                            # Skip corrupted metadata files
                            continue
            
            return sorted(vectorstores, key=lambda x: x.get('created_at', ''), reverse=True)
            
        except Exception as e:
            raise AIProcessingError(f"Failed to list vector stores: {str(e)}")
    
    def delete_vectorstore(self, identifier: str) -> bool:
        """
        Delete a saved vector store.
        
        Args:
            identifier: Unique identifier for the vector store to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            vectorstore_dir = self.vectorstore_path / identifier
            
            if not vectorstore_dir.exists():
                return False
            
            # Remove directory and all contents
            import shutil
            shutil.rmtree(vectorstore_dir)
            
            # Remove from metadata cache
            if identifier in self.vectorstore_metadata:
                del self.vectorstore_metadata[identifier]
            
            return True
            
        except Exception as e:
            raise AIProcessingError(f"Failed to delete vector store: {str(e)}")
    
    def incremental_update_vectorstore(self, new_logs: List[Dict[str, Any]], 
                                     identifier: str = "default") -> None:
        """
        Perform incremental update of vector store with new logs.
        
        Args:
            new_logs: List of new log dictionaries to add
            identifier: Identifier for the vector store to update
            
        Raises:
            AIProcessingError: If incremental update fails
        """
        if not new_logs:
            return
        
        try:
            # If no vector store exists, create a new one
            if not self.vectorstore:
                # Try to load existing vector store first
                if not self.load_vectorstore(identifier):
                    # Create new vector store if none exists
                    self.create_vectorstore(new_logs)
                    self.save_vectorstore(identifier)
                    return
            
            # Create documents from new logs
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500, 
                chunk_overlap=50
            )
            new_documents = []
            
            for log in new_logs:
                full_log = log.get('full_log', '')
                if full_log:
                    splits = text_splitter.split_text(full_log)
                    for chunk in splits:
                        new_documents.append(Document(page_content=chunk))
            
            if new_documents:
                # Add new documents to existing vector store
                self.vectorstore.add_documents(new_documents)
                
                # Save updated vector store
                self.save_vectorstore(identifier)
                
                # Update metadata
                if identifier in self.vectorstore_metadata:
                    self.vectorstore_metadata[identifier]["document_count"] = (
                        self.vectorstore.index.ntotal if hasattr(self.vectorstore, 'index') else 0
                    )
                    self.vectorstore_metadata[identifier]["updated_at"] = datetime.now().isoformat()
                
        except Exception as e:
            raise AIProcessingError(f"Failed to perform incremental update: {str(e)}")
    
    def get_vectorstore_info(self) -> Dict[str, Any]:
        """
        Get information about the current vector store.
        
        Returns:
            Dictionary containing vector store information
        """
        if not self.vectorstore:
            return {"status": "not_initialized", "document_count": 0}
        
        try:
            # Get document count from FAISS index
            doc_count = self.vectorstore.index.ntotal if hasattr(self.vectorstore, 'index') else 0
            return {
                "status": "ready",
                "document_count": doc_count,
                "embedding_model": self.embedding_model_name,
                "llm_model": self.llm_model,
                "vectorstore_path": str(self.vectorstore_path),
                "saved_vectorstores": len(self.list_saved_vectorstores())
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}