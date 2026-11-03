import logging
import re
from typing import Any, Dict, List, Optional
from src.database.connection import db_manager

logger = logging.getLogger(__name__)


class SparseRetriever:
    """Executes lexical search on content_tsvector using PostgreSQL ts_rank_cd."""

    @staticmethod
    def _prepare_tsquery_terms(query: str) -> str:
        """Sanitizes raw natural query into an OR/AND joined tsquery expression."""
        # Extract alphanumeric words and special terms (e.g. .str, bdot500, kio)
        cleaned = re.sub(r"[^\w\s\.]", " ", query, flags=re.UNICODE)
        words = [w.strip(" .") for w in cleaned.split() if len(w.strip(" .")) >= 2]
        if not words:
            return ""
        # Join words with '|' (OR) for broad lexical recall
        return " | ".join(words)

    def search(
        self,
        query: str,
        top_k: int = 50,
        parent_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Finds top_k matching chunks using full-text search and ts_rank_cd."""
        tsquery_str = self._prepare_tsquery_terms(query)
        if not tsquery_str:
            return []

        sql = """
            SELECT cv.id, cv.parent_id, cv.chunk_index, cv.content, cv.metadata_payload,
                   ts_rank_cd(cv.content_tsvector, to_tsquery('simple', %s)) AS rank
            FROM chunk_vectors cv
            WHERE cv.content_tsvector @@ to_tsquery('simple', %s)
        """
        params: List[Any] = [tsquery_str, tsquery_str]

        if parent_id:
            sql += " AND cv.parent_id = %s"
            params.append(parent_id)

        sql += " ORDER BY rank DESC LIMIT %s;"
        params.append(top_k)

        with db_manager.get_cursor() as cur:
            try:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
            except Exception as e:
                logger.warning("Sparse search query failed for query '%s': %s", query, e)
                return []

        results: List[Dict[str, Any]] = []
        for r in rows:
            results.append(
                {
                    "id": str(r[0]),
                    "parent_id": str(r[1]),
                    "chunk_index": r[2],
                    "content": r[3],
                    "metadata": r[4],
                    "score": float(r[5]),
                    "retrieval_mode": "sparse",
                }
            )

        return results
