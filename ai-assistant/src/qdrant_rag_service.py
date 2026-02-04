"""
Qdrant+FastEmbed RAG Service - 2024/2025 Cutting-Edge Solution
Modern CPU-optimized RAG using Qdrant embedded mode with FastEmbed
Based on ADR-0027: CPU-Based AI Deployment Assistant Architecture
Optimized for CentOS Stream 10 / RHEL environments
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import uuid

try:
    from qdrant_client import QdrantClient, models

    QDRANT_AVAILABLE = True
except ImportError as e:
    QDRANT_AVAILABLE = False
    logging.warning(f"Qdrant client not available: {e}")


@dataclass
class RetrievalResult:
    """Result from document retrieval"""

    chunk_id: str
    content: str
    title: str
    source_file: str
    score: float
    metadata: Dict[str, Any]


@dataclass
class RetrievalContext:
    """Context retrieved from RAG for AI augmentation"""

    contexts: List[str]
    sources: List[str]


class QdrantRAGService:
    """Modern Qdrant+FastEmbed RAG service for 2024/2025"""

    def __init__(self, data_dir: str = "/app/data"):
        self.data_dir = Path(data_dir)
        self.rag_docs_dir = self.data_dir / "rag-docs"
        self.vector_db_dir = self.data_dir / "qdrant-db"
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.client = None
        self.collection_name = "qubinode_docs"
        # BGE-small-en-v1.5: Better retrieval accuracy than MiniLM, same 384 dims
        # - MTEB score: 62.17% vs ~56% for MiniLM
        # - Retrieval: 51.68% (optimized for RAG)
        # - Context: 512 tokens vs 256 for MiniLM
        # - CPU performance: ~30ms vs ~45ms (faster!)
        self.model_name = "BAAI/bge-small-en-v1.5"
        self.documents_loaded = False

        # Create directories
        self.vector_db_dir.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> bool:
        """Initialize the Qdrant RAG service"""
        if not QDRANT_AVAILABLE:
            self.logger.warning("Qdrant not available - RAG service disabled")
            return False

        try:
            self.logger.info("Initializing Qdrant+FastEmbed RAG service...")

            # Initialize Qdrant client in embedded mode (no server needed!)
            self.client = QdrantClient(path=str(self.vector_db_dir))
            self.logger.info("✅ Qdrant client initialized in embedded mode")

            # Check if collection exists
            collections = self.client.get_collections()
            collection_exists = any(col.name == self.collection_name for col in collections.collections)

            if collection_exists:
                self.logger.info(f"✅ Found existing collection: {self.collection_name}")
                collection_info = self.client.get_collection(self.collection_name)
                self.documents_loaded = collection_info.points_count > 0
                self.logger.info(f"Collection has {collection_info.points_count} documents")
            else:
                # Build new collection from documents
                await self._build_collection_from_documents()

            self.logger.info(f"🎉 Qdrant+FastEmbed RAG service ready with {self._get_document_count()} documents")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Qdrant RAG service: {e}")
            return False

    def _get_document_count(self) -> int:
        """Get the number of documents in the collection"""
        try:
            if self.client and self.documents_loaded:
                collection_info = self.client.get_collection(self.collection_name)
                return collection_info.points_count
        except Exception:
            pass
        return 0

    async def _build_collection_from_documents(self) -> None:
        """Build Qdrant collection from processed document chunks"""
        try:
            # Load documents from processed chunks
            chunks_file = self.rag_docs_dir / "document_chunks.json"
            if not chunks_file.exists():
                self.logger.warning(f"No processed chunks found at {chunks_file}")
                return

            self.logger.info("Loading and processing documents...")
            with open(chunks_file, "r", encoding="utf-8") as f:
                chunks = json.load(f)

            # Filter valid chunks
            valid_chunks = []
            for chunk in chunks:
                content = chunk.get("content", "").strip()
                if len(content) < 20:  # Skip very short content
                    continue
                valid_chunks.append(chunk)

            if not valid_chunks:
                self.logger.warning("No valid documents found")
                return

            self.logger.info(f"Processing {len(valid_chunks)} documents...")

            # Create collection with FastEmbed integration
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.client.get_embedding_size(self.model_name),
                    distance=models.Distance.COSINE,
                ),
            )
            self.logger.info(f"✅ Created collection with {self.client.get_embedding_size(self.model_name)}D embeddings")

            # Prepare documents for upload
            documents = []
            payloads = []
            ids = []

            for chunk in valid_chunks:
                # Create document with FastEmbed model
                doc = models.Document(text=chunk["content"], model=self.model_name)
                documents.append(doc)

                # Prepare payload (metadata)
                payload = {
                    "title": chunk.get("title", ""),
                    "source_file": chunk.get("source_file", ""),
                    "chunk_type": chunk.get("chunk_type", ""),
                    "word_count": chunk.get("word_count", 0),
                    "document_type": chunk.get("metadata", {}).get("document_type", ""),
                    "created_at": chunk.get("created_at", ""),
                    "original_id": chunk["id"],
                }
                payloads.append(payload)

                # Generate UUID for Qdrant (it prefers UUIDs)
                ids.append(str(uuid.uuid4()))

            # Upload documents in batches for better performance
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i : i + batch_size]
                batch_payloads = payloads[i : i + batch_size]
                batch_ids = ids[i : i + batch_size]

                self.client.upload_collection(
                    collection_name=self.collection_name,
                    vectors=batch_docs,
                    payload=batch_payloads,
                    ids=batch_ids,
                )

                self.logger.info(f"Uploaded batch {i // batch_size + 1}/{(len(documents) + batch_size - 1) // batch_size}")

            self.documents_loaded = True
            self.logger.info(f"🎉 Successfully built collection with {len(documents)} documents")

        except Exception as e:
            self.logger.error(f"Failed to build collection: {e}")

    async def rebuild_collection(self) -> int:
        """Delete existing collection and rebuild from document_chunks.json.

        Returns the new document count.
        """
        if self.client:
            try:
                self.client.delete_collection(self.collection_name)
                self.logger.info(f"Deleted existing collection: {self.collection_name}")
            except Exception:
                pass
        self.documents_loaded = False
        await self._build_collection_from_documents()
        return self._get_document_count()

    async def search_documents(self, query: str, n_results: int = 5, document_types: Optional[List[str]] = None) -> List[RetrievalResult]:
        """Search for relevant documents using Qdrant+FastEmbed"""
        if not self.documents_loaded or not self.client:
            self.logger.warning("Qdrant RAG service not properly initialized")
            return []

        try:
            # Build query filters
            query_filter = None
            if document_types:
                query_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_type",
                            match=models.MatchAny(any=document_types),
                        )
                    ]
                )

            # Perform semantic search using FastEmbed
            search_results = self.client.query_points(
                collection_name=self.collection_name,
                query=models.Document(text=query, model=self.model_name),
                query_filter=query_filter,
                limit=n_results,
                with_payload=True,
            )

            # Convert to RetrievalResult objects
            results = []
            for point in search_results.points:
                payload = point.payload

                result = RetrievalResult(
                    chunk_id=payload.get("original_id", str(point.id)),
                    content=payload.get("content", ""),  # This will be empty, we need to get it differently
                    title=payload.get("title", ""),
                    source_file=payload.get("source_file", ""),
                    score=point.score,
                    metadata={
                        "document_type": payload.get("document_type", ""),
                        "chunk_type": payload.get("chunk_type", ""),
                        "word_count": payload.get("word_count", 0),
                        "created_at": payload.get("created_at", ""),
                    },
                )
                results.append(result)

            # We need to get the actual content from our original chunks
            # This is a limitation of the current approach - let's fix it
            results = await self._enrich_results_with_content(results)

            self.logger.info(f"Retrieved {len(results)} documents for query: {query[:50]}...")
            return results

        except Exception as e:
            self.logger.error(f"Failed to search documents: {e}")
            return []

    async def _enrich_results_with_content(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Enrich results with actual content from original chunks"""
        try:
            # Load original chunks to get content
            chunks_file = self.rag_docs_dir / "document_chunks.json"
            if not chunks_file.exists():
                return results

            with open(chunks_file, "r", encoding="utf-8") as f:
                chunks = json.load(f)

            # Create lookup map
            content_map = {chunk["id"]: chunk["content"] for chunk in chunks}

            # Enrich results
            for result in results:
                if result.chunk_id in content_map:
                    result.content = content_map[result.chunk_id]

            return results

        except Exception as e:
            self.logger.error(f"Failed to enrich results: {e}")
            return results

    async def get_context_for_query(
        self,
        query: str,
        max_context_length: int = 4000,
        document_types: Optional[List[str]] = None,
    ) -> Tuple[str, List[str]]:
        """Get relevant context for a query, formatted for AI assistant"""
        results = await self.search_documents(
            query,
            n_results=10,  # Get more results to have options
            document_types=document_types,
        )

        if not results:
            return "", []

        # Build context string within length limit
        context_parts = []
        sources = []
        current_length = 0

        for result in results:
            # Format context entry
            context_entry = f"## {result.title}\n"
            context_entry += f"Source: {result.source_file}\n"
            context_entry += f"Relevance: {result.score:.3f}\n\n"
            context_entry += result.content + "\n\n"

            # Check if adding this would exceed limit
            if current_length + len(context_entry) > max_context_length:
                break

            context_parts.append(context_entry)
            sources.append(result.source_file)
            current_length += len(context_entry)

        context = "# Relevant Documentation Context\n\n" + "".join(context_parts)
        return context, list(set(sources))  # Remove duplicate sources

    async def retrieve_relevant_context(
        self,
        query: str,
        top_k: int = 5,
    ) -> "RetrievalContext":
        """
        Retrieve relevant context for a query.
        Returns a RetrievalContext object with contexts and sources.

        This method is used by EnhancedAIService for RAG-augmented responses.
        """
        results = await self.search_documents(query, n_results=top_k)

        contexts = []
        sources = []

        for result in results:
            contexts.append(result.content)
            if result.source_file and result.source_file not in sources:
                sources.append(result.source_file)

        return RetrievalContext(contexts=contexts, sources=sources)

    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of Qdrant RAG service"""
        status = {
            "available": QDRANT_AVAILABLE,
            "initialized": self.client is not None,
            "documents_loaded": self.documents_loaded,
            "document_count": self._get_document_count(),
            "embeddings_model": self.model_name if self.client else None,
            "collection_name": self.collection_name,
            "vector_db_type": "Qdrant Embedded + FastEmbed",
        }

        if self.client:
            try:
                # Get embedding size
                status["embedding_size"] = self.client.get_embedding_size(self.model_name)
            except Exception:
                pass

        return status

    async def search_by_document_type(self, query: str, doc_type: str, n_results: int = 3) -> List[RetrievalResult]:
        """Search for documents of a specific type"""
        return await self.search_documents(query, n_results=n_results, document_types=[doc_type])

    async def get_adr_context(self, query: str) -> Tuple[str, List[str]]:
        """Get ADR-specific context for architectural questions"""
        return await self.get_context_for_query(query, document_types=["adr"], max_context_length=3000)

    async def get_config_context(self, query: str) -> Tuple[str, List[str]]:
        """Get configuration-specific context"""
        return await self.get_context_for_query(query, document_types=["config"], max_context_length=2000)


# Mock RAG service for when Qdrant is not available
class MockRAGService:
    """Mock RAG service for development/testing"""

    def __init__(self, data_dir: str = "/app/data"):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Using mock RAG service - Qdrant not available")

    async def initialize(self) -> bool:
        return True

    async def search_documents(self, query: str, n_results: int = 5, document_types: Optional[List[str]] = None) -> List[RetrievalResult]:
        # Return mock results based on query
        mock_content = f"""Mock documentation content for query: "{query}"

