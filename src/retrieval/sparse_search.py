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
        cleaned = re.sub(r"[^\w\s\.]", " ", query, flags=re.UNICODE)
        words = [w.strip(" .") for w in cleaned.split() if len(w.strip(" .")) >= 2]
        if not words:
            return ""
        return " | ".join(words)

    def _execute_query(
        self,
        tsquery_str: str,
        top_k: int,
        parent_id: Optional[str] = None,
        procurement_id: Optional[str] = None,
    ) -> List[Any]:
        sql = """
            SELECT cv.id, cv.parent_id, cv.chunk_index, cv.content, cv.metadata_payload,
                   ts_rank_cd(cv.content_tsvector, to_tsquery('simple', %s)) AS rank
            FROM chunk_vectors cv
        """
        params: List[Any] = [tsquery_str]
        conditions: List[str] = ["cv.content_tsvector @@ to_tsquery('simple', %s)"]
        params.append(tsquery_str)

        if procurement_id and procurement_id.lower() != "sample":
            sql += """
                JOIN parent_nodes pn ON cv.parent_id = pn.id
                JOIN attachments a ON pn.attachment_id = a.id
                JOIN procurements p ON a.procurement_id = p.id
            """
            conditions.append("(p.ocds_id = %s OR p.id::text = %s)")
            params.extend([procurement_id, procurement_id])

        if parent_id:
            conditions.append("cv.parent_id = %s")
            params.append(parent_id)

        sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY rank DESC LIMIT %s;"
        params.append(top_k)

        with db_manager.get_cursor() as cur:
            try:
                cur.execute(sql, tuple(params))
                return cur.fetchall()
            except Exception as e:
                logger.warning("Sparse search query failed: %s", e)
                return []

    def search(
        self,
        query: str,
        top_k: int = 50,
        parent_id: Optional[str] = None,
        procurement_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Finds top_k matching chunks using full-text search and ts_rank_cd."""
        tsquery_str = self._prepare_tsquery_terms(query)
        if not tsquery_str:
            return []

        rows = self._execute_query(tsquery_str, top_k=top_k, parent_id=parent_id, procurement_id=procurement_id)

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
