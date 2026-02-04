"""
Agent Context: Shared RAG and Lineage services for all PydanticAI agents.

This module provides a singleton context that holds:
- RAG service for document retrieval
- Lineage service for Marquez/OpenLineage data
- Auto-loading of Qubinode ADRs on startup

Per ADR-0049: Multi-Agent LLM Memory Architecture
Per ADR-0063: PydanticAI Core Agent Orchestrator
"""

import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RAGContext:
    """Context from RAG for agent use."""

    contexts: List[str]
    sources: List[str]
    scores: List[float]
    total_results: int


@dataclass
class LineageContext:
    """Context from Marquez lineage for agent use."""

    recent_runs: List[Dict[str, Any]]
    success_rate: Optional[float]
    error_patterns: List[str]
    successful_patterns: List[str]


class AgentContextManager:
    """
    Singleton manager for shared agent context.

    Provides:
    - RAG service for document retrieval
    - Lineage service for execution history
    - Auto-loading of Qubinode ADRs
    - Context query methods for agents
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.rag_service = None
        self.lineage_service = None
        self.adrs_loaded = False
        self.project_root = Path(os.getenv("QUBINODE_ROOT", "/opt/qubinode_navigator"))
        self.data_dir = Path(os.getenv("RAG_DATA_DIR", "/app/data"))
        self.adr_dir = Path(os.getenv("ADR_DIR", "/app/docs/adrs"))
        self.drop_dir = Path(os.getenv("RAG_DROP_DIR", "/app/data/rag-drop"))

    async def initialize(
        self,
        rag_service=None,
        lineage_service=None,
        auto_load_adrs: bool = True,
    ) -> bool:
        """
        Initialize the agent context with services.

        Args:
            rag_service: QdrantRAGService or compatible RAG service
            lineage_service: Marquez lineage service
            auto_load_adrs: Whether to auto-load ADRs into RAG

        Returns:
            True if initialization successful
        """
        self.rag_service = rag_service
        self.lineage_service = lineage_service

        # Auto-load ADRs if requested and RAG is available
        if auto_load_adrs and self.rag_service:
            await self._ensure_adrs_loaded()

        logger.info(f"AgentContextManager initialized: RAG={self.rag_service is not None}, Lineage={self.lineage_service is not None}, ADRs loaded={self.adrs_loaded}")
        return True

    async def _ensure_adrs_loaded(self) -> None:
        """Ensure ADRs are loaded into RAG."""
        if self.adrs_loaded:
            return

        # Check if RAG already has documents
        try:
            if hasattr(self.rag_service, "_get_document_count"):
                doc_count = self.rag_service._get_document_count()
                if doc_count > 0:
                    logger.info(f"RAG already has {doc_count} documents loaded")
                    self.adrs_loaded = True
                    return
        except Exception as e:
            logger.warning(f"Could not check RAG document count: {e}")

        # Check for pre-processed chunks
        chunks_file = self.data_dir / "rag-docs" / "document_chunks.json"
        if chunks_file.exists():
            logger.info(f"Found pre-processed chunks at {chunks_file}")
            self.adrs_loaded = True
            return

        # If no chunks exist, we need to prepare them
        logger.info("No pre-processed documents found - preparing documents...")
        await self._prepare_documents()

    async def _prepare_documents(self) -> None:
        """Prepare documents for RAG ingestion using DropDirectoryScanner."""
        try:
            from drop_directory_scanner import DropDirectoryScanner

            scanner = DropDirectoryScanner(
                source_dirs=[self.adr_dir, self.drop_dir],
                output_dir=self.data_dir / "rag-docs",
            )
            files_processed, chunks_generated = scanner.scan_and_process()
            logger.info(f"Scanner processed {files_processed} files, generated {chunks_generated} chunks")

            if chunks_generated > 0 and hasattr(self.rag_service, "rebuild_collection"):
                logger.info("Rebuilding RAG collection with new documents...")
                await self.rag_service.rebuild_collection()

            self.adrs_loaded = chunks_generated > 0

        except Exception as e:
            logger.error(f"Failed to prepare documents: {e}")

    async def query_rag(
        self,
        query: str,
        top_k: int = 5,
        document_types: Optional[List[str]] = None,
    ) -> RAGContext:
        """
        Query RAG for relevant documents.

        Uses Qdrant vector search if available, falls back to keyword search
        on the document_chunks.json file.

        Args:
            query: Search query
            top_k: Maximum results to return
            document_types: Filter by document types (e.g., ["adr", "config"])

        Returns:
            RAGContext with retrieved documents
        """
        # Try Qdrant first if available and has documents
        if self.rag_service:
            try:
                results = await self.rag_service.search_documents(
                    query=query,
                    n_results=top_k,
                    document_types=document_types,
                )
                if results:
                    contexts = [r.content for r in results if r.content]
                    sources = [r.source_file for r in results]
                    scores = [r.score for r in results]
                    return RAGContext(
                        contexts=contexts,
                        sources=sources,
                        scores=scores,
                        total_results=len(results),
                    )
            except Exception as e:
                logger.warning(f"Qdrant search failed, falling back to keyword search: {e}")

        # Fallback to keyword search on document chunks
        return await self._keyword_search(query, top_k, document_types)

    async def _keyword_search(
        self,
        query: str,
        top_k: int = 5,
        document_types: Optional[List[str]] = None,
    ) -> RAGContext:
        """Simple keyword-based search on document chunks."""
        try:
            chunks_file = self.data_dir / "rag-docs" / "document_chunks.json"
            if not chunks_file.exists():
                return RAGContext(contexts=[], sources=[], scores=[], total_results=0)

            with open(chunks_file, "r", encoding="utf-8") as f:
                chunks = json.load(f)

            # Normalize query for matching
            query_terms = set(query.lower().split())

            # Score each chunk by keyword relevance
            scored_chunks = []
            for chunk in chunks:
                # Filter by document type if specified
                doc_type = chunk.get("metadata", {}).get("document_type", "")
                if document_types and doc_type not in document_types:
                    continue

                content = chunk.get("content", "").lower()
                title = chunk.get("title", "").lower()

                # Simple scoring: count matching terms
                content_terms = set(content.split())
                title_terms = set(title.split())

                # Weight title matches higher
                title_matches = len(query_terms & title_terms)
                content_matches = len(query_terms & content_terms)

                score = (title_matches * 3) + content_matches
                if score > 0:
                    # Normalize score to 0-1 range
                    normalized_score = min(score / (len(query_terms) * 3), 1.0)
                    scored_chunks.append((chunk, normalized_score))

            # Sort by score and take top_k
            scored_chunks.sort(key=lambda x: x[1], reverse=True)
            top_chunks = scored_chunks[:top_k]

            contexts = [c[0].get("content", "") for c in top_chunks]
            sources = [c[0].get("source_file", "") for c in top_chunks]
            scores = [c[1] for c in top_chunks]

            return RAGContext(
                contexts=contexts,
                sources=sources,
                scores=scores,
                total_results=len(top_chunks),
            )

        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return RAGContext(contexts=[], sources=[], scores=[], total_results=0)

    async def query_lineage(
        self,
        job_name: Optional[str] = None,
        limit: int = 10,
    ) -> LineageContext:
        """
        Query Marquez lineage for execution history.

        Args:
            job_name: Filter by specific job/DAG name
            limit: Maximum runs to retrieve

        Returns:
            LineageContext with execution history
        """
        if not self.lineage_service:
            return LineageContext(
                recent_runs=[],
                success_rate=None,
                error_patterns=[],
                successful_patterns=[],
            )

        try:
            # Get recent runs from lineage service
            if hasattr(self.lineage_service, "get_recent_runs"):
                runs = await self.lineage_service.get_recent_runs(
                    job_name=job_name,
                    limit=limit,
                )
            else:
                runs = []

            # Calculate success rate
            success_rate = None
            if runs:
                successful = sum(1 for r in runs if r.get("state") == "COMPLETE")
                success_rate = successful / len(runs)

            # Extract error patterns
            error_patterns = []
            successful_patterns = []
            for run in runs:
                if run.get("state") == "FAILED":
                    if run.get("error"):
                        error_patterns.append(run["error"][:200])
                elif run.get("state") == "COMPLETE":
                    if run.get("job"):
                        successful_patterns.append(run["job"])

            return LineageContext(
                recent_runs=runs[:limit],
                success_rate=success_rate,
                error_patterns=list(set(error_patterns))[:5],
                successful_patterns=list(set(successful_patterns))[:5],
            )

        except Exception as e:
            logger.error(f"Lineage query failed: {e}")
            return LineageContext(
                recent_runs=[],
                success_rate=None,
                error_patterns=[],
                successful_patterns=[],
            )

    async def query_available_dags(
        self,
        tags: Optional[List[str]] = None,
        include_paused: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Query Airflow API for available DAGs.

        This provides dynamic discovery of DAG capabilities without
        requiring static documentation that can go stale.

        Args:
            tags: Filter by tags (e.g., ["vm", "qubinode-pipelines"])
            include_paused: Include paused DAGs in results

        Returns:
            List of DAGs with metadata (dag_id, description, tags, params)
        """
        import httpx

        airflow_url = os.getenv("AIRFLOW_API_URL", "http://localhost:8888")
        airflow_user = os.getenv("AIRFLOW_API_USER", "admin")
        airflow_pass = os.getenv("AIRFLOW_API_PASSWORD", "admin")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{airflow_url}/api/v1/dags",
                    auth=(airflow_user, airflow_pass),
                )
                response.raise_for_status()
                data = response.json()

                dags = []
                for dag in data.get("dags", []):
                    # Skip paused DAGs unless requested
                    if dag.get("is_paused") and not include_paused:
                        continue

                    dag_tags = [t.get("name") for t in dag.get("tags", [])]

                    # Filter by tags if specified
                    if tags:
                        if not any(t in dag_tags for t in tags):
                            continue

                    dags.append(
                        {
                            "dag_id": dag.get("dag_id"),
                            "description": dag.get("description"),
                            "tags": dag_tags,
                            "is_paused": dag.get("is_paused", False),
                            "file_token": dag.get("file_token"),
                        }
                    )

                logger.info(f"Found {len(dags)} available DAGs")
                return dags

        except Exception as e:
            logger.warning(f"Failed to query Airflow DAGs: {e}")
            return []

    async def get_dag_details(self, dag_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific DAG including parameters.

        Args:
            dag_id: The DAG ID to query

        Returns:
            DAG details including description, tags, and parameters
        """
        import httpx

        airflow_url = os.getenv("AIRFLOW_API_URL", "http://localhost:8888")
        airflow_user = os.getenv("AIRFLOW_API_USER", "admin")
        airflow_pass = os.getenv("AIRFLOW_API_PASSWORD", "admin")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get DAG details
                response = await client.get(
                    f"{airflow_url}/api/v1/dags/{dag_id}/details",
                    auth=(airflow_user, airflow_pass),
                )
                response.raise_for_status()
                dag = response.json()

                return {
                    "dag_id": dag.get("dag_id"),
                    "description": dag.get("description"),
                    "doc_md": dag.get("doc_md"),  # Markdown documentation
                    "tags": [t.get("name") for t in dag.get("tags", [])],
                    "params": dag.get("params", {}),
                    "is_paused": dag.get("is_paused", False),
                    "schedule_interval": dag.get("schedule_interval"),
                    "file_loc": dag.get("fileloc"),
                }

        except Exception as e:
            logger.warning(f"Failed to get DAG details for {dag_id}: {e}")
            return None

    async def find_dag_for_task(self, task_description: str) -> List[Dict[str, Any]]:
        """
        Find DAGs that can help accomplish a task.

        Uses keyword matching on DAG descriptions and tags to find
        relevant workflows.

        Args:
            task_description: What the user wants to accomplish

        Returns:
            List of matching DAGs with relevance scores
        """
        task_lower = task_description.lower()

        # Get all active DAGs
        all_dags = await self.query_available_dags(include_paused=False)

        # Score each DAG by relevance
        scored_dags = []
        for dag in all_dags:
            score = 0
            dag_text = f"{dag.get('description', '')} {' '.join(dag.get('tags', []))}".lower()

            # Check for keyword matches
            task_words = set(task_lower.split())
            dag_words = set(dag_text.split())

            # Common infrastructure terms to match
            matches = task_words & dag_words
            score = len(matches)

            # Boost for specific patterns
            if "vm" in task_lower and "vm" in dag_text:
                score += 3
            if "centos" in task_lower and ("centos" in dag_text or "generic" in dag.get("dag_id", "")):
                score += 3
            if "rhel" in task_lower and "rhel" in dag_text:
                score += 3
            if "openshift" in task_lower and "ocp" in dag.get("dag_id", ""):
                score += 3
            if "freeipa" in task_lower and "freeipa" in dag.get("dag_id", ""):
                score += 5
            if "deploy" in task_lower and "deployment" in dag.get("dag_id", ""):
                score += 2
            if "create" in task_lower and ("create" in dag_text or "deploy" in dag_text):
                score += 2

            if score > 0:
                scored_dags.append(
                    {
                        **dag,
                        "relevance_score": score,
                    }
                )

        # Sort by relevance
        scored_dags.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored_dags[:5]  # Top 5 matches

    async def get_context_for_task(
        self,
        task_description: str,
        include_lineage: bool = True,
        include_dags: bool = True,
    ) -> Dict[str, Any]:
        """
        Get combined RAG + lineage + DAG context for a task.

        This is the primary method agents should use to get context.

        Args:
            task_description: Description of the task
            include_lineage: Whether to include lineage data
            include_dags: Whether to include DAG discovery

        Returns:
            Combined context dict with 'rag', 'lineage', and 'dags' keys
        """
        # Query RAG in parallel with lineage and DAGs
        rag_task = self.query_rag(task_description, top_k=10)

        tasks = [rag_task]
        if include_lineage:
            tasks.append(self.query_lineage())
        if include_dags:
            tasks.append(self.find_dag_for_task(task_description))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Parse results
        rag_context = results[0] if not isinstance(results[0], Exception) else RAGContext(contexts=[], sources=[], scores=[], total_results=0)

        lineage_context = LineageContext(
            recent_runs=[],
            success_rate=None,
            error_patterns=[],
            successful_patterns=[],
        )
        if include_lineage and len(results) > 1 and not isinstance(results[1], Exception):
            lineage_context = results[1]

        dag_matches = []
        if include_dags:
            dag_idx = 2 if include_lineage else 1
            if len(results) > dag_idx and not isinstance(results[dag_idx], Exception):
                dag_matches = results[dag_idx]

        return {
            "rag": {
                "contexts": rag_context.contexts,
                "sources": rag_context.sources,
                "scores": rag_context.scores,
                "total_results": rag_context.total_results,
            },
            "lineage": {
                "recent_runs": lineage_context.recent_runs,
                "success_rate": lineage_context.success_rate,
                "error_patterns": lineage_context.error_patterns,
                "successful_patterns": lineage_context.successful_patterns,
            },
            "dags": {
                "matches": dag_matches,
                "total_matches": len(dag_matches),
            },
        }

    def get_status(self) -> Dict[str, Any]:
        """Get status of the agent context."""
        return {
            "initialized": self._initialized,
            "rag_available": self.rag_service is not None,
            "lineage_available": self.lineage_service is not None,
            "adrs_loaded": self.adrs_loaded,
            "project_root": str(self.project_root),
            "data_dir": str(self.data_dir),
        }


# Singleton instance
agent_context = AgentContextManager()


async def get_agent_context() -> AgentContextManager:
    """Get the singleton agent context manager."""
    return agent_context


async def initialize_agent_context(
    rag_service=None,
    lineage_service=None,
    auto_load_adrs: bool = True,
) -> AgentContextManager:
    """
    Initialize the agent context with services.

    Call this at startup to set up RAG and lineage services.
    """
    await agent_context.initialize(
        rag_service=rag_service,
        lineage_service=lineage_service,
        auto_load_adrs=auto_load_adrs,
    )
    return agent_context