This is a simulated response that would normally come from our Qdrant+FastEmbed RAG system.
The system would search through 5,200+ document chunks covering:
- Architectural Decision Records (ADRs)
- Configuration files and templates
- Infrastructure automation guides
- Deployment procedures
- Troubleshooting documentation

For production deployment, ensure Qdrant client is properly installed."""

        return [
            RetrievalResult(
                chunk_id="mock_001",
                content=mock_content,
                title=f"Mock Documentation: {query[:30]}...",
                source_file="docs/mock-rag-response.md",
                score=0.85,
                metadata={"document_type": "mock", "source": "fallback"},
            )
        ]

    async def get_context_for_query(
        self,
        query: str,
        max_context_length: int = 4000,
        document_types: Optional[List[str]] = None,
    ) -> Tuple[str, List[str]]:
        context = f"""# Mock RAG Context for: {query}

## Simulated Documentation Response
Source: docs/mock-rag-response.md
Relevance: 0.850

This is a mock response from the RAG system. In production, this would contain
relevant excerpts from the actual Qubinode Navigator documentation, ADRs, and
configuration files based on semantic similarity to your query.

The Qdrant+FastEmbed system would provide contextually relevant information
to help answer questions about infrastructure automation, deployment procedures,
and system configuration.
"""
        return context, ["docs/mock-rag-response.md"]

    async def get_health_status(self) -> Dict[str, Any]:
        return {
            "available": False,
            "initialized": True,
            "documents_loaded": False,
            "document_count": 0,
            "embeddings_model": "mock",
            "collection_name": "mock_collection",
            "vector_db_type": "Mock Service",
        }

    async def search_by_document_type(self, query: str, doc_type: str, n_results: int = 3) -> List[RetrievalResult]:
        return await self.search_documents(query, n_results)

    async def get_adr_context(self, query: str) -> Tuple[str, List[str]]:
        return await self.get_context_for_query(query)

    async def get_config_context(self, query: str) -> Tuple[str, List[str]]:
        return await self.get_context_for_query(query)


def create_rag_service(data_dir: str = "/app/data"):
    """Factory function to create appropriate RAG service"""
    if QDRANT_AVAILABLE:
        return QdrantRAGService(data_dir)
    else:
        return MockRAGService(data_dir)
