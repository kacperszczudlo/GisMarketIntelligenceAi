import json
import logging
from pathlib import Path
from typing import Optional
from uuid import UUID
import psycopg2.extras

from src.database.connection import db_manager
from src.indexing.embedder import BgeM3Embedder
from src.indexing.splitter import ParentChildSplitter

logger = logging.getLogger(__name__)


class DatabaseIndexer:
    """Transactional batch indexer storing Parent-Child nodes and BGE-M3 embeddings in PostgreSQL."""

    def __init__(
        self,
        embedder: Optional[BgeM3Embedder] = None,
        splitter: Optional[ParentChildSplitter] = None,
    ) -> None:
        self.embedder = embedder or BgeM3Embedder()
        self.splitter = splitter or ParentChildSplitter()

    def index_document(self, markdown_text: str, attachment_id: UUID) -> int:
        """Parses, splits, embeds, and indexes document chunks in an atomic database transaction."""
        parents, children = self.splitter.split(markdown_text, attachment_id=attachment_id)
        if not parents or not children:
            logger.warning("No content extracted from document for attachment %s", attachment_id)
            return 0

        # Generate 1024-dimension embeddings for all children
        child_contents = [c.content for c in children]
        embeddings = self.embedder.embed_texts(child_contents)

        with db_manager.get_cursor(commit=True) as cur:
            # 1. Batch insert parent nodes
            parent_rows = [
                (
                    str(p.id),
                    str(attachment_id),
                    p.section_title,
                    p.token_count,
                    p.content,
                )
                for p in parents
            ]
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO parent_nodes (id, attachment_id, section_title, token_count, content)
                VALUES %s;
                """,
                parent_rows,
            )

            # 2. Batch insert child chunk vectors
            child_rows = []
            for child, emb in zip(children, embeddings):
                vec_str = "[" + ",".join(str(x) for x in emb) + "]"
                child_rows.append(
                    (
                        str(child.id),
                        str(child.parent_id),
                        child.chunk_index,
                        child.content,
                        vec_str,
                        json.dumps(child.metadata_payload),
                    )
                )

            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO chunk_vectors (id, parent_id, chunk_index, content, embedding, metadata_payload)
                VALUES %s;
                """,
                child_rows,
                template="(%s, %s, %s, %s, %s::vector, %s::jsonb)",
            )

        logger.info(
            "Successfully indexed %d parents and %d child vectors for attachment %s",
            len(parents),
            len(children),
            attachment_id,
        )
        return len(children)

    def index_file(self, file_path: Path, attachment_id: UUID) -> int:
        """Reads a Markdown file and indexes its contents."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Markdown file does not exist: {path}")
        text = path.read_text(encoding="utf-8")
        return self.index_document(text, attachment_id=attachment_id)
