"""
AI Service Module - DEPRECATED

This module contained the AIService class that handled Ollama-based AI operations.
It has been replaced by EmbeddedAIService which uses LlamaCpp for local inference.
This file is kept for reference but all functionality has been moved to embedded_ai_service.py.

IMPORTANT: This entire class is commented out as it depends on Ollama which has been removed.
Use EmbeddedAIService instead for all AI operations.

All imports and the entire AIService class have been commented out to remove Ollama dependencies.
The functionality has been reimplemented in services/embedded_ai_service.py using LlamaCpp.
"""

# DEPRECATED: All code below has been commented out due to Ollama dependency removal
# Use EmbeddedAIService from services/embedded_ai_service.py instead

# """
# AI Service Module
# 
# This module contains the AIService class that handles all AI-related operations
# including LangChain integration, vector store management, and LLM interactions.
# Extracted from the monolithic chatbot.py to follow microservices architecture.
# """
# 
# import json
# import os
# import pickle
# import time
# from datetime import datetime, timedelta
# from typing import List, Dict, Any, Optional, Tuple
# from pathlib import Path
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain_community.vectorstores import FAISS
# from langchain_huggingface import HuggingFaceEmbeddings
# from langchain_ollama import ChatOllama  # REMOVED: Ollama dependency
# from langchain.chains import ConversationalRetrievalChain
# from langchain.schema import Document
# from langchain.schema.messages import SystemMessage, HumanMessage, AIMessage
# from langchain.memory import ConversationBufferWindowMemory
# from core.exceptions import AIProcessingError, ServiceUnavailableError
# 
# 
# class AIService:
#     """
#     AI Service for handling LangChain integration, embeddings, and LLM operations.
#     
#     This service encapsulates all AI-related functionality including:
#     - Vector store creation and management
#     - Embedding generation
#     - Similarity search
#     - LLM conversation chains
#     - Context management
#     """
#     
#     # ... [ENTIRE CLASS IMPLEMENTATION COMMENTED OUT] ...
#     # This class has been replaced by EmbeddedAIService
#     # All methods and functionality moved to services/embedded_ai_service.py